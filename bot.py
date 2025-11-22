from __future__ import annotations

import asyncio
import logging
import os
import socket

import aiohttp
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.session.aiohttp import AiohttpSession

# Принудительно используем IPv4 (решение от поддержки PS.kz)
os.environ['AIOHTTP_NO_EXTENSIONS'] = '1'


class IPv4AiohttpSession(AiohttpSession):
    """Кастомная сессия с принудительным использованием IPv4"""
    
    def __init__(self, *args, **kwargs):
        # Создаем IPv4 connector
        self._ipv4_connector = aiohttp.TCPConnector(family=socket.AF_INET)
        super().__init__(*args, **kwargs)
        # Сразу создаем сессию с IPv4 connector
        self._session = aiohttp.ClientSession(connector=self._ipv4_connector)

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
    try:
        await bot.send_message(settings.admin_id, "✅ Resonance Assistant запущен")
    except Exception as exc:
        logging.warning("Не удалось уведомить админа: %s", exc)


async def main() -> None:
    # Принудительно используем IPv4 (решение от поддержки PS.kz)
    # Создаем кастомную сессию с IPv4
    session = IPv4AiohttpSession()
    
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
        session=session,
    )
    
    logging.info("Starting bot with IPv4-only connection...")
    
    try:
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
        )
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
    except Exception as exc:
        logging.error("Fatal error in polling: %s", exc, exc_info=True)
        raise
    finally:
        await session.close()


if __name__ == "__main__":
    asyncio.run(main())
