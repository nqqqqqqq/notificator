import time
from app.db import repo

async def deliver_reminder(bot, task_row):
    print(f"TASK: deliver_reminder called for task id={task_row['id']} user={task_row['user_id']}")

    # Пропуск если пользователь спит
    if repo.is_user_sleeping(task_row["user_id"]):
        print(f"TASK: user {task_row['user_id']} is sleeping, skipping notification for task id={task_row['id']}")
        return False

    chat_id = repo.get_user_by_id(task_row["user_id"])["telegram_user_id"]
    message = (
        f"⏰ Напоминание!\n\n"
        f"Задача: <b>{task_row['task_name']}</b>\n"
        f"Заметка: {task_row['task_note'] or '—'}"
    )

    # Отправка сообщения
    try:
        await bot.send_message(chat_id, message, parse_mode="HTML")
        print(f"TASK: message sent to user {task_row['user_id']} for task id={task_row['id']}")
    except Exception as e:
        print(f"TASK: FAILED to send message for task id={task_row['id']} — {e}")
        return False

    # Определяем нужно ли пометить задачу выполненной (разовая или с интервалом <= 0)
    is_one_shot = bool(task_row.get("is_one_shot", 0))
    interval = int(task_row["interval"])
    if is_one_shot or interval <= 0:
        repo.mark_done(task_row["id"], task_row["user_id"])
        print(f"TASK: task id={task_row['id']} marked as done")
    else:
        # Иначе пересчитываем следующее напоминание
        next_ts = time.time() + interval * 60
        repo.reschedule(task_row["id"], task_row["user_id"], next_ts)
        print(f"TASK: task id={task_row['id']} rescheduled to {next_ts}")

    return True
