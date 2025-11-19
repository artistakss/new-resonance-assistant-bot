from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.config import settings
from app.database import repository
from app.keyboards.main import main_menu
from app.keyboards.payments import confirm_payment_kb, payment_methods_kb
from app.services.sheets import sheets_manager

router = Router()


class PaymentFlow(StatesGroup):
    choosing_method = State()
    waiting_proof = State()


@router.message(F.text == "💳 Оплата подписки")
async def start_payment(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        f"Стоимость месячного доступа: **{settings.subscription_price} ₸**\n\n"
        "Выберите удобный способ оплаты ниже.",
        reply_markup=payment_methods_kb,
    )
    await state.set_state(PaymentFlow.choosing_method)


@router.callback_query(PaymentFlow.choosing_method, F.data.startswith("pay:"))
async def choose_method(call: CallbackQuery, state: FSMContext) -> None:
    await call.answer()
    _, method = call.data.split(":", 1)
    if method == "ready":
        return

    details = await repository.get_payment_details(method)
    await state.update_data(method=method)
    await call.message.edit_text(
        f"💰 Оплата через **{method}**\n\n"
        f"Реквизиты: `{details}`\n\n"
        "После перевода нажмите кнопку ниже, чтобы отправить чек.",
        reply_markup=confirm_payment_kb,
    )


@router.callback_query(F.data == "pay:ready")
async def ready_to_upload(call: CallbackQuery, state: FSMContext) -> None:
    await call.answer()
    data = await state.get_data()
    if not data.get("method"):
        await call.message.answer("Сначала выберите способ оплаты.")
        return
    await state.set_state(PaymentFlow.waiting_proof)
    await call.message.edit_text(
        "📸 Отправьте фотографию или PDF-файл подтверждения оплаты.",
    )


@router.message(PaymentFlow.waiting_proof, F.photo | F.document)
async def receive_proof(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    method = data.get("method", "N/A")

    if message.photo:
        file_id = message.photo[-1].file_id
    else:
        file_id = message.document.file_id

    user = message.from_user
    row_index = sheets_manager.log_payment_check(user.id, user.username, method, file_id)
    check_id = await repository.log_payment_check(user.id, method, file_id, row_index)

    caption = (
        "💸 Новый чек на проверку\n"
        f"Пользователь: @{user.username or 'N/A'} ({user.id})\n"
        f"Метод: {method}\n"
        f"Сумма: {settings.subscription_price} ₸\n"
        f"ID записи: {check_id} | Строка Sheets: {row_index or '—'}"
    )

    markup = None
    if row_index:
        from app.handlers.admin import build_review_keyboard

        markup = build_review_keyboard(user.id, check_id, row_index)

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
    except Exception:
        await message.bot.send_message(settings.checker_id, caption, reply_markup=markup)

    await message.answer(
        "Спасибо! Чек отправлен на проверку."
        " Мы уведомим вас, как только администратор подтвердит оплату.",
        reply_markup=main_menu,
    )
    await state.clear()


@router.message(PaymentFlow.waiting_proof)
async def invalid_proof(message: Message) -> None:
    await message.answer("Пришлите, пожалуйста, фото или документ с подтверждением оплаты.")
