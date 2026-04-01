from __future__ import annotations

import logging
import time
from typing import Dict, Literal

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.enums import ChatAction
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.services import ai
from bot.services.memory import add_message, clear_history, get_history

router = Router()
logger = logging.getLogger(__name__)

ModeId = Literal["assistant", "business", "teacher"]

_MODE_PROMPTS: Dict[ModeId, str] = {
    "assistant": (
        "Ты — полезный ассистент в Telegram-боте Resonance. "
        "Отвечай кратко и по делу. Если информации недостаточно — задай уточняющий вопрос."
    ),
    "business": (
        "Ты — бизнес-консультант. Дай структурированный ответ: 1) краткий вывод, 2) варианты, 3) риски, 4) следующий шаг. "
        "Задавай уточняющие вопросы, если данных недостаточно."
    ),
    "teacher": (
        "Ты — преподаватель. Объясняй простыми словами, по шагам, с небольшими примерами. "
        "В конце задай 1 уточняющий вопрос, чтобы проверить понимание."
    ),
}

_MODE_LABELS: Dict[ModeId, str] = {
    "assistant": "🤖 Обычный ассистент",
    "business": "💼 Бизнес-консультант",
    "teacher": "📚 Объясняет как учитель",
}

_user_mode: Dict[int, ModeId] = {}

_last_request_ts: Dict[int, float] = {}
_RATE_LIMIT_SECONDS = 2.0


def _actions_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🧹 Очистить память", callback_data="ask:clear"),
                InlineKeyboardButton(text="💬 Новый диалог", callback_data="ask:new"),
            ],
            [
                InlineKeyboardButton(text="🎛 Режим", callback_data="ask:mode_menu"),
            ],
        ]
    )


def _mode_kb(active: ModeId) -> InlineKeyboardMarkup:
    def _btn(mode: ModeId) -> InlineKeyboardButton:
        prefix = "✅ " if mode == active else ""
        return InlineKeyboardButton(text=f"{prefix}{_MODE_LABELS[mode]}", callback_data=f"ask:mode:{mode}")

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_btn("assistant")],
            [_btn("business")],
            [_btn("teacher")],
        ]
    )


@router.message(Command("ask"))
async def ask_cmd(message: Message, command: CommandObject) -> None:
    text = (command.args or "").strip()
    if not text:
        await message.answer('Напиши вопрос после команды: `/ask как оплатить?`', parse_mode="Markdown")
        return

    user_id = message.from_user.id

    now = time.monotonic()
    last_ts = _last_request_ts.get(user_id, 0.0)
    if now - last_ts < _RATE_LIMIT_SECONDS:
        await message.answer("⏳ Слишком часто. Подожди 2 секунды и попробуй ещё раз.", reply_markup=_actions_kb())
        return
    _last_request_ts[user_id] = now

    mode = _user_mode.get(user_id, "assistant")
    system_prompt = _MODE_PROMPTS[mode]

    add_message(user_id, "user", text)
    history = get_history(user_id)

    try:
        try:
            await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
        except Exception:
            pass

        answer = await ai.chat_completion([{"role": "system", "content": system_prompt}, *history])
    except ai.OpenAIChatError as exc:
        msg = str(exc)
        if "OPENAI_API_KEY is not set" in msg:
            await message.answer("AI-помощник сейчас отключён (не задан `OPENAI_API_KEY`).", reply_markup=_actions_kb())
        else:
            await message.answer(msg or "⚠️ Ошибка при обращении к AI. Попробуй позже.", reply_markup=_actions_kb())
        return
    except Exception as exc:
        logger.error("AI /ask failed: %s", exc, exc_info=True)
        await message.answer("⚠️ Ошибка при обращении к AI. Попробуй позже.", reply_markup=_actions_kb())
        return

    add_message(user_id, "assistant", answer)
    await message.answer(answer, reply_markup=_actions_kb())


@router.message(Command("ask_reset"))
async def ask_reset_cmd(message: Message) -> None:
    clear_history(message.from_user.id)
    await message.answer("Память диалога очищена. Можешь снова писать через /ask.", reply_markup=_actions_kb())


@router.callback_query(F.data == "ask:clear")
async def ask_clear_cb(call: CallbackQuery) -> None:
    clear_history(call.from_user.id)
    await call.answer("Память очищена")
    if call.message:
        await call.message.answer("🧹 Память диалога очищена. Пиши новый вопрос через /ask.", reply_markup=_actions_kb())


@router.callback_query(F.data == "ask:new")
async def ask_new_cb(call: CallbackQuery) -> None:
    clear_history(call.from_user.id)
    await call.answer("Новый диалог")
    if call.message:
        await call.message.answer("💬 Начали новый диалог. Напиши: `/ask ...`", parse_mode="Markdown", reply_markup=_actions_kb())


@router.callback_query(F.data == "ask:mode_menu")
async def ask_mode_menu_cb(call: CallbackQuery) -> None:
    user_id = call.from_user.id
    mode = _user_mode.get(user_id, "assistant")
    await call.answer()
    if call.message:
        await call.message.answer("Выбери режим ассистента:", reply_markup=_mode_kb(mode))


@router.callback_query(F.data.startswith("ask:mode:"))
async def ask_mode_set_cb(call: CallbackQuery) -> None:
    user_id = call.from_user.id
    raw = call.data.split(":", 2)[2]
    if raw not in _MODE_PROMPTS:
        await call.answer("Неизвестный режим", show_alert=True)
        return
    mode: ModeId = raw  # type: ignore[assignment]
    _user_mode[user_id] = mode
    await call.answer("Режим сохранён")
    if call.message:
        await call.message.answer(f"✅ Режим: {_MODE_LABELS[mode]}\nТеперь пиши через `/ask ...`", parse_mode="Markdown", reply_markup=_actions_kb())

