# Resonance Assistant Bot

Новый Telegram-бот на **Aiogram 3**, рассчитанный на:
- продажу доступа в приватный канал;
- проверку чеков и уведомление админов;
- отслеживание подписок и автопроверку истёкших пользователей;
- запись на онлайн/оффлайн консультации;
- интеграцию с Google Sheets (логирование платежей и записей).

## Требования
- Python 3.11
- Установленные зависимости из `requirements.txt`
- Токен Telegram-бота, данные Google Service Account, параметры канала

## Быстрый старт
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # заполните значениями
python bot.py
```

## Переменные окружения
Все настройки перечислены в `.env.example`. Ключевые:
- `BOT_TOKEN` — токен бота
- `ADMIN_ID`, `CHECKER_ID` — телеграм ID основного администратора и проверяющего чеков
- `CHANNEL_ID`, `CHANNEL_LINK` — ID и пригласительная ссылка приватного канала
- `SUBSCRIPTION_PRICE`, `SUBSCRIPTION_DURATION_DAYS`, `REMINDER_BEFORE_DAYS`
- `GSPREAD_JSON_STRING`, `SHEET_URL` — ключ сервисного аккаунта (в одну строку) и ссылка на таблицу

## Архитектура
- `bot.py` — точка входа, настраивает Dispatcher и запускает планировщик подписок
- `app/config.py` — централизованные настройки
- `app/database/repository.py` — работа с SQLite (пользователи, подписки, реквизиты, брони)
- `app/services/` — интеграции (Google Sheets, APScheduler)
- `app/handlers/` — модульные роутеры Aiogram (старт, оплаты, подписка, админ-панель, записи)
- `app/keyboards/` — Reply/Inline клавиатуры

## Развёртывание на PS Clouds
1. Создайте сервис (Ubuntu) и установите зависимости: `sudo apt update && sudo apt install python3.11 python3.11-venv git`.
2. Склонируйте проект или загрузите архив: `git clone <repo> && cd resonance-assistant-main`.
3. Настройте виртуальное окружение и зависимости (см. «Быстрый старт»).
4. Создайте файл `.env` с боевыми значениями.
5. Запускайте через `python bot.py` или создайте systemd unit/PM2-процесс. Пример systemd:
```
[Unit]
Description=Resonance Assistant Bot
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/resonance-assistant-main
ExecStart=/home/ubuntu/resonance-assistant-main/.venv/bin/python bot.py
Restart=always
EnvironmentFile=/home/ubuntu/resonance-assistant-main/.env

[Install]
WantedBy=multi-user.target
```
6. Перезапустите сервис: `sudo systemctl enable --now resonance-bot.service`.

## Планировщик подписок
`apscheduler` ежедневно (05:00 UTC) проверяет базу, удаляет просроченных пользователей из канала и шлёт напоминания за `REMINDER_BEFORE_DAYS`. Для корректной работы бот должен быть админом канала с правом блокировать/разблокировать участников.

## Google Sheets
`app/services/sheets.py` логирует чеки и записи. Если ключи не заданы — интеграция автоматически отключается, бот продолжает работать локально.

## Дальнейшие шаги
- Подключить OpenAI/задачу «/ask», если потребуется умный помощник.
- Добавить вебхуки (например, FastAPI) для хостинга без `polling`.
- Подключить платёжные API (Kaspi, PayBox и т.п.) при необходимости автоматизации.
