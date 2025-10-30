# app/services/scheduler.py
import asyncio
import time
from typing import Optional
from aiogram import Bot
from app.db import repo
from .tasks import deliver_reminder
from app.db.repo import is_user_sleeping

_TICK_LOCK = asyncio.Lock()

async def _process_tick(bot: Bot, batch_limit: int = 50) -> int:
    """
    Обрабатывает одну «тик»-итерацию: достаёт due-задачи и отправляет напоминания.
    Возвращает количество обработанных задач.
    """
    now = time.time()
    due_rows = repo.get_due(now, batch_limit, user_id=None)
    sent = 0
    for row in due_rows:
        ok = await deliver_reminder(bot, row)
        if ok:
            sent += 1
    return sent

async def deliver_reminder(bot: Bot, task_row) -> bool:
    user_id = task_row["user_id"]
    # если пользователь спит — пропускаем
    if is_user_sleeping(user_id):
        return False

async def run(bot: Bot, interval_seconds: int = 15, batch_limit: int = 50, quiet: bool = True):
    """
    Бесконечный цикл: раз в interval_seconds вызывает _process_tick.
    Защищён от наложений через Lock (если тик занял дольше интервала).
    """
    while True:
        started = time.time()
        try:
            async with _TICK_LOCK:
                processed = await _process_tick(bot, batch_limit=batch_limit)
                if not quiet and processed:
                    print(f"[scheduler] sent={processed}")
        except Exception as e:
            # не уронить цикл из-за ошибки — просто логнём
            if not quiet:
                print(f"[scheduler] error: {e}")

        # выдерживаем периодичность
        elapsed = time.time() - started
        sleep_for = max(0.0, interval_seconds - elapsed)
        await asyncio.sleep(sleep_for)
