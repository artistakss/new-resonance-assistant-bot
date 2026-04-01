from __future__ import annotations

import asyncio
import logging
import os
import socket

import aiohttp
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import settings
from bot.database.repository import init_db
from bot.handlers import admin, ask, bookings, gift, payments, status, start
from bot.services.sheets import sheets_manager
from bot.services.subscriptions import setup_scheduler

# Принудительно используем IPv4 (решение от поддержки PS.kz)
os.environ["AIOHTTP_NO_EXTENSIONS"] = "1"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


class IPv4AiohttpSession(AiohttpSession):
    """Кастомная сессия с принудительным использованием IPv4."""

    def __init__(self, *args, **kwargs):
        self._ipv4_connector = aiohttp.TCPConnector(family=socket.AF_INET)
        super().__init__(*args, **kwargs)
        self._session = aiohttp.ClientSession(connector=self._ipv4_connector)


dp = Dispatcher(storage=MemoryStorage())
dp.include_router(payments.router)  # PaymentFlow состояния
dp.include_router(gift.router)  # GiftFlow состояния
dp.include_router(bookings.router)  # BookingFlow состояния
dp.include_router(admin.router)  # Admin состояния
dp.include_router(ask.router)  # /ask команда
dp.include_router(start.router)
dp.include_router(status.router)


@dp.startup.register
async def on_startup(bot: Bot) -> None:
    await init_db()
    setup_scheduler(bot)
    if sheets_manager.enabled:
        logging.info("Google Sheets connected")
    for admin_id in settings.allowed_admins:
        try:
            await bot.send_message(admin_id, "✅ Resonance Assistant запущен")
        except Exception as exc:
            logging.warning("Не удалось уведомить админа %s: %s", admin_id, exc)


async def main() -> None:
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

