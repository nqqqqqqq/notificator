from db import repo

def add_task_service(user_id, task_name, notes, interval):
    if interval <= 0:
        raise ValueError("Interval must be greater than 0")
    task_id = repo.add_task(user_id, task_name, notes, interval)
    return f"Задача успешно добавленна. Следующее напоминание через {interval} минут :)"

