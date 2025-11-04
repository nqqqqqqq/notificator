from datetime import datetime
from typing import Tuple, Optional, List
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from zoneinfo import ZoneInfo

from app.db import repo


def format_ts(ts: float | None, tz: str = "Europe/Warsaw") -> str:
    if ts is None:
        return "—"
    return datetime.fromtimestamp(float(ts), ZoneInfo(tz)).strftime("%Y-%m-%d %H:%M")


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


def _col(row, *names):
    """Вернуть первое существующее имя колонки из списка (на случай разных схем)."""
    for n in names:
        try:
            return row[n]
        except (KeyError, IndexError):
            continue
    return None


def build_list_view(
    user_id: int,
    page: int = 0,
    limit: int = 5,
    selected_task_id: Optional[int] = None,
    seed_a: Optional[int] = None,
    seed_b: Optional[int] = None,
    tz: str = "Europe/Warsaw",  # ← новый параметр
) -> Tuple[str, InlineKeyboardMarkup]:
    # нормализация входа
    if limit <= 0:
        limit = 5
    page = max(0, page)

    # считаем всего и страницы
    total = repo.count_open(user_id)
    if total == 0:
        text = "📭 Задач нет. Добавь первую командой /add"
        return text, InlineKeyboardMarkup(inline_keyboard=[])

    pages = (total + limit - 1) // limit
    page = clamp_page(page, pages)
    offset = page * limit

    # берём строки: случайный порядок по сидy или обычный
    if seed_a is not None and seed_b is not None:
        rows = repo.list_open_paged_random(user_id, offset, limit, seed_a, seed_b)
    else:
        rows = repo.list_open_paged(user_id, offset, limit)

    # Заголовок (минимал)
    header_lines = [
        f"📋 Задачи (стр. {page + 1} / {pages}, всего {total})",
        ""
    ]

    # Тело списка
    body_lines: List[str] = []
    for i, row in enumerate(rows, start=1):
        is_selected = (selected_task_id is not None and row["id"] == selected_task_id)

        remind_ts = _col(row, "remind_time", "next_reminder_at")
        note = _col(row, "task_note", "task_notes")
        snooze_ts = _col(row, "snooze_until", "paused_until")
        one_shot = bool(_col(row, "is_one_shot"))
        interval_val = _col(row, "interval", "interval_minutes")

        # безопасно формируем строку интервала
        interval_str = "—"
        if one_shot:
            interval_str = "разово"
        elif interval_val is not None:
            try:
                iv = int(interval_val)
                interval_str = "разово" if iv <= 0 else f"{iv} мин"
            except Exception:
                interval_str = "—"

        lines = [
            f"{'👉 ' if is_selected else ''}{i}. <b>{row['task_name']}</b>",
            f"   ⏰ {format_ts(remind_ts, tz)} | ⏱ {interval_str}",
        ]
        if note:
            lines.append(f"   💬 {note}")
        if snooze_ts is not None:
            lines.append(f"   😴 Отложено до: {format_ts(snooze_ts, tz)}")

        body_lines.append("\n".join(lines))

    text = "\n\n".join(header_lines + body_lines)

    # Клавиатура
    kb_rows: List[List[InlineKeyboardButton]] = []

    if selected_task_id is None:
        # Рисуем кнопки-номера видимых задач (1..N)
        number_buttons: List[InlineKeyboardButton] = []
        for i, row in enumerate(rows, start=1):
            cb = f"select_task|{row['id']}|{page}|{limit}"
            if seed_a is not None and seed_b is not None:
                cb += f"|{seed_a}|{seed_b}"
            number_buttons.append(InlineKeyboardButton(text=str(i), callback_data=cb))
        kb_rows.extend(_chunk_buttons(number_buttons, per_row=8))
    else:
        tid = selected_task_id

        def with_seed(base: str) -> str:
            if seed_a is None or seed_b is None:
                return base
            return f"{base}|{seed_a}|{seed_b}"

        kb_rows.append([
            InlineKeyboardButton(text="✅ Выполнено", callback_data=with_seed(f"task_done|{tid}|{page}|{limit}"))
        ])
        kb_rows.append([
            InlineKeyboardButton(text="⏱ +15м", callback_data=with_seed(f"task_snooze|{tid}|15|{page}|{limit}")),
            InlineKeyboardButton(text="⏱ +1ч",  callback_data=with_seed(f"task_snooze|{tid}|60|{page}|{limit}")),
            InlineKeyboardButton(text="⏱ +1д",  callback_data=with_seed(f"task_snooze|{tid}|1440|{page}|{limit}")),
        ])
        kb_rows.append([
            InlineKeyboardButton(text="🗑 Удалить", callback_data=with_seed(f"task_delete|{tid}|{page}|{limit}"))
        ])
        kb_rows.append([
            InlineKeyboardButton(text="⬅️ Назад", callback_data=with_seed(f"back_to_list|{page}|{limit}"))
        ])

    # Пагинация
    nav_row: List[InlineKeyboardButton] = []

    def nav_cb(p: int) -> str:
        base = f"list_page|{p}|{limit}"
        if seed_a is not None and seed_b is not None:
            base += f"|{seed_a}|{seed_b}"
        return base

    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=nav_cb(page - 1)))
    if page < pages - 1:
        nav_row.append(InlineKeyboardButton(text="Вперёд ➡️", callback_data=nav_cb(page + 1)))
    if nav_row:
        kb_rows.append(nav_row)

    keyboard = InlineKeyboardMarkup(inline_keyboard=kb_rows)
    return text, keyboard


def add_task_service(user_id: int, task_name: str, notes: str | None, interval: int) -> str:
    if not task_name or not task_name.strip():
        raise ValueError("Название задачи пустое")
    task_id = repo.add_task(user_id, task_name.strip(), notes, interval)
    return f"✅ Задача добавлена (ID: {task_id}). Следующее напоминание через {interval} минут."
