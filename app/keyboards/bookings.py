from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

booking_mode_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Онлайн", callback_data="booking:online")],
        [InlineKeyboardButton(text="Оффлайн", callback_data="booking:offline")],
    ]
)
