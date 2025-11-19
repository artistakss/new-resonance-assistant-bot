from aiogram import F, Router
from aiogram.types import Message

from app.database import repository

router = Router()


@router.message(F.text == "🧾 Статус подписки")
async def status_handler(message: Message) -> None:
    user = await repository.get_user(message.from_user.id)
    if not user or user["status"] != "active" or not user["sub_end"]:
        await message.answer("У вас нет активной подписки. Оформите её через кнопку \"💳 Оплата подписки\".")
        return
    await message.answer(
        f"Доступ активен до {user['sub_end'][:10]}\n"
        "Если вам нужна помощь с продлением, нажмите \"💳 Оплата подписки\".",
    )
