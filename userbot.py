import asyncio
import logging

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.account import GetAuthorizationsRequest, ResetAuthorizationRequest

import db

logger = logging.getLogger("instasession.userbot")


class SessionGuard:
    """Логинится под аккаунтом-владельцем и следит за списком активных сессий."""

    def __init__(self, api_id, api_hash, session_string, bot_notify_callback, check_interval=20):
        self.client = TelegramClient(StringSession(session_string), api_id, api_hash)
        self.notify = bot_notify_callback
        self.check_interval = check_interval
        self._running = False
        self._seen_hashes = set()  # чтобы не слать "обнаружено" на каждый тик поллинга

    async def start(self):
        await self.client.start()
        me = await self.client.get_me()
        logger.info("SessionGuard подключен как %s", getattr(me, "username", me.id))
        self._running = True
        asyncio.create_task(self._poll_loop())

    async def stop(self):
        self._running = False
        await self.client.disconnect()

    async def get_sessions(self):
        result = await self.client(GetAuthorizationsRequest())
        return result.authorizations

    async def kill_session(self, hash_):
        await self.client(ResetAuthorizationRequest(hash=hash_))

    async def _poll_loop(self):
        while self._running:
            try:
                await self._check_once()
            except Exception:
                logger.exception("Ошибка при проверке сессий")
            await asyncio.sleep(self.check_interval)

    async def _check_once(self):
        protection_on = (await db.get_setting("protection_enabled", "1")) == "1"
        auths = await self.get_sessions()

        live_hashes = set()
        for a in auths:
            if a.current:
                continue

            live_hashes.add(str(a.hash))

            device = a.device_model or "?"
            platform = f"{a.platform or ''} {a.system_version or ''}".strip() or "?"
            app_name = f"{a.app_name or ''} {a.app_version or ''}".strip() or "?"
            ip = a.ip or "?"
            country = a.country or "?"
            date_created = a.date_created.isoformat() if a.date_created else "?"

            whitelisted = await db.is_whitelisted(a.hash) or await db.is_whitelisted_by_device(
                a.device_model or "", f"{a.platform or ''} {a.system_version or ''}".strip()
            )

            if whitelisted:
                continue

            is_new_to_us = str(a.hash) not in self._seen_hashes
            if is_new_to_us:
                self._seen_hashes.add(str(a.hash))
                await db.add_log(a.hash, device, platform, app_name, ip, country, date_created, "detected")
                await self.notify(
                    "⚠️ <b>Новая сессия обнаружена</b>\n"
                    f"📱 Устройство: {device}\n"
                    f"💻 Платформа: {platform}\n"
                    f"📦 Приложение: {app_name}\n"
                    f"🌍 IP: {ip} ({country})\n"
                    f"🕒 Дата входа: {date_created}"
                )

            if protection_on:
                try:
                    await self.kill_session(a.hash)
                    await db.add_log(a.hash, device, platform, app_name, ip, country, date_created, "killed")
                    await self.notify(f"🛑 Сессия завершена: {device} · {ip}")
                except Exception:
                    logger.exception("Не удалось завершить сессию %s", a.hash)

        # чистим кэш от сессий, которых уже нет в списке (сами вышли/были убиты)
        self._seen_hashes &= live_hashes
