from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="🚪 Вход в Resonance"),
        ],
        [
            KeyboardButton(text="🎁 Подарить подписку"),
        ],
        [
            KeyboardButton(text="❓ Задать вопрос"),
        ],
        [
            KeyboardButton(text="🔄 Старт"),
            KeyboardButton(text="⬅️ Назад"),
        ],
    ],
    resize_keyboard=True,
    input_field_placeholder="Выберите действие",
)

