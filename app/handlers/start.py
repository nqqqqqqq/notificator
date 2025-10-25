from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram import html

router = Router()

@router.message(CommandStart())
async def command_start_handler(message: Message):
    await message.answer(f" Привет, {html.bold(message.from_user.first_name)}. Это удобный планировщик задач, который поможет тебе не забывать важные для тебя дела! Надеюсь, тебе будет удобно им пользоваться :) ")
