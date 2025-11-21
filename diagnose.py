#!/usr/bin/env python3
"""Скрипт диагностики для проверки конфигурации бота на сервере"""

import os
import sys
from pathlib import Path

print("=" * 60)
print("🔍 ДИАГНОСТИКА RESONANCE ASSISTANT BOT")
print("=" * 60)
print()

# 1. Проверка Python версии
print("1️⃣ Python версия:")
print(f"   Python: {sys.version}")
print(f"   Версия: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
if sys.version_info < (3, 8):
    print("   ⚠️  ВНИМАНИЕ: Требуется Python 3.8+")
else:
    print("   ✅ Версия Python подходит")
print()

# 2. Проверка рабочей директории
print("2️⃣ Рабочая директория:")
cwd = Path.cwd()
print(f"   Текущая: {cwd}")
print(f"   Существует: {cwd.exists()}")
print(f"   Права: {oct(cwd.stat().st_mode)[-3:]}")
print()

# 3. Проверка .env файла
print("3️⃣ Файл .env:")
env_path = cwd / ".env"
print(f"   Путь: {env_path}")
print(f"   Существует: {env_path.exists()}")
if env_path.exists():
    print(f"   Размер: {env_path.stat().st_size} байт")
    print(f"   Права: {oct(env_path.stat().st_mode)[-3:]}")
    # Проверка содержимого (без показа секретов)
    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            required_vars = ['BOT_TOKEN', 'ADMIN_ID', 'CHECKER_ID', 'CHANNEL_ID', 'CHANNEL_LINK']
            found_vars = []
            for line in lines:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    var_name = line.split('=')[0].strip()
                    if var_name in required_vars:
                        found_vars.append(var_name)
            print(f"   Найдено обязательных переменных: {len(found_vars)}/{len(required_vars)}")
            missing = set(required_vars) - set(found_vars)
            if missing:
                print(f"   ⚠️  Отсутствуют: {', '.join(missing)}")
            else:
                print("   ✅ Все обязательные переменные найдены")
    except Exception as e:
        print(f"   ❌ Ошибка чтения: {e}")
else:
    print("   ❌ Файл .env не найден!")
print()

# 4. Проверка bot.py
print("4️⃣ Файл bot.py:")
bot_path = cwd / "bot.py"
print(f"   Путь: {bot_path}")
print(f"   Существует: {bot_path.exists()}")
if bot_path.exists():
    print(f"   Права: {oct(bot_path.stat().st_mode)[-3:]}")
print()

# 5. Проверка директории storage
print("5️⃣ Директория storage:")
storage_path = cwd / "storage"
print(f"   Путь: {storage_path}")
print(f"   Существует: {storage_path.exists()}")
if storage_path.exists():
    print(f"   Права: {oct(storage_path.stat().st_mode)[-3:]}")
    db_path = storage_path / "bot.db"
    print(f"   База данных: {db_path.exists()}")
else:
    print("   ⚠️  Директория не существует (будет создана автоматически)")
print()

# 6. Проверка виртуального окружения
print("6️⃣ Виртуальное окружение:")
venv_path = cwd / ".venv"
print(f"   Путь: {venv_path}")
print(f"   Существует: {venv_path.exists()}")
if venv_path.exists():
    python_path = venv_path / "bin" / "python"
    print(f"   Python: {python_path.exists()}")
    if python_path.exists():
        try:
            import subprocess
            result = subprocess.run(
                [str(python_path), "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            print(f"   Версия: {result.stdout.strip()}")
        except Exception as e:
            print(f"   ⚠️  Не удалось проверить версию: {e}")
else:
    print("   ❌ Виртуальное окружение не найдено!")
print()

# 7. Проверка импортов
print("7️⃣ Проверка импортов:")
try:
    import aiogram
    print(f"   ✅ aiogram: {aiogram.__version__}")
except ImportError as e:
    print(f"   ❌ aiogram: {e}")

try:
    import aiosqlite
    print(f"   ✅ aiosqlite: {aiosqlite.__version__}")
except ImportError as e:
    print(f"   ❌ aiosqlite: {e}")

try:
    import dotenv
    print(f"   ✅ python-dotenv: установлен")
except ImportError as e:
    print(f"   ❌ python-dotenv: {e}")

try:
    import gspread
    print(f"   ✅ gspread: {gspread.__version__}")
except ImportError as e:
    print(f"   ⚠️  gspread: {e} (опционально)")

try:
    import apscheduler
    print(f"   ✅ apscheduler: {apscheduler.__version__}")
except ImportError as e:
    print(f"   ❌ apscheduler: {e}")
print()

# 8. Проверка конфигурации приложения
print("8️⃣ Проверка конфигурации приложения:")
try:
    # Добавляем текущую директорию в путь
    if str(cwd) not in sys.path:
        sys.path.insert(0, str(cwd))
    
    from app.config import settings
    print("   ✅ Модуль config загружен")
    print(f"   Admin ID: {settings.admin_id}")
    print(f"   Checker ID: {settings.checker_id}")
    print(f"   Channel ID: {settings.channel_id}")
    print(f"   Database path: {settings.database_path}")
    print(f"   Database exists: {settings.database_path.exists()}")
except Exception as e:
    print(f"   ❌ Ошибка загрузки конфигурации: {e}")
    import traceback
    print("   Детали:")
    for line in traceback.format_exc().split('\n'):
        if line.strip():
            print(f"      {line}")
print()

# 9. Проверка переменных окружения
print("9️⃣ Переменные окружения:")
env_vars = ['BOT_TOKEN', 'ADMIN_ID', 'CHECKER_ID', 'CHANNEL_ID', 'CHANNEL_LINK']
for var in env_vars:
    value = os.getenv(var)
    if value:
        masked = value[:10] + "..." if len(value) > 10 else value
        print(f"   ✅ {var}: {masked}")
    else:
        print(f"   ❌ {var}: не установлена")
print()

print("=" * 60)
print("✅ Диагностика завершена")
print("=" * 60)

