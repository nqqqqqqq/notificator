import re
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from app.db.repo import get_or_create_user, add_task_at

router = Router()

RU_MONTHS = {
    "янв":1,"января":1,"январь":1,
    "фев":2,"февраля":2,"февраль":2,
    "мар":3,"марта":3,"март":3,
    "апр":4,"апреля":4,"апрель":4,
    "май":5,"мая":5,
    "июн":6,"июня":6,"июнь":6,
    "июл":7,"июля":7,"июль":7,
    "авг":8,"августа":8,"август":8,
    "сен":9,"сентября":9,"сентябрь":9,
    "окт":10,"октября":10,"октябрь":10,
    "ноя":11,"ноября":11,"ноябрь":11,
    "дек":12,"декабря":12,"декабрь":12,
}

def _to_int(s):
    try:
        return int(s)
    except:
        return None

def parse_datetime_ru(text: str, tz_name: str = "Europe/Warsaw") -> float | None:
    s = text.lower().strip()
    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)

    # сегодня / завтра HH:MM
    if s.startswith("сегодня"):
        m = re.search(r"(\d{1,2})[:.](\d{2})", s)
        if not m: return None
        hh, mm = _to_int(m.group(1)), _to_int(m.group(2))
        if hh is None or mm is None: return None
        dt = datetime(now.year, now.month, now.day, hh, mm, tzinfo=tz)
        return dt.timestamp()

    if s.startswith("завтра"):
        m = re.search(r"(\d{1,2})[:.](\d{2})", s)
        if not m: return None
        hh, mm = _to_int(m.group(1)), _to_int(m.group(2))
        if hh is None or mm is None: return None
        dt = datetime(now.year, now.month, now.day, hh, mm, tzinfo=tz) + timedelta(days=1)
        return dt.timestamp()

    # 20.11 17:00  /  20.11.2025 17:00
    m = re.search(r"(\d{1,2})[./](\d{1,2})(?:[./](\d{2,4}))?\s+(\d{1,2})[:.](\d{2})", s)
    if m:
        dd = _to_int(m.group(1)); mm = _to_int(m.group(2))
        yy = _to_int(m.group(3)) if m.group(3) else now.year
        hh = _to_int(m.group(4)); mi = _to_int(m.group(5))
        if yy and yy < 100: yy += 2000
        try:
            dt = datetime(yy, mm, dd, hh, mi, tzinfo=tz)
            return dt.timestamp()
        except ValueError:
            return None

    # 20 ноября 17:00 / 20 ноя 17:00
    m = re.search(r"(\d{1,2})\s+([а-яё]+)\s+(\d{1,2})[:.](\d{2})(?:\s*(\d{4}))?", s)
    if m:
        dd = _to_int(m.group(1)); mon_word = m.group(2)
        hh = _to_int(m.group(3)); mi = _to_int(m.group(4))
        yy = _to_int(m.group(5)) if m.group(5) else now.year
        mon = RU_MONTHS.get(mon_word, None)
        if yy and yy < 100: yy += 2000
        if mon and dd and hh is not None and mi is not None:
            try:
                dt = datetime(yy, mon, dd, hh, mi, tzinfo=tz)
                return dt.timestamp()
            except ValueError:
                return None

    # HH:MM (сегодня, если время уже прошло — завтра)
    m = re.search(r"^(\d{1,2})[:.](\d{2})$", s)
    if m:
        hh = _to_int(m.group(1)); mi = _to_int(m.group(2))
        dt = datetime(now.year, now.month, now.day, hh, mi, tzinfo=tz)
        if dt.timestamp() <= now.timestamp():
            dt = dt + timedelta(days=1)
        return dt.timestamp()

    return None


class AtForm(StatesGroup):
    name = State()
    description = State()
    when = State()

@router.message(Command("at"))
async def at_start(message: Message, state: FSMContext):
    await state.set_state(AtForm.name)
    await message.answer("Название задачи?", reply_markup=ReplyKeyboardRemove())

@router.message(AtForm.name)
async def at_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(AtForm.description)
    await message.answer("Описание (или «-»)?")

@router.message(AtForm.description)
async def at_desc(message: Message, state: FSMContext):
    desc = None if message.text.strip() == "-" else message.text.strip()
    await state.update_data(description=desc)
    await state.set_state(AtForm.when)
    await message.answer("Когда напомнить? Например: «20 ноября 17:00», «20.11 17:00», «сегодня 21:30», «завтра 9:00»")

@router.message(AtForm.when)
async def at_when(message: Message, state: FSMContext):
    user = get_or_create_user(message.from_user.id, message.from_user.username)
    user_id = int(user["id"])

    tz_name = user["timezone"] if "timezone" in user.keys() and user["timezone"] else "Europe/Warsaw"
    when_ts = parse_datetime_ru(message.text, tz_name=tz_name)

    if when_ts is None or when_ts <= time.time():
        await message.answer("Не понял дату/время или время уже прошло. Пример: «20 ноября 17:00». Попробуй ещё.")
        return

    data = await state.get_data()
    task_id = add_task_at(user_id, data["name"], data.get("description"), when_ts)

    await state.clear()
    from datetime import datetime
    from zoneinfo import ZoneInfo
    when_str = datetime.fromtimestamp(when_ts, ZoneInfo(tz_name)).strftime("%Y-%m-%d %H:%M")
    await message.answer(f"✅ Разовая задача добавлена (ID: {task_id})\n⏰ Время: {when_str}")
