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


class GiftSubscriptionState(StatesGroup):
    waiting_user_id = State()
    waiting_duration = State()


class GiftConfirmState(StatesGroup):
    waiting_user_id = State()


def build_review_keyboard(user_id: int, check_id: int, row_index: int | None) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"pay-confirm:{user_id}:{check_id}:{row_index or 0}")],
        [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"pay-reject:{user_id}:{check_id}:{row_index or 0}")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_gift_review_keyboard(username: str, check_id: int, row_index: int | None) -> InlineKeyboardMarkup:
    """Клавиатура для подтверждения подарка подписки"""
    buttons = [
        [InlineKeyboardButton(text="✅ Подтвердить подарок", callback_data=f"gift-confirm:{username}:{check_id}:{row_index or 0}")],
        [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"gift-reject:{username}:{check_id}:{row_index or 0}")],
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
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:back")],
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

    # Получаем информацию о чеке, чтобы узнать длительность подписки
    check_info = await repository.get_payment_check(check_id)
    duration_days = check_info["duration_days"] if check_info and check_info.get("duration_days") else settings.subscription_duration_days

    start = datetime.utcnow()
    start, end = await repository.set_subscription_active(
        user_id=user_id,
        start=start,
        duration_days=duration_days,
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


@router.callback_query(F.data == "admin:back")
async def admin_back(call: CallbackQuery) -> None:
    """Возврат в главное меню админ-панели"""
    if call.from_user.id not in settings.allowed_admins:
        await call.answer("❌ Нет доступа", show_alert=True)
        return
    await call.answer()
    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 Обновить реквизиты", callback_data="admin:update_details")],
            [InlineKeyboardButton(text="👥 Активные подписки", callback_data="admin:list_active")],
            [InlineKeyboardButton(text="📅 Последние записи", callback_data="admin:list_bookings")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:back")],
        ]
    )
    await call.message.edit_text("Админ-панель Resonance", reply_markup=markup)


@router.callback_query(F.data == "admin:gift_subscription")
async def start_gift_subscription(call: CallbackQuery, state: FSMContext) -> None:
    """Начало процесса подарка подписки"""
    if call.from_user.id not in settings.allowed_admins:
        await call.answer("❌ Нет доступа", show_alert=True)
        return
    await call.answer()
    await call.message.edit_text(
        "🎁 Подарок подписки\n\n"
        "Отправьте Telegram ID пользователя, которому хотите подарить подписку.\n"
        "ID можно узнать через @userinfobot или другие боты.",
    )
    await state.set_state(GiftSubscriptionState.waiting_user_id)


@router.message(GiftSubscriptionState.waiting_user_id)
async def receive_gift_user_id(message: Message, state: FSMContext) -> None:
    """Получение user_id для подарка"""
    try:
        user_id = int(message.text.strip())
        await state.update_data(user_id=user_id)
        
        # Показываем варианты длительности подписки
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="1 месяц (30 дней)", callback_data="gift:30")],
                [InlineKeyboardButton(text="3 месяца (90 дней)", callback_data="gift:90")],
                [InlineKeyboardButton(text="6 месяцев (180 дней)", callback_data="gift:180")],
                [InlineKeyboardButton(text="⬅️ Отмена", callback_data="admin:back")],
            ]
        )
        await message.answer(
            f"Выберите длительность подписки для пользователя {user_id}:",
            reply_markup=markup,
        )
        await state.set_state(GiftSubscriptionState.waiting_duration)
    except ValueError:
        await message.answer("❌ Неверный формат. Отправьте числовой ID пользователя.")


@router.callback_query(GiftSubscriptionState.waiting_duration, F.data.startswith("gift:"))
async def confirm_gift_subscription(call: CallbackQuery, state: FSMContext) -> None:
    """Подтверждение и активация подарка подписки"""
    if call.from_user.id not in settings.allowed_admins:
        await call.answer("❌ Нет доступа", show_alert=True)
        return
    
    await call.answer()
    data = await state.get_data()
    user_id = data.get("user_id")
    
    if not user_id:
        await call.message.edit_text("❌ Ошибка: не найден user_id")
        await state.clear()
        return
    
    duration_days = int(call.data.split(":")[1])
    start = datetime.utcnow()
    start, end = await repository.set_subscription_active(
        user_id=user_id,
        start=start,
        duration_days=duration_days,
    )
    
    # Добавляем пользователя в базу, если его там нет
    try:
        user_info = await call.bot.get_chat(user_id)
        await repository.upsert_user(
            user_id,
            user_info.username,
            user_info.first_name or user_info.full_name,
        )
    except Exception as exc:
        logger.warning("Cannot get user info for %s: %s", user_id, exc)
    
    # Добавляем пользователя в канал (если бот является администратором канала)
    try:
        # Пробуем пригласить пользователя в канал
        await call.bot.unban_chat_member(chat_id=settings.channel_id, user_id=user_id, only_if_banned=True)
    except Exception as exc:
        logger.warning("Cannot unban user in channel: %s", exc)
    
    # Уведомляем пользователя
    try:
        await call.bot.send_message(
            user_id,
            f"🎁 Вам подарена подписка на Resonance!\n\n"
            f"Доступ активен до {end:%d.%m.%Y}.\n"
            f"Ссылка на канал: {settings.channel_invite_link}",
        )
    except Exception as exc:
        logger.warning("Cannot notify user %s: %s", user_id, exc)
    
    await call.message.edit_text(
        f"✅ Подписка подарена пользователю {user_id}\n"
        f"Длительность: {duration_days} дней\n"
        f"Доступ до: {end:%d.%m.%Y}",
    )
    await state.clear()


@router.callback_query(F.data.startswith("gift-confirm:"))
async def confirm_gift_payment(call: CallbackQuery, state: FSMContext) -> None:
    """Начало подтверждения подарка - запрос user_id"""
    if call.from_user.id not in settings.allowed_admins:
        await call.answer("❌ Нет доступа", show_alert=True)
        return
    
    await call.answer()
    _, username, check_id, row_index = call.data.split(":")
    check_id = int(check_id)
    row_index = int(row_index)
    
    # Сохраняем данные в состоянии
    await state.update_data(gift_username=username, gift_check_id=check_id, gift_row_index=row_index)
    
    await call.message.edit_text(
        f"🎁 Подтверждение подарка для @{username}\n\n"
        "Отправьте Telegram ID пользователя (user_id).\n"
        "ID можно узнать через @userinfobot или найти в базе данных бота.",
    )
    await state.set_state(GiftConfirmState.waiting_user_id)


@router.message(GiftConfirmState.waiting_user_id)
async def receive_gift_user_id(message: Message, state: FSMContext) -> None:
    """Получение user_id и активация подарка"""
    if message.from_user.id not in settings.allowed_admins:
        await message.answer("❌ У вас нет доступа.")
        await state.clear()
        return
    
    try:
        user_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Неверный формат. Отправьте числовой ID пользователя.")
        return
    
    data = await state.get_data()
    username = data.get("gift_username")
    check_id = data.get("gift_check_id")
    row_index = data.get("gift_row_index")
    
    # Активируем подписку (1 месяц по умолчанию для подарка)
    duration_days = 30
    start = datetime.utcnow()
    start, end = await repository.set_subscription_active(
        user_id=user_id,
        start=start,
        duration_days=duration_days,
    )
    
    # Обновляем статус чека
    await repository.update_payment_check_status(check_id, "approved")
    if row_index:
        sheets_manager.update_payment_status(row_index, "✅ Подтверждено (подарок)", start, end)
    
    # Добавляем пользователя в базу, если его там нет
    try:
        user_info = await message.bot.get_chat(user_id)
        await repository.upsert_user(
            user_id,
            user_info.username,
            user_info.first_name or user_info.full_name,
        )
    except Exception as exc:
        logger.warning("Cannot get user info for %s: %s", user_id, exc)
    
    # Добавляем пользователя в канал
    try:
        await message.bot.unban_chat_member(chat_id=settings.channel_id, user_id=user_id, only_if_banned=True)
    except Exception as exc:
        logger.warning("Cannot unban user in channel: %s", exc)
    
    # Уведомляем получателя подарка
    try:
        await message.bot.send_message(
            user_id,
            f"🎁 Вам подарена подписка на Resonance!\n\n"
            f"Доступ активен до {end:%d.%m.%Y}.\n"
            f"Ссылка на канал: {settings.channel_invite_link}",
        )
    except Exception as exc:
        logger.warning("Cannot notify user %s: %s", user_id, exc)
    
    await message.answer(
        f"✅ Подарок активирован!\n"
        f"Пользователь: @{username} (ID: {user_id})\n"
        f"Длительность: {duration_days} дней\n"
        f"Доступ до: {end:%d.%m.%Y}",
    )
    await state.clear()


@router.callback_query(F.data.startswith("gift-reject:"))
async def reject_gift_payment(call: CallbackQuery) -> None:
    """Отклонение подарка подписки"""
    if call.from_user.id not in settings.allowed_admins:
        await call.answer("❌ Нет доступа", show_alert=True)
        return
    
    await call.answer()
    _, username, check_id, row_index = call.data.split(":")
    check_id = int(check_id)
    row_index = int(row_index)
    
    await repository.update_payment_check_status(check_id, "rejected")
    if row_index:
        sheets_manager.update_payment_status(row_index, "❌ Отклонено")
    
    await call.message.edit_text(f"Подарок для @{username} отклонен", reply_markup=None)
