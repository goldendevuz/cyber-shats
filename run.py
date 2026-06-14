#!/usr/bin/env python3
"""
SHATS.KIBER — PyCharm uchun ishga tushirish fayli
Bu faylni to'g'ridan-to'g'ri PyCharm da run qiling!

Loyiha tuzilmasi:
  shats_kiber/
  ├── run.py          ← SHU FAYLNI ISHGA TUSHIRING
  ├── .env            ← .env.example dan nusxa oling
  ├── requirements.txt
  ├── backend/
  │   ├── app.py
  │   ├── auth.py
  │   ├── database.py
  │   ├── telegram_bot.py
  │   └── knowledge_base.md
  ├── frontend/
  │   ├── login.html
  │   ├── register.html
  │   ├── dashboard.html
  │   └── admin.html
  └── database/
      └── shats.db  (avtomatik yaratiladi)

Ishga tushirishdan oldin:
  1. pip install -r requirements.txt
  2. cp .env.example .env
  3. .env faylini oching va sozlang
  4. Bu faylni run qiling
"""

import sys
import os

# Loyiha ildiz papkasini sys.path ga qo'shish
ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.join(ROOT, 'backend')
sys.path.insert(0, BACKEND)
sys.path.insert(0, ROOT)

# .env avtomatik yuklash
from dotenv import load_dotenv
load_dotenv(os.path.join(ROOT, '.env'))

# Backend ni import qilish va ishga tushirish
from backend.app import app, socketio, init_db, start_bot

if __name__ == '__main__':
    print("=" * 50)
    print("🛡  SHATS.KIBER v3.0 — ishga tushmoqda...")
    print("=" * 50)
    init_db()
    start_bot(socketio)
    port = int(os.environ.get("PORT", 8080))
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    print(f"\n✅ Server tayyor!")
    print(f"🌐 Asosiy:      http://localhost:{port}")
    print(f"👑 Admin panel: http://localhost:{port}/admin.html")
    print(f"🔐 Admin login: superadmin")
    print(f"🔑 Admin parol: SUPERADMIN_PASSWORD (.env faylidan)")
    print(f"\n⚠️  To'xtatish uchun: Ctrl+C\n")
    socketio.run(
      app,
      host="0.0.0.0",
      port=port,
      allow_unsafe_werkzeug=True
  )
