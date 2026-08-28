import os

# Учётные данные приложения Telegram (my.telegram.org) — для userbot-клиента,
# который логинится ПОД ТВОИМ аккаунтом и видит список сессий.
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")

# Строка сессии, полученная один раз локально через gen_session.py
SESSION_STRING = os.getenv("SESSION_STRING", "")

# Токен обычного бота (BotFather) — через него будет управление (меню, кнопки)
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Твой Telegram user id — только этот пользователь сможет управлять ботом
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# Как часто (в секундах) проверять список активных сессий
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "20"))

# Путь к файлу базы данных (whitelist, логи, настройки)
DB_PATH = os.getenv("DB_PATH", "instasession.db")
