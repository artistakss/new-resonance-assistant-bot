from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, List, Optional

import aiosqlite

from app.config import settings

DB_PATH = settings.database_path
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

CREATE_QUERIES: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        full_name TEXT,
        status TEXT DEFAULT 'inactive',
        sub_start TEXT,
        sub_end TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS payment_details (
        method TEXT PRIMARY KEY,
        label TEXT,
        details TEXT NOT NULL,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS payment_checks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        method TEXT NOT NULL,
        file_id TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        sheet_row INTEGER,
        duration_days INTEGER DEFAULT 30,
        price_kzt INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        mode TEXT NOT NULL,
        slot TEXT NOT NULL,
        note TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )
    """
)

DEFAULT_PAYMENT_METHODS = (
    ("Kaspi", "Kaspi Bank", "Укажите актуальные реквизиты Kaspi"),
    ("Tinkoff", "Tinkoff", "Укажите карту Tinkoff"),
    ("USDT", "USDT TRC-20", "Введите кошелек USDT"),
)


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH.as_posix()) as db:
        for query in CREATE_QUERIES:
            await db.execute(query)
        for method, label, details in DEFAULT_PAYMENT_METHODS:
            await db.execute(
                "INSERT OR IGNORE INTO payment_details(method, label, details) VALUES (?, ?, ?)",
                (method, label, details),
            )
        
        # Миграция: добавляем поля duration_days и price_kzt в payment_checks, если их нет
        try:
            await db.execute("ALTER TABLE payment_checks ADD COLUMN duration_days INTEGER DEFAULT 30")
        except aiosqlite.OperationalError:
            pass  # Поле уже существует
        
        try:
            await db.execute("ALTER TABLE payment_checks ADD COLUMN price_kzt INTEGER")
        except aiosqlite.OperationalError:
            pass  # Поле уже существует
        
        await db.commit()


async def upsert_user(user_id: int, username: str | None, full_name: str | None) -> None:
    async with aiosqlite.connect(DB_PATH.as_posix()) as db:
        await db.execute(
            """
            INSERT INTO users(user_id, username, full_name, status)
            VALUES(?, ?, ?, COALESCE((SELECT status FROM users WHERE user_id = ?), 'inactive'))
            ON CONFLICT(user_id) DO UPDATE SET
                username=excluded.username,
                full_name=excluded.full_name,
                updated_at=CURRENT_TIMESTAMP
            """,
            (user_id, username, full_name, user_id),
        )
        await db.commit()


async def get_user(user_id: int) -> Optional[aiosqlite.Row]:
    async with aiosqlite.connect(DB_PATH.as_posix()) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return await cursor.fetchone()


async def set_subscription_active(user_id: int, start: datetime, duration_days: int) -> tuple[datetime, datetime]:
    end = start + timedelta(days=duration_days)
    async with aiosqlite.connect(DB_PATH.as_posix()) as db:
        await db.execute(
            """
            UPDATE users SET status='active', sub_start=?, sub_end=?, updated_at=CURRENT_TIMESTAMP
            WHERE user_id=?
            """,
            (start.isoformat(), end.isoformat(), user_id),
        )
        await db.commit()
    return start, end


async def deactivate_user(user_id: int) -> None:
    async with aiosqlite.connect(DB_PATH.as_posix()) as db:
        await db.execute(
            "UPDATE users SET status='inactive', updated_at=CURRENT_TIMESTAMP WHERE user_id=?",
            (user_id,),
        )
        await db.commit()


async def get_active_users() -> List[aiosqlite.Row]:
    async with aiosqlite.connect(DB_PATH.as_posix()) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE status='active' AND sub_end IS NOT NULL")
        return await cursor.fetchall()


async def get_users_with_expired(checkpoint: datetime) -> List[aiosqlite.Row]:
    async with aiosqlite.connect(DB_PATH.as_posix()) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM users WHERE status='active' AND sub_end IS NOT NULL AND sub_end <= ?",
            (checkpoint.isoformat(),),
        )
        return await cursor.fetchall()


async def get_users_to_remind(checkpoint: datetime, days_before: int) -> List[aiosqlite.Row]:
    window_start = checkpoint
    window_end = checkpoint + timedelta(days=days_before)
    async with aiosqlite.connect(DB_PATH.as_posix()) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT * FROM users
            WHERE status='active' AND sub_end IS NOT NULL
              AND sub_end BETWEEN ? AND ?
            """,
            (window_start.isoformat(), window_end.isoformat()),
        )
        return await cursor.fetchall()


async def get_payment_details(method: str) -> str:
    async with aiosqlite.connect(DB_PATH.as_posix()) as db:
        cursor = await db.execute("SELECT details FROM payment_details WHERE method = ?", (method,))
        row = await cursor.fetchone()
        return row[0] if row else "Реквизиты не указаны"


async def update_payment_details(method: str, details: str) -> None:
    async with aiosqlite.connect(DB_PATH.as_posix()) as db:
        await db.execute(
            """
            INSERT INTO payment_details(method, label, details)
            VALUES(?, ?, ?)
            ON CONFLICT(method) DO UPDATE SET details=excluded.details, updated_at=CURRENT_TIMESTAMP
            """,
            (method, method, details),
        )
        await db.commit()


async def list_payment_methods() -> List[aiosqlite.Row]:
    async with aiosqlite.connect(DB_PATH.as_posix()) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT method, label, details FROM payment_details ORDER BY method")
        return await cursor.fetchall()


async def log_payment_check(
    user_id: int, 
    method: str, 
    file_id: str, 
    sheet_row: int | None,
    duration_days: int = 30,
    price_kzt: int | None = None,
) -> int:
    async with aiosqlite.connect(DB_PATH.as_posix()) as db:
        cursor = await db.execute(
            """
            INSERT INTO payment_checks(user_id, method, file_id, sheet_row, duration_days, price_kzt)
            VALUES(?, ?, ?, ?, ?, ?)
            """,
            (user_id, method, file_id, sheet_row, duration_days, price_kzt),
        )
        await db.commit()
        return cursor.lastrowid


async def get_payment_check(check_id: int) -> Optional[aiosqlite.Row]:
    """Получить информацию о чеке по ID"""
    async with aiosqlite.connect(DB_PATH.as_posix()) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM payment_checks WHERE id = ?", (check_id,))
        return await cursor.fetchone()


async def update_payment_check_status(check_id: int, status: str) -> None:
    async with aiosqlite.connect(DB_PATH.as_posix()) as db:
        await db.execute(
            "UPDATE payment_checks SET status=?, created_at=created_at WHERE id=?",
            (status, check_id),
        )
        await db.commit()


async def add_booking(user_id: int, mode: str, slot: str, note: str | None = None) -> int:
    async with aiosqlite.connect(DB_PATH.as_posix()) as db:
        cursor = await db.execute(
            "INSERT INTO bookings(user_id, mode, slot, note) VALUES(?, ?, ?, ?)",
            (user_id, mode, slot, note),
        )
        await db.commit()
        return cursor.lastrowid


async def list_recent_bookings(limit: int = 10) -> List[aiosqlite.Row]:
    async with aiosqlite.connect(DB_PATH.as_posix()) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM bookings ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        return await cursor.fetchall()


