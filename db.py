# ============================================================
# CYBER SHATS — Baza bilan ishlash uchun yordamchi funksiyalar
# ============================================================
import sqlite3
from flask import g, current_app


def get_db():
    """Joriy so'rov uchun SQLite ulanishini qaytaradi (har bir request uchun bitta)."""
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DB_PATH"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def query_one(sql, args=()):
    cur = get_db().execute(sql, args)
    row = cur.fetchone()
    return dict(row) if row else None


def query_all(sql, args=()):
    cur = get_db().execute(sql, args)
    rows = cur.fetchall()
    return [dict(r) for r in rows]


def execute(sql, args=()):
    db = get_db()
    cur = db.execute(sql, args)
    db.commit()
    return cur.lastrowid


def log_action(user_id, action, details="", ip=""):
    """Har bir muhim amalni xavfsizlik jurnaliga (action_logs) yozadi."""
    try:
        execute(
            "INSERT INTO action_logs (user_id, action, details, ip) VALUES (?,?,?,?)",
            (user_id, action, details, ip),
        )
    except Exception:
        pass  # log yozilmasa ham asosiy funksiya to'xtamasligi kerak
