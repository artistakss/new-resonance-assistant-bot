from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.database import repository
from bot.keyboards.main import main_menu

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
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
    from bot.config import settings

    user = message.from_user
    question_text = "Напишите ваш вопрос в свободной форме."

    admin_message = (
        "❓ Новый вопрос\n"
        f"От: @{user.username or 'N/A'} ({user.id})\n"
        f"Имя: {user.full_name or 'N/A'}\n\n"
        "Вопрос будет отправлен после того, как пользователь его напишет."
    )

    sent_count = 0
    for admin_id in settings.allowed_admins:
        try:
            await message.bot.send_message(admin_id, admin_message)
            sent_count += 1
        except Exception as exc:
            import logging

            logger = logging.getLogger(__name__)
            logger.warning("Failed to notify admin %s about question: %s", admin_id, exc)

    if sent_count == 0:
        import logging

        logger = logging.getLogger(__name__)
        logger.error("Failed to notify any admin about question")

    await message.answer(question_text + "\nАдминистратор свяжется с вами в течение дня.")


@router.message(F.text == "🔄 Старт")
async def start_button(message: Message, state: FSMContext) -> None:
    await cmd_start(message, state)


@router.message(
    F.text.startswith("❓") == False,
    F.text != "🚪 Вход в Resonance",
    F.text != "🎁 Подарить подписку",
    F.text != "⬅️ Назад",
    F.text != "🔄 Старт",
)
async def handle_question(message: Message, state: FSMContext) -> None:
    """Обработка вопроса пользователя (если не в состоянии оплаты/подарка)."""
    from bot.config import settings

    current_state = await state.get_state()
    if current_state:
        state_str = str(current_state)
        if "PaymentFlow" in state_str or "GiftFlow" in state_str:
            import logging

            logger = logging.getLogger(__name__)
            logger.info("Skipping handle_question for user %s, state: %s", message.from_user.id, current_state)
            return

    user = message.from_user

    admin_message = (
        "❓ Вопрос от пользователя\n"
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
            logger.warning("Failed to notify admin %s about question: %s", admin_id, exc)

    if sent_count > 0:
        await message.answer("✅ Ваш вопрос отправлен администратору.\nМы свяжемся с вами в течение дня.")
    else:
        import logging

        logger = logging.getLogger(__name__)
        logger.error("Failed to send question to any admin")
        await message.answer("Произошла ошибка при отправке вопроса. Попробуйте позже.")


@router.message(F.text == "⬅️ Назад")
async def back_to_main(message: Message, state: FSMContext) -> None:
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

