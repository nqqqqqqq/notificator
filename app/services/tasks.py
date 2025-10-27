# app/services/tasks.py
import time
from aiogram import Bot
from app.db import repo

async def deliver_reminder(bot: Bot, task_row) -> bool:
    """
    Отправляет напоминание по одной задаче и сдвигает её next_reminder_at на следующий интервал.
    Возвращает True, если всё прошло хорошо.
    """
    user_id = task_row["user_id"]
    task_id = task_row["id"]
    name = task_row["task_name"]
    note = task_row["task_note"] or ""
    interval = int(task_row["interval"])

    # 1) Кому слать
    user = repo.get_user_by_id(user_id)
    if not user:
        return False
    chat_id = user["telegram_user_id"]

    # 2) Текст сообщения
    lines = [f"🔔 Напоминание: <b>{name}</b>"]
    if note:
        lines.append(note)
    text = "\n".join(lines)

    # 3) Отправка
    await bot.send_message(chat_id, text)

    # 4) Перенос на следующий раз
    next_ts = time.time() + interval * 60
    repo.reschedule(task_id, user_id, next_ts)
    return True
