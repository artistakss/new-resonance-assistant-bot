import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from app.config import settings
from app.database import repository
from app.keyboards.main import main_menu
from app.keyboards.payments import confirm_payment_kb
from app.services.sheets import sheets_manager

logger = logging.getLogger(__name__)
router = Router()


class GiftFlow(StatesGroup):
    waiting_username = State()
    waiting_proof = State()


@router.message(F.text == "🎁 Подарить подписку")
async def start_gift(message: Message, state: FSMContext) -> None:
    """Начало процесса подарка подписки"""
    await state.clear()
    await message.answer(
        "🎁 Подарок подписки\n\n"
        "Отправьте @username пользователя, которому хотите подарить подписку.\n"
        "Например: @username или просто username",
    )
    await state.set_state(GiftFlow.waiting_username)


@router.message(GiftFlow.waiting_username)
async def receive_gift_username(message: Message, state: FSMContext) -> None:
    """Получение username для подарка"""
    username = message.text.strip().lstrip("@")
    
    if not username:
        await message.answer("❌ Неверный формат. Отправьте @username или username.")
        return
    
    # Сохраняем username в состоянии
    await state.update_data(gift_username=username)
    
    # Просим отправить чек
    await message.answer(
        f"Выбран получатель: @{username}\n\n"
        "📸 Отправьте фотографию или PDF-файл подтверждения оплаты подарка.",
    )
    await state.set_state(GiftFlow.waiting_proof)


@router.message(GiftFlow.waiting_proof, F.photo | F.document)
async def receive_gift_proof(message: Message, state: FSMContext) -> None:
    """Получение чека для подарка подписки"""
    data = await state.get_data()
    gift_username = data.get("gift_username")
    
    if not gift_username:
        await message.answer("❌ Ошибка: не найден username получателя.")
        await state.clear()
        return
    
    # Пробуем найти пользователя по username
    # В Telegram API нужно использовать get_chat для получения user_id по username
    try:
        # Пробуем получить информацию о пользователе через бота
        # Но сначала нужно получить user_id - для этого используем поиск в базе или попросим админа ввести user_id
        # Пока что сохраняем username и админ сможет найти пользователя вручную
        user_id = None  # Будет определен админом при проверке чека
    except Exception as exc:
        logger.error("Error getting user info: %s", exc)
        user_id = None
    
    if message.photo:
        file_id = message.photo[-1].file_id
    else:
        file_id = message.document.file_id
    
    user = message.from_user
    
    # Логируем чек для подарка (с особым методом "Gift")
    row_index = sheets_manager.log_payment_check(user.id, user.username, f"Gift-{gift_username}", file_id)
    check_id = await repository.log_payment_check(
        user.id, f"Gift-{gift_username}", file_id, row_index, 
        duration_days=30,  # По умолчанию 1 месяц для подарка
        price_kzt=0  # Подарок - цена 0
    )
    
    # Сохраняем username получателя в данных чека (используем поле method для хранения дополнительной информации)
    # Или лучше создать отдельное поле в БД, но пока используем существующую структуру
    
    caption = (
        "🎁 Чек на подарок подписки\n"
        f"От: @{user.username or 'N/A'} ({user.id})\n"
        f"Получатель: @{gift_username}\n"
        f"Метод: Подарок\n"
        f"Сумма: Подарок (бесплатно)\n"
        f"ID записи: {check_id} | Строка Sheets: {row_index or '—'}\n\n"
        f"⚠️ Админ должен найти user_id для @{gift_username} и активировать подписку вручную."
    )
    
    markup = None
    if row_index:
        from app.handlers.admin import build_gift_review_keyboard
        
        markup = build_gift_review_keyboard(gift_username, check_id, row_index)
    
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
        f"Спасибо! Чек на подарок для @{gift_username} отправлен на проверку.\n"
        "Мы уведомим получателя, как только администратор подтвердит подарок.",
        reply_markup=main_menu,
    )
    await state.clear()


@router.message(GiftFlow.waiting_proof)
async def invalid_gift_proof(message: Message) -> None:
    """Обработка некорректного ввода для подарка"""
    await message.answer(
        "Пожалуйста, отправьте фото или документ с подтверждением оплаты подарка."
    )

