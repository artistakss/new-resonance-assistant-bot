from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import List

from dotenv import load_dotenv

# Загружаем переменные из .env
# Пробуем несколько путей: рядом с config.py, в рабочей директории, в корне проекта
env_paths = [
    Path(__file__).resolve().parent.parent / ".env",  # Рядом с bot.py
    Path.cwd() / ".env",  # В текущей рабочей директории
    Path.home() / "resonance-assistant" / ".env",  # В домашней директории
]
for env_path in env_paths:
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=False)
        break
else:
    # Если не нашли, пробуем загрузить из текущей директории (может быть установлен через systemd EnvironmentFile)
    load_dotenv(override=False)


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


def _resolve_database_path(path_str: str) -> Path:
    """Разрешает путь к базе данных относительно рабочей директории"""
    path = Path(path_str)
    if path.is_absolute():
        return path
    # Относительный путь - разрешаем относительно рабочей директории
    return Path.cwd() / path


@dataclass
class Settings:
    bot_token: str
    admin_id: int
    channel_id: int
    channel_invite_link: str

    subscription_price: int = 9999  # Цена за 1 месяц (для обратной совместимости)
    subscription_duration_days: int = 30
    reminder_before_days: int = 3
    
    # Цены для разных вариантов подписки (в тенге)
    subscription_prices: dict[int, int] = field(default_factory=lambda: {
        30: 9999,   # 1 месяц
        90: 25000,  # 3 месяца (выгоднее на ~5000)
        180: 45000, # 6 месяцев (выгоднее на ~15000)
    })
    
    # Цены в рублях (для отображения)
    subscription_prices_rub: dict[int, int] = field(default_factory=lambda: {
        30: 1515,   # 1 месяц
        90: 3788,   # 3 месяца
        180: 6818,  # 6 месяцев
    })

    gspread_json_string: str = ""
    sheet_url: str = ""

    openai_api_key: str | None = None

    database_path: Path = field(default=Path("storage/bot.db"))

    @property
    def allowed_admins(self) -> List[int]:
        """Список всех админов (из ADMIN_ID и ALLOWED_ADMINS)"""
        raw = os.getenv("ALLOWED_ADMINS")
        if raw:
            ids = {int(item.strip()) for item in raw.split(',') if item.strip()}
        else:
            ids = set()
        # Добавляем основной admin_id
        ids.add(self.admin_id)
        return sorted(ids)
    
    @property
    def checker_id(self) -> int:
        """Для обратной совместимости - возвращает первый админ из списка"""
        return self.allowed_admins[0] if self.allowed_admins else self.admin_id

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
        channel_id=_env_int("CHANNEL_ID"),
        channel_invite_link=_env("CHANNEL_LINK"),
        subscription_price=_env_int("SUBSCRIPTION_PRICE", 20000),
        subscription_duration_days=_env_int("SUBSCRIPTION_DURATION_DAYS", 30),
        reminder_before_days=_env_int("REMINDER_BEFORE_DAYS", 3),
        gspread_json_string=os.getenv("GSPREAD_JSON_STRING", ""),
        sheet_url=os.getenv("SHEET_URL", ""),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        database_path=_resolve_database_path(os.getenv("DATABASE_PATH", "storage/bot.db")),
    )


settings = get_settings()
