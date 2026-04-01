from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from bot.config import settings
from bot.database import repository
from bot.keyboards.bookings import booking_mode_kb
from bot.keyboards.main import main_menu
from bot.services.sheets import sheets_manager

router = Router()


class BookingFlow(StatesGroup):
    choosing_mode = State()
    waiting_slot = State()


@router.message(F.text == "📅 Записаться")
async def booking_entry(message: Message, state: FSMContext) -> None:
    await state.set_state(BookingFlow.choosing_mode)
    await message.answer(
        "Выберите формат встречи с Анжеликой:",
        reply_markup=booking_mode_kb,
    )


@router.callback_query(BookingFlow.choosing_mode, F.data.startswith("booking:"))
async def select_mode(call: CallbackQuery, state: FSMContext) -> None:
    await call.answer()
    mode = call.data.split(":", 1)[1]
    await state.update_data(mode=mode)
    await state.set_state(BookingFlow.waiting_slot)
    await call.message.edit_text("Напишите удобные дату и время, а также город (для оффлайн) и формат связи (для онлайн).")


@router.message(BookingFlow.waiting_slot)
async def save_booking(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    mode = data.get("mode", "online")
    slot = message.text
    user = message.from_user

    booking_id = await repository.add_booking(user.id, mode, slot, None)
    sheets_manager.log_booking(user.id, user.username, mode, slot, None)

    text = (
        "✅ Заявка сохранена!\n"
        f"Формат: {mode}\n"
        f"Запрос: {slot}\n"
        "Анжелика или администратор подтвердят время в ближайшее время."
    )
    await message.answer(text, reply_markup=main_menu)

    notify = (
        "📅 Новая заявка на встречу\n"
        f"Пользователь: @{user.username or 'N/A'} ({user.id})\n"
        f"Формат: {mode}\n"
        f"Детали: {slot}\n"
        f"ID брони: {booking_id}"
    )
    for admin_id in settings.allowed_admins:
        try:
            await message.bot.send_message(admin_id, notify)
        except Exception as exc:
            import logging

            logger = logging.getLogger(__name__)
            logger.warning("Failed to notify admin %s about booking: %s", admin_id, exc)
    await state.clear()

