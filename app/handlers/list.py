from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram import html

router = Router()

@router.message(Command("list"))
async def command_start_handler(message: Message):
    pass
