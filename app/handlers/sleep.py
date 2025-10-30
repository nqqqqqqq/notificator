from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from app.db.repo import get_or_create_user, set_sleep_state

router = Router()

@router.message(Command("sleep"))
async def go_sleep(message: Message):
    user = get_or_create_user(message.from_user.id, message.from_user.username)
    set_sleep_state(user["id"], True)
    await message.answer("😴 Хорошо, я не буду тебя беспокоить, пока ты спишь.")

@router.message(Command("awake"))
async def wake_up(message: Message):
    user = get_or_create_user(message.from_user.id, message.from_user.username)
    set_sleep_state(user["id"], False)
    await message.answer("🌞 Доброе утро! Я снова буду напоминать тебе о задачах.")
