#!/usr/bin/env python3
"""
Скрипт для тестирования функций бота без реальных уведомлений
Использование: python3 test_bot.py
"""

import asyncio
import sys
from pathlib import Path

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent))

from app.config import settings
from app.database.repository import init_db, get_user, list_payment_methods, get_payment_check
from app.services.sheets import sheets_manager


async def test_database():
    """Тестирование базы данных"""
    print("=" * 50)
    print("ТЕСТИРОВАНИЕ БАЗЫ ДАННЫХ")
    print("=" * 50)
    
    await init_db()
    print("✅ База данных инициализирована")
    
    # Проверка методов оплаты
    methods = await list_payment_methods()
    print(f"\n📋 Методы оплаты ({len(methods)}):")
    for method in methods:
        print(f"  - {method['method']}: {method['details'][:50]}...")
    
    print("\n✅ Тест базы данных пройден")


async def test_sheets():
    """Тестирование Google Sheets"""
    print("\n" + "=" * 50)
    print("ТЕСТИРОВАНИЕ GOOGLE SHEETS")
    print("=" * 50)
    
    if sheets_manager.enabled:
        print("✅ Google Sheets подключен")
        print(f"📊 URL таблицы: {settings.sheet_url}")
        
        # Проверка структуры таблицы
        if sheets_manager.sheet:
            headers = sheets_manager.sheet.row_values(1)
            print(f"\n📋 Заголовки таблицы ({len(headers)}):")
            for i, header in enumerate(headers, 1):
                print(f"  {i}. {header}")
    else:
        print("⚠️ Google Sheets не настроен (это нормально для тестирования)")
    
    print("\n✅ Тест Google Sheets пройден")


async def test_config():
    """Тестирование конфигурации"""
    print("\n" + "=" * 50)
    print("ТЕСТИРОВАНИЕ КОНФИГУРАЦИИ")
    print("=" * 50)
    
    print(f"🤖 Bot Token: {settings.bot_token[:10]}...")
    print(f"👤 Admin ID: {settings.admin_id}")
    print(f"✅ Checker ID: {settings.checker_id}")
    print(f"📢 Channel ID: {settings.channel_id}")
    print(f"🔗 Channel Link: {settings.channel_invite_link}")
    
    print(f"\n💰 Цены подписок:")
    print(f"  - 1 месяц: {settings.subscription_prices[30]:,} ₸ / {settings.subscription_prices_rub[30]:,} ₽")
    print(f"  - 3 месяца: {settings.subscription_prices[90]:,} ₸ / {settings.subscription_prices_rub[90]:,} ₽")
    print(f"  - 6 месяцев: {settings.subscription_prices[180]:,} ₸ / {settings.subscription_prices_rub[180]:,} ₽")
    
    print(f"\n👥 Разрешенные админы: {settings.allowed_admins}")
    
    print("\n✅ Тест конфигурации пройден")


async def main():
    """Главная функция тестирования"""
    print("\n" + "=" * 50)
    print("ТЕСТИРОВАНИЕ БОТА RESONANCE ASSISTANT")
    print("=" * 50)
    
    try:
        await test_config()
        await test_database()
        await test_sheets()
        
        print("\n" + "=" * 50)
        print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ")
        print("=" * 50)
        print("\n📝 Следующие шаги:")
        print("1. Откройте бота в Telegram")
        print("2. Отправьте /start")
        print("3. Следуйте инструкциям из ПЛАН_ТЕСТИРОВАНИЯ.md")
        print("\n💡 Совет: Для тестирования используйте свой Telegram ID")
        print(f"   Ваш ID можно узнать через @userinfobot")
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

