import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

import db
import keyboards

logger = logging.getLogger("instasession.bot")

router = Router()

WELCOME = "🤖 <b>InstaSession</b>\nЗащита аккаунта от чужих сессий."


def setup_handlers(session_guard, admin_id: int) -> Router:

    def is_admin(user_id: int) -> bool:
        return user_id == admin_id

    @router.message(Command("start"))
    @router.message(Command("menu"))
    async def cmd_menu(message: Message):
        if not is_admin(message.from_user.id):
            return await message.answer("⛔️ Этот бот приватный.")
        protection_on = (await db.get_setting("protection_enabled", "1")) == "1"
        await message.answer(WELCOME, reply_markup=keyboards.main_menu(protection_on))

    @router.callback_query(F.data == "menu:main")
    async def cb_main(call: CallbackQuery):
        if not is_admin(call.from_user.id):
            return await call.answer()
        protection_on = (await db.get_setting("protection_enabled", "1")) == "1"
        await call.message.edit_text(WELCOME, reply_markup=keyboards.main_menu(protection_on))
        await call.answer()

    @router.callback_query(F.data == "toggle_protection")
    async def cb_toggle(call: CallbackQuery):
        if not is_admin(call.from_user.id):
            return await call.answer()
        current_on = (await db.get_setting("protection_enabled", "1")) == "1"
        await db.set_setting("protection_enabled", "0" if current_on else "1")
        new_state = not current_on
        await call.message.edit_reply_markup(reply_markup=keyboards.main_menu(new_state))
        await call.answer("Защита включена ✅" if new_state else "Защита выключена ⛔️")

    @router.callback_query(F.data.in_({"menu:whitelist", "menu:refresh"}))
    async def cb_whitelist(call: CallbackQuery):
        if not is_admin(call.from_user.id):
            return await call.answer()
        await call.answer("Загружаю сессии...")
        try:
            sessions = await session_guard.get_sessions()
        except Exception:
            logger.exception("Не удалось получить список сессий")
            return await call.message.edit_text(
                "❌ Ошибка получения сессий. Проверь SESSION_STRING/API_ID/API_HASH.",
                reply_markup=keyboards.back_menu(),
            )
        sessions = [s for s in sessions if not s.current]
        wl = await db.get_whitelist()
        wl_hashes = {row[0] for row in wl}
        await call.message.edit_text(
            "🛡 <b>Белый список</b>\n"
            "Нажми на сессию, чтобы добавить/убрать из белого списка.\n"
            "✅ — в белом списке, не будет удалена автоматически.",
            reply_markup=keyboards.whitelist_menu(sessions, wl_hashes),
        )

    @router.callback_query(F.data.startswith("wl:"))
    async def cb_toggle_whitelist(call: CallbackQuery):
        if not is_admin(call.from_user.id):
            return await call.answer()
        hash_str = call.data.split(":", 1)[1]

        try:
            sessions = await session_guard.get_sessions()
        except Exception:
            logger.exception("Не удалось получить список сессий")
            return await call.answer("Ошибка получения сессий", show_alert=True)

        sessions = [s for s in sessions if not s.current]
        target = next((s for s in sessions if str(s.hash) == hash_str), None)
        if not target:
            return await call.answer("Сессия больше не активна", show_alert=True)

        if await db.is_whitelisted(hash_str):
            await db.remove_whitelist(hash_str)
            await call.answer("Убрано из белого списка")
        else:
            await db.add_whitelist(hash_str, target.device_model, target.platform, target.ip)
            await call.answer("Добавлено в белый список ✅")

        wl = await db.get_whitelist()
        wl_hashes = {row[0] for row in wl}
        await call.message.edit_reply_markup(reply_markup=keyboards.whitelist_menu(sessions, wl_hashes))

    @router.callback_query(F.data == "menu:logs")
    async def cb_logs(call: CallbackQuery):
        if not is_admin(call.from_user.id):
            return await call.answer()
        logs = await db.get_logs(15)
        if not logs:
            text = "📋 <b>Логи</b>\n\nПока пусто."
        else:
            action_emoji = {"detected": "⚠️", "killed": "🛑"}
            lines = ["📋 <b>Логи (последние 15 событий)</b>\n"]
            for device, platform, app_name, ip, country, date_created, action, ts in logs:
                emoji = action_emoji.get(action, "•")
                verb = "обнаружена" if action == "detected" else "завершена"
                lines.append(
                    f"{emoji} <b>{device}</b> ({platform})\n"
                    f"   IP: {ip} · {country} | {app_name}\n"
                    f"   вход: {date_created} · {verb} в {ts[:19]}"
                )
            text = "\n".join(lines)
        await call.message.edit_text(text[:4000], reply_markup=keyboards.back_menu())
        await call.answer()

    @router.callback_query(F.data == "noop")
    async def cb_noop(call: CallbackQuery):
        await call.answer()

    return router
