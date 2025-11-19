from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import settings
from app.database.repository import init_db
from app.handlers import admin, bookings, payments, status, start
from app.services.sheets import sheets_manager
from app.services.subscriptions import setup_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


dp = Dispatcher(storage=MemoryStorage())
dp.include_router(start.router)
dp.include_router(bookings.router)
dp.include_router(payments.router)
dp.include_router(status.router)
dp.include_router(admin.router)


@dp.startup.register
async def on_startup(bot: Bot) -> None:
    await init_db()
    setup_scheduler(bot)
    if sheets_manager.enabled:
        logging.info("Google Sheets connected")
    await bot.send_message(settings.admin_id, "✅ Resonance Assistant запущен")


async def main() -> None:
    bot = Bot(token=settings.bot_token, parse_mode=ParseMode.MARKDOWN)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
