from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.database import repository
from app.keyboards.main import main_menu

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    # Сбрасываем состояние FSM при /start
    await state.clear()
    user = message.from_user
    await repository.upsert_user(user.id, user.username, user.full_name)
    await message.answer(
        "🧘 Добро пожаловать в поле Resonance!\n\n"
        "Месяц подписки — 9 999 ₸ / 1 515 ₽.\n"
        "Поле триединства: дух • душа • тело — в лице трёх мастеров.\n"
        "3 раза в неделю живые эфиры: сатсанги, практики, разборы, задания и новая информация.",
        reply_markup=main_menu,
    )


@router.message(F.text == "🧘 Описание Анжелики")
async def describe(message: Message) -> None:
    await message.answer(
        "✨ Анжелика — эксперт по эмоциональному балансу и осознанности."
        " Проводит личные онлайн и офлайн сессии, ведёт резиденцию Resonance."
    )


@router.message(F.text == "❓ Задать вопрос")
async def ask_question(message: Message) -> None:
    from app.config import settings
    user = message.from_user
    question_text = "Напишите ваш вопрос в свободной форме."
    
    # Отправляем вопрос всем админам
    admin_message = (
        f"❓ Новый вопрос\n"
        f"От: @{user.username or 'N/A'} ({user.id})\n"
        f"Имя: {user.full_name or 'N/A'}\n\n"
        f"Вопрос будет отправлен после того, как пользователь его напишет."
    )
    
    sent_count = 0
    for admin_id in settings.allowed_admins:
        try:
            await message.bot.send_message(admin_id, admin_message)
            sent_count += 1
        except Exception as exc:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to notify admin {admin_id} about question: {exc}")
    
    if sent_count == 0:
        import logging
        logger = logging.getLogger(__name__)
        logger.error("Failed to notify any admin about question")
    
    await message.answer(
        question_text + "\nАдминистратор свяжется с вами в течение дня."
    )


@router.message(F.text.startswith("❓") == False, F.text != "🚪 Вход в Resonance", F.text != "🎁 Подарить подписку", F.text != "⬅️ Назад")
async def handle_question(message: Message, state: FSMContext) -> None:
    """Обработка вопроса пользователя (если не в состоянии оплаты/подарка)"""
    from app.config import settings
    
    # Проверяем, не находимся ли мы в состоянии оплаты или подарка
    current_state = await state.get_state()
    if current_state:
        state_str = str(current_state)
        if "PaymentFlow" in state_str or "GiftFlow" in state_str:
            # Пропускаем, если в состоянии оплаты/подарка - эти обработчики должны обработать сообщение
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Skipping handle_question for user {message.from_user.id}, state: {current_state}")
            return
    
    user = message.from_user
    
    # Отправляем вопрос всем админам
    admin_message = (
        f"❓ Вопрос от пользователя\n"
        f"От: @{user.username or 'N/A'} ({user.id})\n"
        f"Имя: {user.full_name or 'N/A'}\n\n"
        f"Вопрос:\n{message.text}"
    )
    
    sent_count = 0
    for admin_id in settings.allowed_admins:
        try:
            await message.bot.send_message(admin_id, admin_message)
            sent_count += 1
        except Exception as exc:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to notify admin {admin_id} about question: {exc}")
    
    if sent_count > 0:
        await message.answer(
            "✅ Ваш вопрос отправлен администратору.\n"
            "Мы свяжемся с вами в течение дня."
        )
    else:
        import logging
        logger = logging.getLogger(__name__)
        logger.error("Failed to send question to any admin")
        await message.answer("Произошла ошибка при отправке вопроса. Попробуйте позже.")


@router.message(F.text == "⬅️ Назад")
async def back_to_main(message: Message, state: FSMContext) -> None:
    # Сбрасываем состояние FSM при возврате в главное меню
    await state.clear()
    user = message.from_user
    await repository.upsert_user(user.id, user.username, user.full_name)
    await message.answer(
        "🧘 Добро пожаловать в поле Resonance!\n\n"
        "Месяц подписки — 9 999 ₸ / 1 515 ₽.\n"
        "Поле триединства: дух • душа • тело — в лице трёх мастеров.\n"
        "3 раза в неделю живые эфиры: сатсанги, практики, разборы, задания и новая информация.",
        reply_markup=main_menu,
    )


@router.message(F.text == "🔄 Старт")
async def start_button(message: Message, state: FSMContext) -> None:
    # Обработчик кнопки "Старт" - то же самое, что /start
    await cmd_start(message, state)
