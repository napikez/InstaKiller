import aiosqlite
from datetime import datetime

DB_PATH = None


async def init_db(path: str):
    global DB_PATH
    DB_PATH = path
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS whitelist (
            hash TEXT PRIMARY KEY,
            device TEXT,
            platform TEXT,
            ip TEXT,
            added_at TEXT
        )""")
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hash TEXT,
            device TEXT,
            platform TEXT,
            app_name TEXT,
            ip TEXT,
            country TEXT,
            date_created TEXT,
            action TEXT,
            timestamp TEXT
        )""")
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )""")
        await conn.commit()


async def get_setting(key: str, default=None):
    async with aiosqlite.connect(DB_PATH) as conn:
        cur = await conn.execute("SELECT value FROM settings WHERE key=?", (key,))
        row = await cur.fetchone()
        return row[0] if row else default


async def set_setting(key: str, value):
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute(
            "INSERT INTO settings(key, value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, str(value)),
        )
        await conn.commit()


async def is_whitelisted(hash_) -> bool:
    async with aiosqlite.connect(DB_PATH) as conn:
        cur = await conn.execute("SELECT 1 FROM whitelist WHERE hash=?", (str(hash_),))
        return (await cur.fetchone()) is not None


async def is_whitelisted_by_device(device: str, platform: str) -> bool:
    """Доп. проверка: если то же устройство/платформа уже были одобрены
    (у сессии на Telegram меняется hash при каждом новом входе,
    поэтому чистая проверка по hash не переживает повторный логин)."""
    if not device:
        return False
    async with aiosqlite.connect(DB_PATH) as conn:
        cur = await conn.execute(
            "SELECT 1 FROM whitelist WHERE device=? AND platform=?", (device, platform)
        )
        return (await cur.fetchone()) is not None


async def add_whitelist(hash_, device, platform, ip):
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute(
            "INSERT OR REPLACE INTO whitelist(hash, device, platform, ip, added_at) VALUES(?,?,?,?,?)",
            (str(hash_), device, platform, ip, datetime.utcnow().isoformat()),
        )
        await conn.commit()


async def remove_whitelist(hash_):
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute("DELETE FROM whitelist WHERE hash=?", (str(hash_),))
        await conn.commit()


async def get_whitelist():
    async with aiosqlite.connect(DB_PATH) as conn:
        cur = await conn.execute("SELECT hash, device, platform, ip FROM whitelist")
        return await cur.fetchall()


async def add_log(hash_, device, platform, app_name, ip, country, date_created, action):
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute(
            """INSERT INTO logs(hash, device, platform, app_name, ip, country, date_created, action, timestamp)
               VALUES(?,?,?,?,?,?,?,?,?)""",
            (str(hash_), device, platform, app_name, ip, country, date_created, action,
             datetime.utcnow().isoformat()),
        )
        await conn.commit()


async def get_logs(limit: int = 15):
    async with aiosqlite.connect(DB_PATH) as conn:
        cur = await conn.execute(
            """SELECT device, platform, app_name, ip, country, date_created, action, timestamp
               FROM logs ORDER BY id DESC LIMIT ?""",
            (limit,),
        )
        return await cur.fetchall()
