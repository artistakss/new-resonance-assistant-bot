import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from bot.database import repository
from bot.keyboards.main import main_menu
from bot.services.notifications import notify_admins_about_check
from bot.services.sheets import sheets_manager

logger = logging.getLogger(__name__)
router = Router()


class GiftFlow(StatesGroup):
    waiting_username = State()
    waiting_proof = State()


@router.message(F.text == "🎁 Подарить подписку")
async def start_gift(message: Message, state: FSMContext) -> None:
    """Начало процесса подарка подписки."""
    await state.clear()
    await message.answer(
        "🎁 Подарок подписки\n\n"
        "Отправьте @username пользователя, которому хотите подарить подписку.\n"
        "Например: @username или просто username"
    )
    await state.set_state(GiftFlow.waiting_username)


@router.message(GiftFlow.waiting_username)
async def receive_gift_username(message: Message, state: FSMContext) -> None:
    """Получение username для подарка."""
    try:
        current_state = await state.get_state()
        logger.info(
            "receive_gift_username called for user %s, state: %s, text: %s",
            message.from_user.id,
            current_state,
            message.text,
        )

        if not message.text:
            logger.warning("Non-text message in waiting_username from user %s", message.from_user.id)
            await message.answer("❌ Пожалуйста, отправьте текстовое сообщение с username (например: @username или username).")
            return

        username = message.text.strip().lstrip("@")
        logger.info("Received gift username from user %s: %s", message.from_user.id, username)

        if not username:
            await message.answer("❌ Неверный формат. Отправьте @username или username.")
            return

        await state.update_data(gift_username=username)
        logger.info("Gift username saved for user %s: %s", message.from_user.id, username)

        await message.answer(
            f"Выбран получатель: @{username}\n\n📸 Отправьте фотографию или PDF-файл подтверждения оплаты подарка."
        )
        await state.set_state(GiftFlow.waiting_proof)
        logger.info("State set to waiting_proof for gift from user %s", message.from_user.id)
    except Exception as exc:
        logger.error("Error in receive_gift_username: %s", exc, exc_info=True)
        await message.answer("❌ Произошла ошибка. Попробуйте еще раз.")


@router.message(GiftFlow.waiting_proof)
async def receive_gift_proof(message: Message, state: FSMContext) -> None:
    """Получение чека для подарка подписки."""
    current_state = await state.get_state()
    logger.info(
        "receive_gift_proof called for user %s, state: %s, has_photo: %s, has_document: %s",
        message.from_user.id,
        current_state,
        bool(message.photo),
        bool(message.document),
    )

    if not (message.photo or message.document):
        logger.info("Invalid gift proof type from user %s, text: %s", message.from_user.id, message.text)
        await message.answer("Пожалуйста, отправьте фото или документ с подтверждением оплаты подарка.")
        return

    try:
        data = await state.get_data()
        gift_username = data.get("gift_username")

        if not gift_username:
            await message.answer("❌ Ошибка: не найден username получателя.")
            await state.clear()
            return

        if message.photo:
            file_id = message.photo[-1].file_id
        else:
            file_id = message.document.file_id

        user = message.from_user
        logger.info("Received gift proof from user %s for @%s", user.id, gift_username)

        gift_method = f"Gift-{gift_username}"
        row_index = sheets_manager.log_payment_check(user.id, user.username, gift_method, file_id)
        check_id = await repository.log_payment_check(
            user.id,
            gift_method,
            file_id,
            row_index,
            duration_days=30,
            price_kzt=0,
        )

        caption = (
            "🎁 Чек на подарок подписки\n"
            f"От: @{user.username or 'N/A'} ({user.id})\n"
            f"Получатель: @{gift_username}\n"
            "Метод: Подарок\n"
            "Сумма: Подарок (бесплатно)\n"
            f"ID записи: {check_id} | Строка Sheets: {row_index or '—'}\n\n"
            f"⚠️ Админ должен найти user_id для @{gift_username} и активировать подписку вручную."
        )

        markup = None
        if row_index:
            from bot.handlers.admin import build_gift_review_keyboard

            markup = build_gift_review_keyboard(gift_username, check_id, row_index)

        if message.photo:
            sent_count = await notify_admins_about_check(
                message.bot,
                photo_file_id=file_id,
                caption=caption,
                reply_markup=markup,
            )
        else:
            sent_count = await notify_admins_about_check(
                message.bot,
                document_file_id=file_id,
                caption=caption,
                reply_markup=markup,
            )

        if sent_count == 0:
            logger.error("Failed to send gift check notification to any admin")

        await message.answer(
            f"✅ Спасибо! Чек на подарок для @{gift_username} отправлен на проверку.\n"
            "Мы уведомим получателя, как только администратор подтвердит подарок.",
            reply_markup=main_menu,
        )
        await state.clear()
        logger.info("Gift proof processed successfully for user %s", user.id)
    except Exception as exc:
        logger.error("Error processing gift proof: %s", exc, exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при обработке чека подарка. Пожалуйста, попробуйте еще раз.",
            reply_markup=main_menu,
        )
        await state.clear()

