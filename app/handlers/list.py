# app/handlers/list.py
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.chat_action import ChatActionSender

from app.db.repo import get_or_create_user, count_open
from app.service import build_list_view
from app.db import repo

router = Router()


@router.message(Command("list"))
async def list_cmd(message: Message):
    # первая страница
    user = get_or_create_user(telegram_user_id=message.from_user.id,
                              username=message.from_user.username)
    user_id = int(user["id"])
    text, kb = build_list_view(user_id, page=0, limit=5, selected_task_id=None)
    async with ChatActionSender.typing(message.bot, message.chat.id):
        await message.answer(text, reply_markup=kb)


# ===== колбэки =====

def _parse_parts(cb: str):
    # универсальный парсер callback_data, разделённых '|'
    # возвращает список частей
    return cb.split("|")


@router.callback_query(F.data.startswith("list_page|"))
async def cb_list_page(query: CallbackQuery):
    # list_page|{page}|{limit}
    parts = _parse_parts(query.data)
    page = int(parts[1])
    limit = int(parts[2])

    user = get_or_create_user(telegram_user_id=query.from_user.id,
                              username=query.from_user.username)
    user_id = int(user["id"])

    text, kb = build_list_view(user_id, page=page, limit=limit, selected_task_id=None)
    await query.message.edit_text(text, reply_markup=kb)
    await query.answer()


@router.callback_query(F.data.startswith("select_task|"))
async def cb_select_task(query: CallbackQuery):
    # select_task|{task_id}|{page}|{limit}
    parts = _parse_parts(query.data)
    task_id = int(parts[1])
    page = int(parts[2])
    limit = int(parts[3])

    user = get_or_create_user(telegram_user_id=query.from_user.id,
                              username=query.from_user.username)
    user_id = int(user["id"])

    text, kb = build_list_view(user_id, page=page, limit=limit, selected_task_id=task_id)
    await query.message.edit_text(text, reply_markup=kb)
    await query.answer()


@router.callback_query(F.data.startswith("task_done|"))
async def cb_task_done(query: CallbackQuery):
    # task_done|{task_id}|{page}|{limit}
    parts = _parse_parts(query.data)
    task_id = int(parts[1])
    page = int(parts[2])
    limit = int(parts[3])

    user = get_or_create_user(telegram_user_id=query.from_user.id,
                              username=query.from_user.username)
    user_id = int(user["id"])

    ok = repo.mark_done(task_id, user_id)
    if not ok:
        await query.answer("Не получилось отметить выполненной (возможно, не ваша задача?)", show_alert=True)
    # пересчитать страницу: она могла опустеть
    total = count_open(user_id)
    pages = (total + limit - 1) // limit
    if pages == 0:
        # пусто, показываем пустой список
        text, kb = build_list_view(user_id, page=0, limit=limit, selected_task_id=None)
    else:
        if page >= pages:
            page = max(0, pages - 1)
        text, kb = build_list_view(user_id, page=page, limit=limit, selected_task_id=None)

    await query.message.edit_text(text, reply_markup=kb)
    await query.answer("Готово ✅")


@router.callback_query(F.data.startswith("task_snooze|"))
async def cb_task_snooze(query: CallbackQuery):
    # task_snooze|{task_id}|{minutes}|{page}|{limit}
    parts = _parse_parts(query.data)
    task_id = int(parts[1])
    minutes = int(parts[2])
    page = int(parts[3])
    limit = int(parts[4])

    user = get_or_create_user(telegram_user_id=query.from_user.id,
                              username=query.from_user.username)
    user_id = int(user["id"])

    ok = repo.snooze(task_id, user_id, minutes)
    if not ok:
        await query.answer("Не удалось отложить", show_alert=True)

    # после snooze задача может «уехать», возвращаемся к списку
    text, kb = build_list_view(user_id, page=page, limit=limit, selected_task_id=task_id)
    await query.message.edit_text(text, reply_markup=kb)
    await query.answer("Отложено ⏱")


@router.callback_query(F.data.startswith("task_delete|"))
async def cb_task_delete(query: CallbackQuery):
    # task_delete|{task_id}|{page}|{limit}
    parts = _parse_parts(query.data)
    task_id = int(parts[1])
    page = int(parts[2])
    limit = int(parts[3])

    user = get_or_create_user(telegram_user_id=query.from_user.id,
                              username=query.from_user.username)
    user_id = int(user["id"])

    ok = repo.delete_task(task_id, user_id)
    if not ok:
        await query.answer("Не удалось удалить", show_alert=True)

    # пересчитать страницу
    total = count_open(user_id)
    pages = (total + limit - 1) // limit
    if pages == 0:
        text, kb = build_list_view(user_id, page=0, limit=limit, selected_task_id=None)
    else:
        if page >= pages:
            page = max(0, pages - 1)
        text, kb = build_list_view(user_id, page=page, limit=limit, selected_task_id=None)

    await query.message.edit_text(text, reply_markup=kb)
    await query.answer("Удалено 🗑")


@router.callback_query(F.data.startswith("back_to_list|"))
async def cb_back_to_list(query: CallbackQuery):
    # back_to_list|{page}|{limit}
    parts = _parse_parts(query.data)
    page = int(parts[1])
    limit = int(parts[2])

    user = get_or_create_user(telegram_user_id=query.from_user.id,
                              username=query.from_user.username)
    user_id = int(user["id"])

    text, kb = build_list_view(user_id, page=page, limit=limit, selected_task_id=None)
    await query.message.edit_text(text, reply_markup=kb)
    await query.answer()
