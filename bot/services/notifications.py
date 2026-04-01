"""Утилиты для отправки уведомлений админам."""

import logging
from typing import Optional

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup

from bot.config import settings

logger = logging.getLogger(__name__)


async def notify_admins_about_check(
    bot: Bot,
    photo_file_id: Optional[str] = None,
    document_file_id: Optional[str] = None,
    caption: str = "",
    reply_markup: Optional[InlineKeyboardMarkup] = None,
) -> int:
    """
    Отправляет уведомление о чеке всем админам.

    Returns:
        Количество успешно отправленных уведомлений
    """
    sent_count = 0

    for admin_id in settings.allowed_admins:
        try:
            if photo_file_id:
                await bot.send_photo(
                    admin_id,
                    photo=photo_file_id,
                    caption=caption,
                    reply_markup=reply_markup,
                    parse_mode=None,
                )
                sent_count += 1
            elif document_file_id:
                await bot.send_document(
                    admin_id,
                    document=document_file_id,
                    caption=caption,
                    reply_markup=reply_markup,
                    parse_mode=None,
                )
                sent_count += 1
            else:
                await bot.send_message(
                    admin_id,
                    caption,
                    reply_markup=reply_markup,
                    parse_mode=None,
                )
                sent_count += 1
        except Exception as exc:
            logger.warning("Failed to send check notification to admin %s: %s", admin_id, exc)

    if sent_count > 0:
        logger.info("Check notification sent to %s admin(s)", sent_count)
    else:
        logger.error("Failed to send check notification to any admin")

    return sent_count

