import time
from datetime import datetime
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from zoneinfo import ZoneInfo


from app.db.repo import (
    get_or_create_user,
    set_sleep_state,
    get_sleep_started_at,
    get_missed_during_sleep,
    reschedule,
)

router = Router()

def _fmt_ts(ts: float, tz: str = "Europe/Warsaw") -> str:
    return datetime.fromtimestamp(float(ts), ZoneInfo(tz)).strftime("%Y-%m-%d %H:%M")

@router.message(Command("sleep"))
async def cmd_sleep(message: Message):
    user = get_or_create_user(message.from_user.id, message.from_user.username)
    set_sleep_state(user["id"], True)
    await message.answer("😴 Ок, не буду беспокоить, пока ты спишь.")

@router.message(Command("awake"))
async def cmd_awake(message: Message):
    print(">> /awake received from", message.from_user.id)  # debug
    user = get_or_create_user(message.from_user.id, message.from_user.username)
    user_id = int(user["id"])

    # Получаем начало последнего сна
    since = get_sleep_started_at(user_id)
    print(">> sleep_started_at:", since)  # debug

    set_sleep_state(user_id, False)  # пробуждаем

    now = time.time()
    missed = get_missed_during_sleep(user_id, since_ts=since, now_ts=now)
    print(">> missed found:", len(missed) if missed else 0)  # debug

    tz = user["timezone"] if "timezone" in user.keys() and user["timezone"] else "Europe/Warsaw"

    # Если задач нет — всегда отвечаем!
    if not missed:
        await message.answer("🌞 Доброе! Пока ты спал, ничего не накопилось.")
        print(">> answered: nothing missed")  # debug
        return

    # Сводка задач
    lines = [f"🌞 Доброе! Пока ты спал, накопилось задач: {len(missed)}", ""]
    for i, row in enumerate(missed, start=1):
        name = row["task_name"]
        when = datetime.fromtimestamp(row["next_reminder_at"], ZoneInfo(tz)).strftime("%Y-%m-%d %H:%M")
        interval = int(row["interval"])
        note = row["task_note"]
        one_shot = bool(row.get("is_one_shot", 0))
        interval_str = "разово" if one_shot or interval <= 0 else f"{interval} мин"
        lines.append(f"{i}. <b>{name}</b>")
        lines.append(f"   ⏰ было на: {when} | ⏱ {interval_str}")
        if note:
            lines.append(f"   💬 {note}")
        lines.append("")
    await message.answer("\n".join(lines).strip())
    print(">> answered: missed summary sent")  # debug

    # Сдвигаем задачи на следующее напоминание (если надо)
    for row in missed:
        interval = int(row["interval"])
        next_ts = now + interval * 60 if interval > 0 else now
        reschedule(row["id"], user_id, next_ts)