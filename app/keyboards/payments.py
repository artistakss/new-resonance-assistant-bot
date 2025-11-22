from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.config import settings


def get_subscription_plans_kb() -> InlineKeyboardMarkup:
    """Клавиатура с вариантами подписок"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=f"1 месяц — {settings.subscription_prices[30]:,} ₸ / {settings.subscription_prices_rub[30]:,} ₽",
                callback_data="plan:30"
            )],
            [InlineKeyboardButton(
                text=f"3 месяца — {settings.subscription_prices[90]:,} ₸ / {settings.subscription_prices_rub[90]:,} ₽ (выгоднее!)",
                callback_data="plan:90"
            )],
            [InlineKeyboardButton(
                text=f"6 месяцев — {settings.subscription_prices[180]:,} ₸ / {settings.subscription_prices_rub[180]:,} ₽ (максимальная выгода!)",
                callback_data="plan:180"
            )],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="plan:back")],
        ]
    )


payment_methods_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Kaspi Bank", callback_data="pay:Kaspi")],
        [InlineKeyboardButton(text="Tinkoff", callback_data="pay:Tinkoff")],
        [InlineKeyboardButton(text="Crypto USDT", callback_data="pay:USDT")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="pay:back")],
    ]
)

confirm_payment_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я оплатил", callback_data="pay:ready")]
    ]
)
