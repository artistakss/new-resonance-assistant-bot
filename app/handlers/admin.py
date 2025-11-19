from __future__ import annotations

import logging
from datetime import datetime

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.config import settings
from app.database import repository
from app.services.sheets import sheets_manager

router = Router()
# Временно убираем фильтр для отладки - вернём после проверки
# router.message.filter(F.from_user.id.in_(settings.allowed_admins))
# router.callback_query.filter(F.from_user.id.in_(settings.allowed_admins))

logger = logging.getLogger(__name__)


class UpdateDetailsState(StatesGroup):
    waiting_method = State()
    waiting_details = State()


def build_review_keyboard(user_id: int, check_id: int, row_index: int | None) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"pay-confirm:{user_id}:{check_id}:{row_index or 0}")],
        [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"pay-reject:{user_id}:{check_id}:{row_index or 0}")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(Command("admin"))
async def admin_menu(message: Message) -> None:
    # Проверка прав админа
    if message.from_user.id not in settings.allowed_admins:
        await message.answer("❌ У вас нет доступа к админ-панели.")
        logger.warning(f"User {message.from_user.id} tried to access admin panel. Allowed: {settings.allowed_admins}")
        return
    
    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 Обновить реквизиты", callback_data="admin:update_details")],
            [InlineKeyboardButton(text="👥 Активные подписки", callback_data="admin:list_active")],
            [InlineKeyboardButton(text="📅 Последние записи", callback_data="admin:list_bookings")],
        ]
    )
    await message.answer("Админ-панель Resonance", reply_markup=markup)


@router.callback_query(F.data == "admin:update_details")
async def choose_method(call: CallbackQuery, state: FSMContext) -> None:
    if call.from_user.id not in settings.allowed_admins:
        await call.answer("❌ Нет доступа", show_alert=True)
        return
    await call.answer()
    methods = await repository.list_payment_methods()
    keyboard = [
        [InlineKeyboardButton(text=row["method"], callback_data=f"admin:method:{row['method']}")]
        for row in methods
    ]
    await call.message.edit_text("Какой метод обновляем?", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await state.set_state(UpdateDetailsState.waiting_details)


@router.callback_query(UpdateDetailsState.waiting_details, F.data.startswith("admin:method:"))
async def ask_new_details(call: CallbackQuery, state: FSMContext) -> None:
    await call.answer()
    method = call.data.split(":")[-1]
    await state.update_data(method=method)
    await call.message.edit_text(f"Отправьте новые реквизиты для {method}:")


@router.message(UpdateDetailsState.waiting_details)
async def save_new_details(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    method = data.get("method")
    if not method:
        await message.answer("Сначала выберите метод.")
        return
    await repository.update_payment_details(method, message.text)
    await state.clear()
    await message.answer(f"Реквизиты для {method} обновлены.")


@router.callback_query(F.data == "admin:list_active")
async def list_active(call: CallbackQuery) -> None:
    await call.answer()
    users = await repository.get_active_users()
    if not users:
        await call.message.edit_text("Нет активных подписчиков")
        return
    lines = ["👥 Активные подписчики:"]
    for row in users[:10]:
        end_text = row["sub_end"] or "?"
        lines.append(f"• @{row['username'] or 'N/A'} — до {end_text[:10]}")
    await call.message.edit_text("\n".join(lines))


@router.callback_query(F.data == "admin:list_bookings")
async def list_bookings(call: CallbackQuery) -> None:
    await call.answer()
    rows = await repository.list_recent_bookings()
    if not rows:
        await call.message.edit_text("Пока нет записей")
        return
    lines = ["📅 Последние записи:"]
    for row in rows:
        lines.append(f"• @{row['user_id']} {row['mode']} — {row['slot']}")
    await call.message.edit_text("\n".join(lines))


@router.callback_query(F.data.startswith("pay-confirm:"))
async def confirm_payment(call: CallbackQuery) -> None:
    await call.answer()
    _, user_id, check_id, row_index = call.data.split(":")
    user_id = int(user_id)
    check_id = int(check_id)
    row_index = int(row_index)

    start = datetime.utcnow()
    start, end = await repository.set_subscription_active(
        user_id=user_id,
        start=start,
        duration_days=settings.subscription_duration_days,
    )
    await repository.update_payment_check_status(check_id, "approved")
    if row_index:
        sheets_manager.update_payment_status(row_index, "✅ Подтверждено", start, end)

    try:
        await call.bot.send_message(
            user_id,
            f"✅ Оплата подтверждена! Доступ активен до {end:%d.%m.%Y}.\n"
            f"Ссылка на канал: {settings.channel_invite_link}",
        )
    except Exception as exc:
        logger.warning("Cannot notify user %s: %s", user_id, exc)

    await call.message.edit_text("Доступ активирован", reply_markup=None)


@router.callback_query(F.data.startswith("pay-reject:"))
async def reject_payment(call: CallbackQuery) -> None:
    await call.answer()
    _, user_id, check_id, row_index = call.data.split(":")
    user_id = int(user_id)
    check_id = int(check_id)
    row_index = int(row_index)

    await repository.update_payment_check_status(check_id, "rejected")
    if row_index:
        sheets_manager.update_payment_status(row_index, "❌ Отклонено")

    try:
        await call.bot.send_message(
            user_id,
            "❌ Оплата не подтверждена. Проверьте реквизиты и отправьте чек повторно.",
        )
    except Exception as exc:
        logger.warning("Cannot notify user %s: %s", user_id, exc)

    await call.message.edit_text("Оплата отклонена", reply_markup=None)
