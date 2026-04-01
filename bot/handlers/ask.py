from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.services import ai
from bot.services.memory import add_message, clear_history, get_history

router = Router()
logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "Ты — полезный ассистент в Telegram-боте Resonance. "
    "Отвечай кратко и по делу. Если информации недостаточно — задай уточняющий вопрос."
)

_ASK_ACTIONS_KB = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="🧹 Очистить память", callback_data="ask:clear"),
            InlineKeyboardButton(text="💬 Новый диалог", callback_data="ask:new"),
        ]
    ]
)


@router.message(Command("ask"))
async def ask_cmd(message: Message, command: CommandObject) -> None:
    text = (command.args or "").strip()
    if not text:
        await message.answer('Напиши вопрос после команды: `/ask как оплатить?`', parse_mode="Markdown")
        return

    user_id = message.from_user.id

    add_message(user_id, "user", text)
    history = get_history(user_id)

    try:
        answer = await ai.chat_completion([{"role": "system", "content": _SYSTEM_PROMPT}, *history])
    except ai.OpenAIChatError:
        await message.answer("AI-помощник сейчас отключён (не задан `OPENAI_API_KEY`).")
        return
    except Exception as exc:
        logger.error("AI /ask failed: %s", exc, exc_info=True)
        await message.answer("Не получилось получить ответ от AI. Попробуй позже.")
        return

    add_message(user_id, "assistant", answer)
    await message.answer(answer, reply_markup=_ASK_ACTIONS_KB)


@router.message(Command("ask_reset"))
async def ask_reset_cmd(message: Message) -> None:
    clear_history(message.from_user.id)
    await message.answer("Память диалога очищена. Можешь снова писать через /ask.")


@router.callback_query(F.data == "ask:clear")
async def ask_clear_cb(call: CallbackQuery) -> None:
    clear_history(call.from_user.id)
    await call.answer("Память очищена")
    if call.message:
        await call.message.answer("🧹 Память диалога очищена. Пиши новый вопрос через /ask.", reply_markup=_ASK_ACTIONS_KB)


@router.callback_query(F.data == "ask:new")
async def ask_new_cb(call: CallbackQuery) -> None:
    clear_history(call.from_user.id)
    await call.answer("Новый диалог")
    if call.message:
        await call.message.answer("💬 Начали новый диалог. Напиши: `/ask ...`", parse_mode="Markdown", reply_markup=_ASK_ACTIONS_KB)

