from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


payment_methods_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Kaspi Bank", callback_data="pay:Kaspi")],
        [InlineKeyboardButton(text="Tinkoff", callback_data="pay:Tinkoff")],
        [InlineKeyboardButton(text="Crypto USDT", callback_data="pay:USDT")],
    ]
)

confirm_payment_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я оплатил", callback_data="pay:ready")]
    ]
)
