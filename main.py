# main.py
import asyncio
import logging
import os
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from app.handlers import add, list
from app.services.scheduler import run as scheduler_run


async def main():
    # --- логирование ---
    logging.basicConfig(level=logging.INFO)

    # --- загрузка токена ---
    load_dotenv()
    BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

    if not BOT_TOKEN or ":" not in BOT_TOKEN:
        raise RuntimeError("❌ BOT_TOKEN не найден или неверный. Проверь .env")

    # --- инициализация бота и диспетчера ---
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    # --- подключаем роутеры ---
    dp.include_router(add.form_router)
    dp.include_router(list.router)

    # --- запускаем фоновый планировщик напоминаний ---
    asyncio.create_task(scheduler_run(bot, interval_seconds=15, batch_limit=50, quiet=False))

    logging.info("✅ Бот запущен и ждёт события")

    # --- стартуем polling ---
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logging.exception("Polling упал с ошибкой: %s", e)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
