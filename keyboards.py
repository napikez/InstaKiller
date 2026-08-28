from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu(protection_on: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🛡 Белый список", callback_data="menu:whitelist")
    status = "🟢 Защита: Вкл (нажми, чтобы выключить)" if protection_on else "🔴 Защита: Выкл (нажми, чтобы включить)"
    b.button(text=status, callback_data="toggle_protection")
    b.button(text="📋 Логи", callback_data="menu:logs")
    b.button(text="🔄 Обновить список сессий", callback_data="menu:refresh")
    b.adjust(1)
    return b.as_markup()


def whitelist_menu(sessions, whitelisted_hashes) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if not sessions:
        b.button(text="Нет активных сессий кроме текущей", callback_data="noop")
    for s in sessions:
        mark = "✅" if str(s.hash) in whitelisted_hashes else "⬜️"
        device = s.device_model or "?"
        ip = s.ip or "?"
        label = f"{mark} {device} · {ip}"
        b.button(text=label[:64], callback_data=f"wl:{s.hash}")
    b.button(text="◀️ Назад", callback_data="menu:main")
    b.adjust(1)
    return b.as_markup()


def back_menu() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="◀️ Назад", callback_data="menu:main")
    b.adjust(1)
    return b.as_markup()
