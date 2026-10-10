"""Один раз запусти у себя на компьютере, чтобы получить TG_SESSION.

    python scripts/telegram_login.py

Спросит телефон, код из Telegram и (если есть) облачный пароль.
Напечатанная строка — это ключ к твоему аккаунту: храни её только в секретах, никому не отправляй.
"""
from telethon.sessions import StringSession
from telethon.sync import TelegramClient

api_id = int(input("TG_API_ID (с my.telegram.org): ").strip())
api_hash = input("TG_API_HASH: ").strip()

with TelegramClient(StringSession(), api_id, api_hash) as client:
    print("\nГотово. Твоя TG_SESSION (скопируй целиком в секреты):\n")
    print(client.session.save())
