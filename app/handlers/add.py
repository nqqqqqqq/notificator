from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext

from service import add_task_service
from db.repo import get_or_create_user

from aiogram.fsm.state import StatesGroup, State
form_router = Router()

class Form(StatesGroup):
    name = State()
    description = State()
    interval = State() # minutes

@form_router.message(Command("add"))
async def command_add(message: Message, state : FSMContext) -> None:
    await state.set_state("Form.name")
    await message.answer(
        "Отлично! Напиши название задачи:",
        reply_markup=ReplyKeyboardRemove(),
    )

@form_router.message(Form.name)
async def add_name(message: Message, state: FSMContext) -> None:
    await state.update_data(name=message.text.strip())
    await state.set_state("Form.description")
    await message.answer(
        "Добавь описание к задаче, это может быть ссылка, подробная информация или любые другие уточнения, чтобы ты не забыл. Или просто -",
        reply_markup=ReplyKeyboardRemove(),
    )

@form_router.message(Form.description)
async def add_description(message: Message, state: FSMContext) -> None:
    desc = None if message.text.strip() == "-" else message.text.strip()
    await state.update_data(description=desc)
    await state.set_state("Form.interval")
    await message.answer(
        "Отлично, когда тебе напомнить об этой задаче? Числом, пожалуйста",
        reply_markup=ReplyKeyboardRemove(),
    )

@form_router.message(Form.interval)
async def add_interval(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit():
        await message.answer("Нужно число минут, попробуй ещё раз")
        return

    minutes = int(text)
    if minutes <= 0:
        await message.answer("Интервал должен быть больше 0")
        return


    data = await state.get_data()
    name = data["name"]
    description = data["description"]

    user = get_or_create_user(telegram_user_id=message.from_user.id, username=message.from_user.username)
    user_id = user[id]

    result_text = add_task_service(user_id, name, description, minutes)
    await state.clear()

    await message.answer(result_text, reply_markup=ReplyKeyboardRemove())
