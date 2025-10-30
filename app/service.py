# app/service.py
from datetime import datetime
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import Tuple, Optional, List

from app.db import repo


def format_ts(ts: float | None) -> str:
    if not ts:
        return "—"
    # храним UTC (time.time), форматируем просто, без TZ
    return datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d %H:%M")


def clamp_page(page: int, pages: int) -> int:
    if pages <= 0:
        return 0
    if page < 0:
        return 0
    if page >= pages:
        return pages - 1
    return page


def _chunk_buttons(btns: List[InlineKeyboardButton], per_row: int = 8) -> List[List[InlineKeyboardButton]]:
    rows: List[List[InlineKeyboardButton]] = []
    for i in range(0, len(btns), per_row):
        rows.append(btns[i:i + per_row])
    return rows


def build_list_view(
    user_id: int,
    page: int = 0,
    limit: int = 5,
    selected_task_id: Optional[int] = None,
) -> Tuple[str, InlineKeyboardMarkup]:
    # нормализация входа
    if limit <= 0:
        limit = 5
    page = max(0, page)

    total = repo.count_open(user_id)
    if total == 0:
        text = "📭 Задач нет. Добавь первую командой /add"
        return text, InlineKeyboardMarkup(inline_keyboard=[])

    pages = (total + limit - 1) // limit
    page = clamp_page(page, pages)
    offset = page * limit

    rows = repo.list_open_paged(user_id, offset, limit)
    if rows:
        print("DEBUG row keys:", list(rows[0].keys()))

    # Заголовок
    header_lines = [
        "🗒️ Мои задачи",
        f"Страница {page + 1} из {pages}",
        f"Всего: {total}",
        "",
    ]

    # Тело списка: пометим выбранную стрелкой
    body_lines = []
    for i, row in enumerate(rows, start=1):
        is_selected = (selected_task_id is not None and row["id"] == selected_task_id)
        prefix = "→ " if is_selected else ""
        info = [
            f"{prefix}{i}) {row['task_name']}",
            f"   След. напоминание: {format_ts(row['next_reminder_at'])}",
            f"   Интервал: {int(row['interval'])} мин",
        ]
        if row["task_note"]:
            info.append(f"   Заметка: {row['task_note']}")
        if row["paused_until"]:
            info.append(f"   Отложено до: {format_ts(row['paused_until'])}")
        body_lines.append("\n".join(info))

    text = "\n".join(header_lines + body_lines) or "📭 Задач нет."

    kb_rows: List[List[InlineKeyboardButton]] = []

    if selected_task_id is None:
        # Рисуем кнопку-номера для видимых задач (1..N)
        number_buttons = []
        for i, row in enumerate(rows, start=1):
            number_buttons.append(
                InlineKeyboardButton(
                    text=str(i),
                    callback_data=f"select_task|{row['id']}|{page}|{limit}",
                )
            )
        kb_rows.extend(_chunk_buttons(number_buttons, per_row=8))
    else:
        # Рисуем действия для выбранной задачи
        tid = selected_task_id
        kb_rows.append([
            InlineKeyboardButton(text="✅ Выполнено", callback_data=f"task_done|{tid}|{page}|{limit}")
        ])
        kb_rows.append([
            InlineKeyboardButton(text="⏱ +15м", callback_data=f"task_snooze|{tid}|15|{page}|{limit}"),
            InlineKeyboardButton(text="⏱ +1ч",  callback_data=f"task_snooze|{tid}|60|{page}|{limit}"),
            InlineKeyboardButton(text="⏱ +1д",  callback_data=f"task_snooze|{tid}|1440|{page}|{limit}"),
        ])
        kb_rows.append([
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"task_delete|{tid}|{page}|{limit}")
        ])
        kb_rows.append([
            InlineKeyboardButton(text="⬅️ Назад", callback_data=f"back_to_list|{page}|{limit}")
        ])

    # Пагинация (всегда внизу)
    nav_row: List[InlineKeyboardButton] = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"list_page|{page - 1}|{limit}"))
    if page < pages - 1:
        nav_row.append(InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"list_page|{page + 1}|{limit}"))
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

    task_id = repo.add_task(user_id, task_name.strip(), notes, interval)
    return f"✅ Задача добавлена (ID: {task_id}). Следующее напоминание через {interval} минут."



