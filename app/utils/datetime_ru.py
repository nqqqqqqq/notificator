# app/utils/datetime_ru.py
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

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

    # сегодня HH:MM
    if s.startswith("сегодня"):
        m = re.search(r"(\d{1,2})[:.](\d{2})", s)
        if not m: return None
        hh, mm = _to_int(m.group(1)), _to_int(m.group(2))
        if hh is None or mm is None: return None
        dt = datetime(now.year, now.month, now.day, hh, mm, tzinfo=tz)
        return dt.timestamp()

    # завтра HH:MM
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
        mon = RU_MONTHS.get(mon_word)
        if yy and yy < 100: yy += 2000
        if mon and dd and hh is not None and mi is not None:
            try:
                dt = datetime(yy, mon, dd, hh, mi, tzinfo=tz)
                return dt.timestamp()
            except ValueError:
                return None

    # HH:MM (сегодня, если уже прошло — завтра)
    m = re.search(r"^(\d{1,2})[:.](\d{2})$", s)
    if m:
        hh = _to_int(m.group(1)); mi = _to_int(m.group(2))
        dt = datetime(now.year, now.month, now.day, hh, mi, tzinfo=tz)
        if dt.timestamp() <= now.timestamp():
            dt = dt + timedelta(days=1)
        return dt.timestamp()

    return None
