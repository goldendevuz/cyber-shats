"""
CYBER SHATS — Google va GitHub OAuth ro'yxatdan o'tish
Foydalanish: app.register_blueprint(oauth_bp)
"""
import os, urllib.parse, urllib.request, json, secrets

from flask import Blueprint, redirect, request, session, flash, url_for
from werkzeug.security import generate_password_hash

from config import Config
from db import query_one, execute, log_action
from security import log_security_event

oauth_bp = Blueprint("oauth", __name__)

GOOGLE_AUTH_URL   = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL  = "https://oauth2.googleapis.com/token"
GOOGLE_INFO_URL   = "https://www.googleapis.com/oauth2/v3/userinfo"

GITHUB_AUTH_URL   = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL  = "https://github.com/login/oauth/access_token"
GITHUB_INFO_URL   = "https://api.github.com/user"
GITHUB_EMAIL_URL  = "https://api.github.com/user/emails"


def _fetch(url, headers=None, data=None):
    req = urllib.request.Request(url, headers=headers or {}, data=data)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())


def _oauth_redirect(base, **params):
    return redirect(base + "?" + urllib.parse.urlencode(params))


def _get_or_create_oauth_user(provider, provider_id, email, name):
    """OAuth orqali foydalanuvchini topadi yoki yangi yaratadi."""
    # Allaqachon bog'langan bo'lsa
    link = query_one("SELECT * FROM oauth_links WHERE provider=? AND provider_id=?",
                     (provider, provider_id))
    if link:
        return query_one("SELECT * FROM users WHERE id=?", (link["user_id"],))

    # Email orqali mavjud foydalanuvchini topish
    user = query_one("SELECT * FROM users WHERE email=?", (email,))
    if user:
        # Bog'laymiz
        execute("INSERT OR IGNORE INTO oauth_links (user_id, provider, provider_id, email, name) VALUES (?,?,?,?,?)",
                (user["id"], provider, provider_id, email, name))
        execute("UPDATE users SET oauth_provider=? WHERE id=?", (provider, user["id"]))
        return user

    # Yangi foydalanuvchi yaratish
    parts = (name or "User").split(maxsplit=1)
    ism = parts[0]
    familiya = parts[1] if len(parts) > 1 else ""
    fake_pass = generate_password_hash(secrets.token_hex(24))
    execute(
        "INSERT INTO users (ism, familiya, email, password_hash, role, oauth_provider) VALUES (?,?,?,?,?,?)",
        (ism, familiya, email, fake_pass, "student", provider)
    )
    uid = query_one("SELECT id FROM users WHERE email=?", (email,))["id"]
    execute("INSERT OR IGNORE INTO oauth_links (user_id, provider, provider_id, email, name) VALUES (?,?,?,?,?)",
            (uid, provider, provider_id, email, name))
    execute("INSERT OR IGNORE INTO user_ratings (user_id, total_score, rank_position) VALUES (?,?,0)", (uid, 0))
    log_action(uid, "oauth_register", details=f"provider:{provider}", ip=request.remote_addr)
    return query_one("SELECT * FROM users WHERE id=?", (uid,))


# ==================================================================
# GOOGLE OAuth
# ==================================================================
@oauth_bp.route("/auth/google")
def google_login():
    if not Config.GOOGLE_CLIENT_ID:
        flash("Google OAuth sozlanmagan.", "error")
        return redirect(url_for("login"))
    state = secrets.token_urlsafe(16)
    session["oauth_state"] = state
    return _oauth_redirect(GOOGLE_AUTH_URL,
        client_id=Config.GOOGLE_CLIENT_ID,
        redirect_uri=Config.OAUTH_REDIRECT_BASE + "/auth/google/callback",
        response_type="code",
        scope="openid email profile",
        state=state,
        access_type="offline",
        prompt="select_account"
    )


@oauth_bp.route("/auth/google/callback")
def google_callback():
    if request.args.get("state") != session.pop("oauth_state", None):
        flash("OAuth xatosi: state mos kelmadi.", "error")
        return redirect(url_for("login"))
    code = request.args.get("code")
    if not code:
        flash("Google orqali kirish bekor qilindi.", "warn")
        return redirect(url_for("login"))
    try:
        data = urllib.parse.urlencode({
            "code": code,
            "client_id": Config.GOOGLE_CLIENT_ID,
            "client_secret": Config.GOOGLE_CLIENT_SECRET,
            "redirect_uri": Config.OAUTH_REDIRECT_BASE + "/auth/google/callback",
            "grant_type": "authorization_code"
        }).encode()
        tokens = _fetch(GOOGLE_TOKEN_URL, {"Content-Type": "application/x-www-form-urlencoded"}, data)
        access_token = tokens.get("access_token", "")
        info = _fetch(GOOGLE_INFO_URL, {"Authorization": f"Bearer {access_token}"})
        email = info.get("email", "")
        name  = info.get("name", "")
        gid   = info.get("sub", "")
        if not email:
            raise ValueError("Email topilmadi")
        user = _get_or_create_oauth_user("google", gid, email, name)
        if not user or user.get("is_blocked"):
            flash("Hisob bloklangan yoki topilmadi.", "error")
            return redirect(url_for("login"))
        session["user_id"] = user["id"]
        execute("UPDATE users SET last_login_ip=?, failed_login_count=0, locked_until=NULL WHERE id=?",
                (request.remote_addr, user["id"]))
        log_action(user["id"], "google_login", ip=request.remote_addr)
        flash(f"Xush kelibsiz, {user['ism']}! Google orqali kirdingiz.", "success")
        return redirect(url_for("dashboard"))
    except Exception as e:
        log_security_event(None, "oauth_error", request.remote_addr,
                           request.headers.get("User-Agent",""), f"google:{e}", "medium")
        flash("Google orqali kirish xatosi. Qayta urinib ko'ring.", "error")
        return redirect(url_for("login"))


# ==================================================================
# GITHUB OAuth
# ==================================================================
@oauth_bp.route("/auth/github")
def github_login():
    if not Config.GITHUB_CLIENT_ID:
        flash("GitHub OAuth sozlanmagan.", "error")
        return redirect(url_for("login"))
    state = secrets.token_urlsafe(16)
    session["oauth_state"] = state
    return _oauth_redirect(GITHUB_AUTH_URL,
        client_id=Config.GITHUB_CLIENT_ID,
        redirect_uri=Config.OAUTH_REDIRECT_BASE + "/auth/github/callback",
        scope="user:email",
        state=state
    )


@oauth_bp.route("/auth/github/callback")
def github_callback():
    if request.args.get("state") != session.pop("oauth_state", None):
        flash("OAuth xatosi: state mos kelmadi.", "error")
        return redirect(url_for("login"))
    code = request.args.get("code")
    if not code:
        flash("GitHub orqali kirish bekor qilindi.", "warn")
        return redirect(url_for("login"))
    try:
        data = urllib.parse.urlencode({
            "client_id": Config.GITHUB_CLIENT_ID,
            "client_secret": Config.GITHUB_CLIENT_SECRET,
            "code": code,
            "redirect_uri": Config.OAUTH_REDIRECT_BASE + "/auth/github/callback"
        }).encode()
        tokens = _fetch(GITHUB_TOKEN_URL,
                        {"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
                        data)
        access_token = tokens.get("access_token", "")
        info = _fetch(GITHUB_INFO_URL, {"Authorization": f"Bearer {access_token}", "User-Agent": "CyberShats"})
        gid  = str(info.get("id", ""))
        name = info.get("name") or info.get("login", "")
        email = info.get("email")
        if not email:
            emails = _fetch(GITHUB_EMAIL_URL, {"Authorization": f"Bearer {access_token}", "User-Agent": "CyberShats"})
            primary = next((e for e in emails if e.get("primary") and e.get("verified")), None)
            email = primary["email"] if primary else None
        if not email:
            flash("GitHub hisobingizda tasdiqlangan email topilmadi.", "error")
            return redirect(url_for("login"))
        user = _get_or_create_oauth_user("github", gid, email, name)
        if not user or user.get("is_blocked"):
            flash("Hisob bloklangan yoki topilmadi.", "error")
            return redirect(url_for("login"))
        session["user_id"] = user["id"]
        execute("UPDATE users SET last_login_ip=?, failed_login_count=0, locked_until=NULL WHERE id=?",
                (request.remote_addr, user["id"]))
        log_action(user["id"], "github_login", ip=request.remote_addr)
        flash(f"Xush kelibsiz, {user['ism']}! GitHub orqali kirdingiz.", "success")
        return redirect(url_for("dashboard"))
    except Exception as e:
        log_security_event(None, "oauth_error", request.remote_addr,
                           request.headers.get("User-Agent",""), f"github:{e}", "medium")
        flash("GitHub orqali kirish xatosi. Qayta urinib ko'ring.", "error")
        return redirect(url_for("login"))
