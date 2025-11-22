from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="💳 Оплата подписки"),
        ],
        [
            KeyboardButton(text="❓ Задать вопрос"),
        ],
        [
            KeyboardButton(text="⬅️ Назад"),
        ],
    ],
    resize_keyboard=True,
    input_field_placeholder="Выберите действие",
)
