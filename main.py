import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiohttp import web

import config
import db
from userbot import SessionGuard
from bot_handlers import setup_handlers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger("instasession.main")


async def health(request):
    return web.Response(text="InstaSession is running")


async def run_web():
    app = web.Application()
    app.router.add_get("/", health)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", "10000"))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info("Health server слушает порт %s", port)


def check_config():
    missing = []
    if not config.API_ID:
        missing.append("API_ID")
    if not config.API_HASH:
        missing.append("API_HASH")
    if not config.SESSION_STRING:
        missing.append("SESSION_STRING")
    if not config.BOT_TOKEN:
        missing.append("BOT_TOKEN")
    if not config.ADMIN_ID:
        missing.append("ADMIN_ID")
    if missing:
        logger.error("Не заданы переменные окружения: %s", ", ".join(missing))
        sys.exit(1)


async def main():
    check_config()
    await db.init_db(config.DB_PATH)
    if await db.get_setting("protection_enabled") is None:
        await db.set_setting("protection_enabled", "1")

    bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher()

    async def notify(text: str):
        try:
            await bot.send_message(config.ADMIN_ID, text)
        except Exception:
            logger.warning("Не удалось отправить уведомление админу", exc_info=True)

    guard = SessionGuard(
        api_id=config.API_ID,
        api_hash=config.API_HASH,
        session_string=config.SESSION_STRING,
        bot_notify_callback=notify,
        check_interval=config.CHECK_INTERVAL,
    )

    router = setup_handlers(guard, config.ADMIN_ID)
    dp.include_router(router)

    await run_web()
    await guard.start()

    logger.info("InstaSession запущен, старт polling бота")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
