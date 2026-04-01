from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.config import settings
from bot.database import repository

logger = logging.getLogger(__name__)


async def check_subscriptions(bot: Bot) -> None:
    now = datetime.utcnow()

    expired = await repository.get_users_with_expired(now)
    for user in expired:
        user_id = user["user_id"]
        try:
            await bot.ban_chat_member(chat_id=settings.channel_id, user_id=user_id, until_date=now)
            await bot.unban_chat_member(chat_id=settings.channel_id, user_id=user_id)
        except Exception as exc:
            logger.warning("Failed to remove expired user %s: %s", user_id, exc)
        await repository.deactivate_user(user_id)
        try:
            await bot.send_message(
                user_id,
                "⛔ Доступ к каналу временно закрыт. Ваша подписка истекла. "
                'Продлите её через кнопку "💳 Оплата подписки", чтобы вернуться.',
            )
        except Exception as exc:
            logger.debug("Cannot notify expired user %s: %s", user_id, exc)

    to_remind = await repository.get_users_to_remind(now, settings.reminder_before_days)
    for user in to_remind:
        user_id = user["user_id"]
        sub_end_raw = user["sub_end"]
        if not sub_end_raw:
            continue
        end = datetime.fromisoformat(sub_end_raw)
        try:
            await bot.send_message(
                user_id,
                f"⚠️ Срок подписки скоро закончится — {end:%d.%m.%Y}. "
                "Продлите доступ заранее, чтобы не потерять канал.",
            )
        except Exception as exc:
            logger.debug("Cannot notify user %s about reminder: %s", user_id, exc)


scheduler: Optional[AsyncIOScheduler] = None


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    global scheduler
    if scheduler:
        return scheduler

    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(check_subscriptions, "cron", hour=5, minute=0, args=(bot,))
    scheduler.start()
    logger.info("Subscription scheduler started")
    return scheduler

