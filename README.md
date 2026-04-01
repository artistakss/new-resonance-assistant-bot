# 🤖 Resonance Assistant — AI Telegram Bot

## 📌 About
Production-oriented Telegram bot built with **aiogram 3**.
It helps run a private community: handles **subscription access**, **payment proof checks**, **admin moderation**, **booking requests**, and includes an **AI assistant** with short-term conversation memory.

## 🚀 Features
- **Subscriptions**: activate access, track expiry, reminders, auto-remove expired users from the channel (scheduler)
- **Payments**: user sends photo/PDF proof → admins get a review message with approve/reject actions
- **Admin panel**: manage payment details, view active subscribers, recent bookings
- **Bookings**: online/offline booking requests + admin notifications
- **Google Sheets (optional)**: log payments and bookings when configured
- **AI assistant (optional)**: `/ask` with **memory of last 5 messages** per user + inline buttons to reset

## 🛠 Tech Stack
- Python 3.11
- aiogram 3
- SQLite (`aiosqlite`)
- APScheduler
- Google Sheets (`gspread`) — optional
- OpenAI API — optional
- `python-dotenv`, `httpx`

## ⚙️ Setup
```bash
git clone https://github.com/artistakss/new-resonance-assistant-bot
cd resonance-assistant-main
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python main.py
```

## 🔐 Environment variables
All settings are listed in `.env.example`. Key ones:
- `BOT_TOKEN`
- `ADMIN_ID`, `ALLOWED_ADMINS`
- `CHANNEL_ID`, `CHANNEL_LINK`
- `DATABASE_PATH`
- `GSPREAD_JSON_STRING`, `SHEET_URL` (optional)
- `OPENAI_API_KEY` (optional, enables `/ask`)

## 🧠 AI assistant (memory + UI)
- Ask: `/ask <your question>`
- Reset memory: `/ask_reset`
- Inline buttons under `/ask` answers:
  - **🧹 Очистить память**
  - **💬 Новый диалог**

## ✅ Use cases
- **Personal assistant**: quick Q&A with short-term context using `/ask` (last 5 messages memory)
- **Customer support bot**: collect questions from users and forward them to admins; keep conversation context for follow-ups
- **FAQ automation**: answer common questions (pricing, access, schedule) and reduce admin workload
- **Paid community access**: manage subscriptions, review payment proofs, and automate access control in a private channel

## 🧱 Project structure
- `main.py` — entrypoint (dispatcher, routers, scheduler)
- `bot/handlers/` — message/callback handlers
- `bot/services/` — integrations (OpenAI, Sheets, scheduler, memory)
- `bot/database/` — SQLite repository
- `bot/keyboards/` — reply/inline keyboards

## 📷 Demo
Add screenshots/GIFs of:
- payment proof flow + admin approve/reject
- `/ask` memory + inline buttons

## 📈 Future Improvements
- Persist AI memory in DB (instead of RAM)
- Webhooks (FastAPI) for deployment without long polling
- Role-based assistant modes (user/admin/expert)

## Развёртывание на PS Clouds
1. Создайте сервис (Ubuntu) и установите зависимости: `sudo apt update && sudo apt install python3.11 python3.11-venv git`.
2. Склонируйте проект или загрузите архив: `git clone <repo> && cd resonance-assistant-main`.
3. Настройте виртуальное окружение и зависимости (см. «Быстрый старт»).
4. Создайте файл `.env` с боевыми значениями.
5. Запускайте через `python main.py` или создайте systemd unit/PM2-процесс. Пример systemd:
```
[Unit]
Description=Resonance Assistant Bot
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/resonance-assistant-main
ExecStart=/home/ubuntu/resonance-assistant-main/.venv/bin/python main.py
Restart=always
EnvironmentFile=/home/ubuntu/resonance-assistant-main/.env

[Install]
WantedBy=multi-user.target
```
6. Перезапустите сервис: `sudo systemctl enable --now resonance-bot.service`.

## Планировщик подписок
`apscheduler` ежедневно (05:00 UTC) проверяет базу, удаляет просроченных пользователей из канала и шлёт напоминания за `REMINDER_BEFORE_DAYS`. Для корректной работы бот должен быть админом канала с правом блокировать/разблокировать участников.

## Google Sheets
`bot/services/sheets.py` логирует чеки и записи. Если ключи не заданы — интеграция автоматически отключается, бот продолжает работать локально.
