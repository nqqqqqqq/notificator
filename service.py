# service.py
from datetime import datetime
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db import repo


def add_task_service(user_id, task_name, notes, interval):
    if interval <= 0:
        raise ValueError("Interval must be greater than 0")
    task_id = repo.add_task(user_id, task_name, notes, interval)
    return f"Записал себе задачу {task_name}! Обязательно напомню тебе, чтобы ты не забыл. Удачи тебе :)"

def format_ts(ts: float) -> str:
    """Простой человекочитаемый формат UTC: YYYY-MM-DD HH:MM."""
    try:
        return datetime.utcfromtimestamp(float(ts)).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return "—"


def build_list_view(user_id: int, page: int = 0, limit: int = 5) -> tuple[str, InlineKeyboardMarkup]:
    # 1. Нормализация входа
    if limit is None or limit <= 0:
        limit = 5
    if page is None or page < 0:
        page = 0

    # 2. Данные
    total = int(repo.count_open(user_id))
    if total == 0:
        text = "Задач нет"
        kb = InlineKeyboardMarkup(inline_keyboard=[])
        return text, kb

    pages = (total + limit - 1) // limit
    if page >= pages:
        page = pages - 1

    offset = page * limit
    rows = repo.list_open_paged(user_id, offset, limit)

    # 3. Заголовок
    lines: list[str] = []
    lines.append("Мои задачи")
    lines.append(f"Страница {page + 1} из {pages}")
    lines.append(f"Всего: {total}")
    lines.append("")  # пустая строка-разделитель

    # 4. Тело списка
    for i, row in enumerate(rows, start=1):
        task_id = row["id"]
        name = row["task_name"] or "(без названия)"
        remind = format_ts(row["remind_time"])
        interval = int(row["interval_minutes"]) if row["interval_minutes"] is not None else 0
        snooze_info = ""
        if row["snooze_until"] is not None:
            snooze_info = f"\nОтложено до: {format_ts(row['snooze_until'])}"

        lines.append(
            f"{i}) {name}\n"
            f"Следующее: {remind}\n"
            f"Интервал: {interval} мин{snooze_info}"
        )

    text = "\n".join(lines)

    # 5. Клавиатура
    kb = InlineKeyboardBuilder()

    # Кнопки на каждую задачу
    for row in rows:
        task_id = row["id"]
        kb.row(
            InlineKeyboardButton(
                text="Сделано",
                callback_data=f"task_done|{task_id}|{page}|{limit}",
            ),
            InlineKeyboardButton(
                text="Отложить",
                callback_data=f"task_snooze|{task_id}|{page}|{limit}",
            ),
            InlineKeyboardButton(
                text="Удалить",
                callback_data=f"task_delete|{task_id}|{page}|{limit}",
            ),
        )

    # Навигация
    nav_row: list[InlineKeyboardButton] = []
    if page > 0:
        nav_row.append(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=f"list_page|{page - 1}|{limit}",
            )
        )
    if page < pages - 1:
        nav_row.append(
            InlineKeyboardButton(
                text="Вперёд ➡️",
                callback_data=f"list_page|{page + 1}|{limit}",
            )
        )
    if nav_row:
        kb.row(*nav_row)

    return text, kb.as_markup()


