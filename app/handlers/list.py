#list.py

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from app.db.repo import get_or_create_user
from app.service import build_list_view

router = Router()

@router.message(Command("list"))
async def command_start_handler(message: Message):
    username = message.from_user.username
    telegram_user_id = message.from_user.id

    page = 0
    limit = 5

    user = get_or_create_user(telegram_user_id, username)
    user_id = user["id"]
    text, kb = build_list_view(user_id, page, limit)
    await message.answer(text, reply_markup=kb)

