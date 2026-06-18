# ============================================================
# CYBER SHATS — Autentifikatsiya yordamchilari (session asosida)
# ============================================================
from functools import wraps
from flask import session, redirect, url_for, request, flash, jsonify
from db import query_one


def get_current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return query_one("SELECT * FROM users WHERE id=?", (uid,))


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Davom etish uchun avval tizimga kiring.", "warn")
            return redirect(url_for("login", next=request.path))
        user = get_current_user()
        if not user or user["is_blocked"]:
            session.clear()
            flash("Hisobingiz bloklangan yoki topilmadi.", "error")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        user = get_current_user()
        if not user or user["role"] not in ("admin", "mentor"):
            flash("Bu sahifa faqat administratorlar uchun.", "error")
            return redirect(url_for("dashboard"))
        return view(*args, **kwargs)
    return wrapped


def api_login_required(view):
    """API endpointlar uchun — JSON xato qaytaradi, redirect qilmaydi."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return jsonify(success=False, data=None, error="Avtorizatsiya talab qilinadi", ts=None), 401
        return view(*args, **kwargs)
    return wrapped
