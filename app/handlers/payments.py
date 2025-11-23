import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramNetworkError
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.config import settings
from app.database import repository
from app.keyboards.main import main_menu
from app.keyboards.payments import confirm_payment_kb, get_subscription_plans_kb, payment_methods_kb
from app.services.sheets import sheets_manager

logger = logging.getLogger(__name__)
router = Router()


class PaymentFlow(StatesGroup):
    choosing_plan = State()
    choosing_method = State()
    waiting_proof = State()


@router.message(F.text == "🚪 Вход в Resonance")
async def start_payment(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "Выберите период подписки:",
        reply_markup=get_subscription_plans_kb(),
    )
    await state.set_state(PaymentFlow.choosing_plan)


@router.callback_query(PaymentFlow.choosing_plan, F.data.startswith("plan:"))
async def choose_plan(call: CallbackQuery, state: FSMContext) -> None:
    """Выбор периода подписки"""
    try:
        await call.answer()
    except Exception:
        pass
    
    if call.data == "plan:back":
        await call.message.delete()
        await state.clear()
        return
    
    duration_days = int(call.data.split(":")[1])
    price_kzt = settings.subscription_prices[duration_days]
    price_rub = settings.subscription_prices_rub[duration_days]
    
    await state.update_data(duration_days=duration_days, price_kzt=price_kzt)
    
    period_text = f"{duration_days // 30} {'месяц' if duration_days == 30 else 'месяца' if duration_days == 90 else 'месяцев'}"
    await call.message.edit_text(
        f"Выбрано: {period_text}\n"
        f"Стоимость: **{price_kzt:,} ₸ / {price_rub:,} ₽**\n\n"
        "Выберите удобный способ оплаты:",
        reply_markup=payment_methods_kb,
        parse_mode="Markdown",
    )
    await state.set_state(PaymentFlow.choosing_method)


@router.callback_query(PaymentFlow.choosing_method, F.data.startswith("pay:"))
async def choose_method(call: CallbackQuery, state: FSMContext) -> None:
    try:
        await call.answer()
    except Exception:
        pass  # Игнорируем ошибки ответа на callback
    
    _, method = call.data.split(":", 1)
    logger.info(f"choose_method callback: method={method}, user={call.from_user.id}")
    
    if method == "ready":
        # Это обрабатывается отдельным обработчиком
        return
    if method == "back":
        # Возврат к выбору плана
        await call.message.edit_text(
            "Выберите период подписки:",
            reply_markup=get_subscription_plans_kb(),
        )
        await state.set_state(PaymentFlow.choosing_plan)
        return

    try:
        details = await repository.get_payment_details(method)
        await state.update_data(method=method)
        await call.message.edit_text(
            f"💰 Оплата через **{method}**\n\n"
            f"Реквизиты:\n`{details}`\n\n"
            "💡 *Нажмите на текст реквизитов выше, чтобы скопировать их*\n\n"
            "После перевода нажмите кнопку ниже, чтобы отправить чек.",
            reply_markup=confirm_payment_kb,
            parse_mode="Markdown",
        )
    except TelegramNetworkError as exc:
        logger.error("Network error in choose_method: %s", exc)
        # Пробуем отправить новое сообщение вместо редактирования
        try:
            await call.message.answer(
                f"💰 Оплата через **{method}**\n\n"
                f"Реквизиты:\n`{details}`\n\n"
                "💡 *Нажмите на текст реквизитов выше, чтобы скопировать их*\n\n"
                "После перевода нажмите кнопку ниже, чтобы отправить чек.",
                reply_markup=confirm_payment_kb,
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.error("Failed to send payment method details: %s", e)
    except Exception as exc:
        logger.error("Error in choose_method: %s", exc, exc_info=True)


@router.callback_query(F.data == "pay:ready")
async def ready_to_upload(call: CallbackQuery, state: FSMContext) -> None:
    try:
        await call.answer("Ожидаю ваш чек...")
        data = await state.get_data()
        logger.info(f"pay:ready callback from user {call.from_user.id}, data: {data}")
        
        if not data.get("method"):
            logger.warning(f"No method in state for user {call.from_user.id}")
            await call.message.answer("Сначала выберите способ оплаты.")
            return
        
        # Сохраняем состояние
        await state.set_state(PaymentFlow.waiting_proof)
        current_state = await state.get_state()
        logger.info(f"State set to waiting_proof for user {call.from_user.id}, current_state: {current_state}")
        
        # Отправляем новое сообщение
        sent_msg = await call.message.answer(
            "📸 Отправьте фотографию или PDF-файл подтверждения оплаты.",
        )
        logger.info(f"Sent message to user {call.from_user.id} asking for proof, message_id: {sent_msg.message_id}")
    except Exception as exc:
        logger.error(f"Error in ready_to_upload: {exc}", exc_info=True)
        try:
            await call.answer("Произошла ошибка. Попробуйте еще раз.")
        except:
            pass


@router.message(PaymentFlow.waiting_proof)
async def receive_proof(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    logger.info(f"receive_proof called for user {message.from_user.id}, state: {current_state}, has_photo: {bool(message.photo)}, has_document: {bool(message.document)}")
    
    # Проверяем, что это фото или документ
    if not (message.photo or message.document):
        logger.info(f"Invalid proof type from user {message.from_user.id}, text: {message.text}")
        await message.answer("Пришлите, пожалуйста, фото или документ с подтверждением оплаты.")
        return
    
    try:
        data = await state.get_data()
        method = data.get("method", "N/A")
        duration_days = data.get("duration_days", settings.subscription_duration_days)
        price_kzt = data.get("price_kzt", settings.subscription_price)

        if message.photo:
            file_id = message.photo[-1].file_id
        else:
            file_id = message.document.file_id

        user = message.from_user
        logger.info(f"Received payment proof from user {user.id}, method: {method}")
        
        row_index = sheets_manager.log_payment_check(user.id, user.username, method, file_id)
        check_id = await repository.log_payment_check(
            user.id, method, file_id, row_index, duration_days, price_kzt
        )

        period_text = f"{duration_days // 30} {'месяц' if duration_days == 30 else 'месяца' if duration_days == 90 else 'месяцев'}"
        caption = (
            "💸 Новый чек на проверку\n"
            f"Пользователь: @{user.username or 'N/A'} ({user.id})\n"
            f"Метод: {method}\n"
            f"Период: {period_text} ({duration_days} дней)\n"
            f"Сумма: {price_kzt:,} ₸\n"
            f"ID записи: {check_id} | Строка Sheets: {row_index or '—'}"
        )

        markup = None
        if row_index:
            from app.handlers.admin import build_review_keyboard

            markup = build_review_keyboard(user.id, check_id, row_index)

        # Отправляем уведомление админу
        try:
            if message.photo:
                await message.bot.send_photo(
                    settings.checker_id,
                    photo=file_id,
                    caption=caption,
                    reply_markup=markup,
                )
            else:
                await message.bot.send_document(
                    settings.checker_id,
                    document=file_id,
                    caption=caption,
                    reply_markup=markup,
                )
            logger.info(f"Payment check notification sent to checker_id {settings.checker_id}")
        except Exception as exc:
            logger.error(f"Failed to send photo/document to checker, trying text: {exc}")
            try:
                await message.bot.send_message(settings.checker_id, caption, reply_markup=markup)
                logger.info(f"Payment check notification sent as text to checker_id {settings.checker_id}")
            except Exception as exc2:
                logger.error(f"Failed to send notification to checker_id {settings.checker_id}: {exc2}")

        await message.answer(
            "✅ Спасибо! Чек отправлен на проверку.\n"
            "Мы уведомим вас, как только администратор подтвердит оплату.",
            reply_markup=main_menu,
        )
        await state.clear()
        logger.info(f"Payment proof processed successfully for user {user.id}")
    except Exception as exc:
        logger.error(f"Error processing payment proof: {exc}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при обработке чека. Пожалуйста, попробуйте еще раз.",
            reply_markup=main_menu,
        )
        await state.clear()


