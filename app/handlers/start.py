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
    await message.answer(
        "Напишите ваш вопрос в свободной форме."
        " Администратор свяжется с вами в течение дня."
    )


@router.message(F.text == "⬅️ Назад")
async def back_to_main(message: Message, state: FSMContext) -> None:
    # Сбрасываем состояние FSM при возврате в главное меню
    await state.clear()
    await message.answer(
        "🧘 Добро пожаловать в поле Resonance!\n\n"
        "Месяц подписки — 9 999 ₸ / 1 515 ₽.\n"
        "Поле триединства: дух • душа • тело — в лице трёх мастеров.\n"
        "3 раза в неделю живые эфиры: сатсанги, практики, разборы, задания и новая информация.",
        reply_markup=main_menu,
    )
