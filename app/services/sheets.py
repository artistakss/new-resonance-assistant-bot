from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

import gspread

from app.config import settings

logger = logging.getLogger(__name__)


class SheetsManager:
    def __init__(self) -> None:
        self.sheet = None
        creds = settings.google_credentials()
        if not creds or not settings.sheet_url:
            logger.warning("Google Sheets credentials are not configured; logging will be disabled")
            return
        try:
            client = gspread.service_account_from_dict(creds)
            self.sheet = client.open_by_url(settings.sheet_url).sheet1
            self._ensure_headers()
        except Exception as exc:  # pragma: no cover - network interaction
            logger.error("Failed to connect to Google Sheets: %s", exc)
            self.sheet = None

    @property
    def enabled(self) -> bool:
        return self.sheet is not None

    def _ensure_headers(self) -> None:
        if not self.sheet:
            return
        # Обновленная структура таблицы (без столбцов для бронирований)
        expected = [
            "Дата/Время",
            "user_id",
            "@username",
            "Метод",
            "ID чека",
            "Статус",
            "Начало подписки",
            "Окончание подписки",
            "Комментарий",
        ]
        current = self.sheet.row_values(1)
        # Обновляем заголовки, если они отличаются
        if len(current) < len(expected) or current[:len(expected)] != expected:
            # Обновляем только заголовки, не трогая данные
            self.sheet.update('A1:I1', [expected])

    def log_payment_check(
        self,
        user_id: int,
        username: str | None,
        method: str,
        file_id: str,
        status: str = "На проверке",
    ) -> Optional[int]:
        if not self.sheet:
            return None
        row = [
            datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
            user_id,
            username or 'N/A',
            method,
            file_id,
            status,
            "",
            "",
            "",
        ]
        self.sheet.append_row(row)
        return len(self.sheet.get_all_values())

    def update_payment_status(
        self,
        row_index: int,
        status: str,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> None:
        if not self.sheet:
            return
        data = [{"range": f'F{row_index}', "values": [[status]]}]
        if start and end:
            data.append({"range": f'G{row_index}', "values": [[start.strftime('%Y-%m-%d')]]})
            data.append({"range": f'H{row_index}', "values": [[end.strftime('%Y-%m-%d')]]})
        self.sheet.batch_update(data)

    def log_booking(self, user_id: int, username: str | None, mode: str, slot: str, note: str | None) -> None:
        if not self.sheet:
            return
        row = [
            datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
            user_id,
            username or 'N/A',
            f"Бронь {mode}",
            slot,
            'Создано',
            '',
            '',
            note or '',
        ]
        self.sheet.append_row(row)


sheets_manager = SheetsManager()
