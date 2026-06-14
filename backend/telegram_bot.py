"""
SHATS.KIBER — Telegram bot integratsiyasi

Vazifalari:
  1. Foydalanuvchilarga xabar yuborish (login/parol, PRO tasdiq, e'lonlar va h.k.)
  2. Botga yozilgan xabarlarni qabul qilish, bazaga saqlash va admin (@shedow_777 /
     TELEGRAM_ADMIN_ID) ga yo'naltirish — Admin paneldagi "Telegram" bo'limida
     real vaqtda ko'rinadi va hisoblagichlar (badge) haqiqiy son bilan yangilanadi.
  3. Admin panel orqali foydalanuvchiga javob yozish (reply) imkoniyati.

Eslatma: agar .env faylida TELEGRAM_BOT_TOKEN bo'sh bo'lsa, bot ishlamaydi,
lekin server xatosiz davom etadi (xabarlar konsolga chiqariladi).
"""

import os
import time
import threading
import requests as req

from database import get_db

BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
ADMIN_ID = os.environ.get('TELEGRAM_ADMIN_ID', '')
ADMIN_USERNAME = os.environ.get('TELEGRAM_ADMIN_USERNAME', 'shedow_777')

API_URL = f'https://api.telegram.org/bot{BOT_TOKEN}'

_polling_started = False


def tg_send(chat_id, text, parse_mode='HTML'):
    """Telegramga xabar yuboradi. chat_id — raqam (user_id) yoki '@username'."""
    if not BOT_TOKEN:
        print(f"[Telegram log] -> {chat_id}: {text[:80]}")
        return False
    try:
        r = req.post(
            f'{API_URL}/sendMessage',
            json={'chat_id': chat_id, 'text': text, 'parse_mode': parse_mode},
            timeout=10
        )
        return r.ok
    except Exception as e:
        print(f"[Telegram xato] {e}")
        return False


def _save_message(chat_id, username, first_name, message, direction='in'):
    db = get_db()
    db.execute(
        "INSERT INTO telegram_messages (chat_id, username, first_name, direction, message) "
        "VALUES (?,?,?,?,?)",
        (str(chat_id), username or '', first_name or '', direction, message)
    )
    db.commit()
    msg_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    db.close()
    return msg_id


def _forward_to_admin(chat_id, username, first_name, message):
    """Foydalanuvchidan kelgan xabarni admin (@shedow_777) ga yuboradi."""
    who = f"@{username}" if username else (first_name or f"ID:{chat_id}")
    text = (
        f"📩 <b>Yangi xabar — SHATS.KIBER bot</b>\n\n"
        f"👤 Kimdan: {who}\n"
        f"🆔 chat_id: <code>{chat_id}</code>\n\n"
        f"💬 Xabar:\n{message}\n\n"
        f"↩️ Javob berish uchun Admin panel → Telegram bo'limidan foydalaning."
    )
    target = ADMIN_ID or f"@{ADMIN_USERNAME}"
    if target:
        tg_send(target, text)


def _handle_update(update, socketio=None):
    msg = update.get('message') or update.get('edited_message')
    if not msg:
        return

    chat = msg.get('chat', {})
    chat_id = chat.get('id')
    username = chat.get('username', '')
    first_name = chat.get('first_name', '')
    text = msg.get('text', '')

    if not text or chat_id is None:
        return

    if text.strip() == '/start':
        tg_send(
            chat_id,
            "👋 <b>SHATS.KIBER botiga xush kelibsiz!</b>\n\n"
            "Savolingiz, takliflaringiz yoki muammolaringizni shu yerga yozing — "
            "admin tez orada javob beradi.\n\n"
            "🔗 Saytga kirish: https://shats.uz"
        )

    msg_id = _save_message(chat_id, username, first_name, text, direction='in')
    _forward_to_admin(chat_id, username, first_name, text)

    if socketio:
        try:
            socketio.emit('telegram_message', {
                'id': msg_id,
                'chat_id': str(chat_id),
                'username': username,
                'first_name': first_name,
                'message': text,
                'direction': 'in'
            }, room='admin_room')
        except Exception as e:
            print(f"[Telegram socket xato] {e}")


def _poll_loop(socketio=None):
    print("🤖 Telegram bot polling ishga tushdi...")
    offset = 0
    while True:
        try:
            r = req.get(
                f'{API_URL}/getUpdates',
                params={'offset': offset, 'timeout': 25},
                timeout=35
            )
            data = r.json()
            if not data.get('ok'):
                time.sleep(5)
                continue
            for update in data.get('result', []):
                offset = update['update_id'] + 1
                _handle_update(update, socketio=socketio)
        except req.exceptions.RequestException:
            time.sleep(5)
        except Exception as e:
            print(f"[Telegram poll xato] {e}")
            time.sleep(5)


def start_bot(socketio=None):
    """Background thread'da Telegram pollingni ishga tushiradi (bir marta)."""
    global _polling_started
    if _polling_started:
        return
    if not BOT_TOKEN:
        print("⚠️  TELEGRAM_BOT_TOKEN sozlanmagan — bot polling o'tkazib yuborildi.")
        return
    _polling_started = True
    t = threading.Thread(target=_poll_loop, args=(socketio,), daemon=True)
    t.start()
