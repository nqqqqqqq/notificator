# service.py

from datetime import datetime
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.db.repo import add_task, count_open, list_open_paged


def format_ts(ts: float) -> str:
    """Простой человекочитаемый формат времени (UTC)."""
    if ts is None:
        return "—"
    return datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d %H:%M")


def build_list_view(user_id: int, page: int = 0, limit: int = 5) -> tuple[str, InlineKeyboardMarkup]:
    # 1) Нормализация входа
    if limit <= 0:
        limit = 5
    page = max(0, page)

    # 2) Данные: total, pages, rows
    total = count_open(user_id)
    if total == 0:
        text = "📭 Задач нет. Добавь первую командой /add"
        return text, InlineKeyboardMarkup(inline_keyboard=[])

    pages = (total + limit - 1) // limit
    if page >= pages:
        page = pages - 1

    offset = page * limit
    rows = list_open_paged(user_id, offset, limit)

    # 3) Заголовок
    header_lines = [
        "🗒️ Мои задачи",
        f"Страница {page + 1} из {pages}",
        f"Всего: {total}",
        ""
    ]

    # 4) Элементы списка
    body_lines = []
    for i, row in enumerate(rows, start=1):
        rt = format_ts(row["next_reminder_at"])
        info = [
            f"{i}) {row['task_name']}",
            f"   След. напоминание: {rt}",
            f"   Интервал: {row['interval']} мин"
        ]
        if row["task_note"]:
            info.append(f"   Заметка: {row['task_note']}")
        if row["paused_until"]:
            info.append(f"   Отложено до: {format_ts(row['paused_until'])}")
        body_lines.append("\n".join(info))

    text = "\n".join(header_lines + body_lines) or "📭 Задач нет."

    # 5) Клавиатура навигации
    kb_rows = []

    # Для каждой задачи — ряд кнопок действий
    for row in rows:
        task_id = row["id"]
        kb_rows.append([
            InlineKeyboardButton(
                text="✅ Сделано",
                callback_data=f"task_done|{task_id}|{page}|{limit}"
            ),
            InlineKeyboardButton(
                text="⏱ Отложить",
                callback_data=f"task_snooze|{task_id}|{page}|{limit}"
            ),
            InlineKeyboardButton(
                text="🗑 Удалить",
                callback_data=f"task_delete|{task_id}|{page}|{limit}"
            ),
        ])

    # Ряд навигации
    nav_row = []
    if page > 0:
        nav_row.append(
            InlineKeyboardButton(text="⬅️ Назад", callback_data=f"list_page|{page - 1}|{limit}")
        )
    else:
        # Ничего не добавляем — «неактивная» кнопка в инлайн-кб не поддерживается
        pass

    if page < pages - 1:
        nav_row.append(
            InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"list_page|{page + 1}|{limit}")
        )

    if nav_row:
        kb_rows.append(nav_row)

    keyboard = InlineKeyboardMarkup(inline_keyboard=kb_rows)
    return text, keyboard

def add_task_service(user_id: int, task_name: str, notes: str | None, interval: int) -> str:
    # валидация входа
    if not task_name or not task_name.strip():
        raise ValueError("Название задачи пустое")
    # if interval <= 0:
    #   raise ValueError("Интервал должен быть больше 0")

    task_id = add_task(user_id, task_name.strip(), notes, interval)
    return f"✅ Задача добавлена (ID: {task_id}). Следующее напоминание через {interval} минут."
