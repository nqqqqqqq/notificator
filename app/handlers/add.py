import re
import unicodedata
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext

from app.service import add_task_service
from app.db.repo import get_or_create_user
from aiogram.fsm.state import StatesGroup, State

form_router = Router()

def normalize(string: str) -> str:
    # Приведение регистра и нормализация юникода
    string = unicodedata.normalize('NFKD', string).lower().strip()

    # Убираем "через" / "спустя"
    string = re.sub(r"\s*\b(через|спустя)\b\s*", " ", string)

    # Приводим "минус" и юникодный минус к дефису
    string = string.replace("−", "-")
    string = re.sub(r"\bминус\b", "-", string)

    # Унификация единиц времени
    string = re.sub(r"\bмин\.?\b", " минут", string)         # мин., мин -> минут
    string = re.sub(r"\bчас(?:\.|а|ов)?\b", " час", string)  # час., часа, часов -> час

    # Перестановка порядка слов: "минут 20" -> "20 минут", "час 2" -> "2 час"
    string = re.sub(r"\bминут\s+(-?\d+)\b", r"\1 минут", string)
    string = re.sub(r"\bчас\s+(-?\d+)\b",   r"\1 час", string)

    # Убираем лишние пробелы
    string = re.sub(r"\s+", " ", string).strip()
    return string


RU_NUM = {
    "ноль": 0,
    "один": 1,
    "два": 2,
    "три": 3,
    "четыре": 4,
    "пять": 5,
    "шесть": 6,
    "семь": 7,
    "восемь": 8,
    "девять": 9,
    "десять": 10,
    "одинадцать": 11,
    "двенадцать": 12,
    "тринадцать": 13,
    "четырнадцать": 14,
    "пятнадцать": 15,
    "двадцать": 20,
    "тридцать": 30,
    "сорок": 40,
    "пятьдесят": 50
}


def word_to_int(words: str) -> int | None:
    total = 0
    for word in words.split():
        v = RU_NUM.get(word)
        if v is None:
            return None
        total += v
    return total if total > 0 else None


def parse_hours_minutes_combo(t: str) -> int | None:
    h = re.search(r"\b(-?\d+)\s*час\b", t)
    m = re.search(r"\b(-?\d+)\s*минут[аы]?\b", t)
    if h and m:
        return int(h.group(1)) * 60 + int(m.group(1))
    return None


def parse_decimal_hours(t: str) -> int | None:
    m = re.search(r"\b(-?\d+[.,]\d+)\s*час\b", t)
    if not m:
        return None
    hours = float(m.group(1).replace(",", "."))
    return int(round(hours * 60))


def parse_number_with_unit(t: str) -> int | None:
    m = re.search(r"\b(-?\d+)\s*(минут[аы]?|час)\b", t)
    if not m:
        return None
    value = int(m.group(1))
    unit = m.group(2)
    return value * 60 if unit.startswith("час") else value


def parse_special_forms(t: str) -> int | None:
    if re.search(r"\bпол ?часа\b", t):
        return 30
    if re.search(r"\bполтора\s*час(а|ов)?\b", t):
        return 90
    return None


def parse_words_with_unit(t: str) -> int | None:
    # Варианты: "- пять минут" / "минус пять минут"
    m = re.search(r"(?:^|\s)-\s*([а-яё\s]+)\s*минут[аы]?\b", t)
    if m:
        val = word_to_int(m.group(1).strip())
        return -val if val is not None else None

    m = re.search(r"\b([а-яё\s]+)\s*минут[аы]?\b", t)
    if not m:
        return None
    val = word_to_int(m.group(1).strip())
    return val


def parse_plain_number(t: str) -> int | None:
    if t.startswith("-") and t[1:].isdigit():
        return -int(t[1:])
    return int(t) if t.isdigit() else None


def parse_to_minutes(text: str) -> int | None:
    t = normalize(text)

    # 1) "2 часа 30 минут"
    minutes = parse_hours_minutes_combo(t)
    if minutes:
        return minutes

    # 2) "1,5 часа"
    minutes = parse_decimal_hours(t)
    if minutes:
        return minutes

    # 3) "полчаса", "полтора часа"
    minutes = parse_special_forms(t)
    if minutes:
        return minutes

    # 4) "5 минут", "-2 часа"
    minutes = parse_number_with_unit(t)
    if minutes:
        return minutes

    # 5) "двадцать минут", "- пять минут"
    minutes = parse_words_with_unit(t)
    if minutes:
        return minutes

    # 6) Просто число
    minutes = parse_plain_number(t)
    if minutes:
        return minutes

    return None


class Form(StatesGroup):
    name = State()
    description = State()
    interval = State()


@form_router.message(Command("add"))
async def command_add(message: Message, state: FSMContext) -> None:
    await state.set_state(Form.name)
    await message.answer(
        "Отлично! Напиши название задачи:",
        reply_markup=ReplyKeyboardRemove(),
    )


@form_router.message(Form.name)
async def add_name(message: Message, state: FSMContext) -> None:
    await state.update_data(name=message.text.strip())
    await state.set_state(Form.description)
    await message.answer(
        "Добавь описание к задаче или уточнения",
        reply_markup=ReplyKeyboardRemove(),
    )


@form_router.message(Form.description)
async def add_description(message: Message, state: FSMContext) -> None:
    desc = None if message.text.strip() == "-" else message.text.strip()
    await state.update_data(description=desc)
    await state.set_state(Form.interval)
    await message.answer(
        "Когда напомнить об этой задаче? Укажи число или время, например: '10 минут' или '2 часа'",
        reply_markup=ReplyKeyboardRemove(),
    )


@form_router.message(Form.interval)
async def add_interval(message: Message, state: FSMContext):
    text = message.text.strip()
    minutes = parse_to_minutes(text)

    if minutes is None:
        await message.answer(
            "Нужно число минут, попробуй ещё раз!",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    if minutes <= 0:
        await message.answer(
            "Время не может быть меньше нуля. Попробуй ещё раз!",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    data = await state.get_data()
    name = data["name"]
    description = data["description"]

    user = get_or_create_user(
        telegram_user_id=message.from_user.id,
        username=message.from_user.username,
    )
    user_id = int(user["id"])

    result_text = add_task_service(user_id, name, description, minutes)
    await state.clear()

    await message.answer(result_text, reply_markup=ReplyKeyboardRemove())
