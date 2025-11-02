import time
from datetime import datetime
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.db.repo import (
    get_or_create_user,
    set_sleep_state,
    get_sleep_started_at,
    get_missed_during_sleep,
    reschedule,
)

router = Router()

def _fmt_ts(ts: float) -> str:
    return datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d %H:%M")

@router.message(Command("sleep"))
async def cmd_sleep(message: Message):
    user = get_or_create_user(message.from_user.id, message.from_user.username)
    set_sleep_state(user["id"], True)
    await message.answer("😴 Ок, не буду беспокоить, пока ты спишь.")

@router.message(Command("awake"))
async def cmd_awake(message: Message):
    user = get_or_create_user(message.from_user.id, message.from_user.username)
    user_id = int(user["id"])

    since = get_sleep_started_at(user_id)
    set_sleep_state(user_id, False)

    now = time.time()
    missed = get_missed_during_sleep(user_id, since_ts=since, now_ts=now)

    if not missed:
        await message.answer("🌞 Доброе! Пока ты спал, ничего не накопилось.")
        return

    lines = [f"🌞 Доброе! Пока ты спал, накопилось задач: {len(missed)}", ""]
    for i, row in enumerate(missed, start=1):
        name = row["task_name"]
        when = _fmt_ts(row["next_reminder_at"])
        interval = int(row["interval"])
        note = row["task_note"]
        lines.append(f"{i}. <b>{name}</b>")
        lines.append(f"   ⏰ было на: {when} | ⏱ {'разово' if interval <= 0 or row.get('is_one_shot', 0) else f'{interval} мин'}")
        if note:
            lines.append(f"   💬 {note}")
        lines.append("")
    await message.answer("\n".join(lines).strip())

    for row in missed:
        # переносим цикл к бодрствованию
        interval = int(row["interval"])
        next_ts = now + interval * 60 if interval > 0 else now  # для разовых не критично, их закроет deliver_reminder
        reschedule(row["id"], user_id, next_ts)
