from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import List

from dotenv import load_dotenv

# Загружаем переменные из .env (для локальной разработки)
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")


def _env(key: str, default: str | None = None) -> str:
    value = os.getenv(key, default)
    if value is None:
        raise RuntimeError(f"Environment variable {key} is required but not set")
    return value


def _env_int(key: str, default: int | None = None) -> int:
    raw = os.getenv(key)
    if raw is None:
        if default is None:
            raise RuntimeError(f"Environment variable {key} is required but not set")
        return default
    return int(raw)


@dataclass
class Settings:
    bot_token: str
    admin_id: int
    checker_id: int
    channel_id: int
    channel_invite_link: str

    subscription_price: int = 9999
    subscription_duration_days: int = 30
    reminder_before_days: int = 3

    gspread_json_string: str = ""
    sheet_url: str = ""

    openai_api_key: str | None = None

    database_path: Path = field(default=Path("storage/bot.db"))

    @property
    def allowed_admins(self) -> List[int]:
        raw = os.getenv("ALLOWED_ADMINS")
        if raw:
            ids = {int(item.strip()) for item in raw.split(',') if item.strip()}
        else:
            ids = set()
        ids.update({self.admin_id, self.checker_id})
        return sorted(ids)

    def google_credentials(self) -> dict | None:
        if not self.gspread_json_string:
            return None
        try:
            return json.loads(self.gspread_json_string)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Invalid GSPREAD_JSON_STRING, expected JSON string") from exc


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        bot_token=_env("BOT_TOKEN"),
        admin_id=_env_int("ADMIN_ID"),
        checker_id=_env_int("CHECKER_ID"),
        channel_id=_env_int("CHANNEL_ID"),
        channel_invite_link=_env("CHANNEL_LINK"),
        subscription_price=_env_int("SUBSCRIPTION_PRICE", 20000),
        subscription_duration_days=_env_int("SUBSCRIPTION_DURATION_DAYS", 30),
        reminder_before_days=_env_int("REMINDER_BEFORE_DAYS", 3),
        gspread_json_string=os.getenv("GSPREAD_JSON_STRING", ""),
        sheet_url=os.getenv("SHEET_URL", ""),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        database_path=Path(os.getenv("DATABASE_PATH", "storage/bot.db")),
    )


settings = get_settings()
