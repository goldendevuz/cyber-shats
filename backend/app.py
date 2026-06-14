"""
SHATS.KIBER — Kiberxavfsizlik o'quv platformasi
Flask + SocketIO backend (to'liq tuzatilgan versiya v3.0)

Tuzatilgan xatolar:
  1. admin_pro_users() funksiyasida @app.route yo'q edi — qo'shildi
  2. eventlet o'rniga threading ishlatiladi (Python 3.14 uchun)
  3. python-dotenv .env faylini avtomatik yuklaydi
  4. sys.path to'g'ri sozlandi (PyCharm uchun)
"""

import sys
import os

# PyCharm uchun: backend papkasini sys.path ga qo'shish
sys.path.insert(0, os.path.dirname(__file__))

# .env faylini avtomatik yuklash
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

import json
import re
import bleach
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit, join_room
from flask_cors import CORS

from database import get_db, init_db
from auth import (verify_login, verify_token, log_action, is_pro,
                  check_ip_blocked, revoke_token)
from telegram_bot import tg_send, start_bot

# ─── App sozlash ──────────────────────────────────────────────────────────
app = Flask(__name__, static_folder='../frontend', static_url_path='')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'SHATS_SUPER_SECRET_2026_CHANGE_IN_PROD')

# ─── Bilim bazasi (AI system prompt uchun) ────────────────────────────────
_KB_PATH = os.path.join(os.path.dirname(__file__), 'knowledge_base.md')

def load_knowledge_base() -> str:
    try:
        with open(_KB_PATH, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception:
        return ''

KNOWLEDGE_BASE = load_knowledge_base()

# ─── CORS sozlash ─────────────────────────────────────────────────────────
ALLOWED_ORIGINS = os.environ.get('ALLOWED_ORIGINS', 'http://localhost:5000').split(',')
CORS(app, resources={r"/api/*": {"origins": ALLOWED_ORIGINS}})

socketio = SocketIO(app, cors_allowed_origins=ALLOWED_ORIGINS, async_mode='threading')


# ─── Xavfsizlik sarlavhalari ──────────────────────────────────────────────
@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.socket.io; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "connect-src 'self' wss: ws:; "
        "img-src 'self' data:;"
    )
    return response


# ─── Helper funksiyalar ───────────────────────────────────────────────────
def get_client_ip():
    xff = request.headers.get('X-Forwarded-For', '')
    if xff:
        return xff.split(',')[0].strip()
    return request.remote_addr


def sanitize(text: str, max_len: int = 500) -> str:
    """Matnni tozalash — XSS va SQL injection uchun."""
    if not isinstance(text, str):
        return ''
    text = bleach.clean(text.strip(), tags=[], strip=True)
    return text[:max_len]


def is_safe_host(host: str) -> bool:
    """Faqat to'g'ri hostname/IP formatini qabul qilish."""
    if not host:
        return False
    if re.search(r'[;&|`$()\n\r\']', host):
        return False
    if len(host) > 253:
        return False
    return True


def auth_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user = verify_token(token)
        if not user:
            return jsonify({'error': 'Avtorizatsiya talab qilinadi'}), 401
        request.user = user
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user = verify_token(token)
        if not user or user.get('role') != 'superadmin':
            return jsonify({'error': 'Admin huquqi talab qilinadi'}), 403
        request.user = user
        return f(*args, **kwargs)
    return decorated


def pro_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user = verify_token(token)
        if not user:
            return jsonify({'error': 'Avtorizatsiya talab qilinadi'}), 401
        if not is_pro(user['user_id']) and user.get('role') != 'superadmin':
            return jsonify({'error': 'Pro versiya talab qilinadi', 'upgrade': True}), 403
        request.user = user
        return f(*args, **kwargs)
    return decorated


# ─── Static fayllar ───────────────────────────────────────────────────────
@app.route('/')
def index():
    return send_from_directory('../frontend', 'login.html')


@app.route('/<path:path>')
def serve_static(path):
    allowed_ext = ('.html', '.css', '.js', '.ico', '.png', '.jpg', '.svg', '.woff2')
    if not any(path.endswith(ext) for ext in allowed_ext):
        return jsonify({'error': 'Not found'}), 404
    return send_from_directory('../frontend', path)


# ─── Auth routes ──────────────────────────────────────────────────────────
@app.route('/api/login', methods=['POST'])
def login():
    ip = get_client_ip()
    if check_ip_blocked(ip):
        return jsonify({
            'error': '🔴 IP manzilingiz BLOKLANDI!',
            'blocked': True,
            'unblock_cost': 100000,
            'message': "Blokdan chiqarish uchun 100,000 so'm to'lang"
        }), 403

    data = request.json or {}
    username = sanitize(data.get('username', ''), max_len=64)
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'error': "Login va parol majburiy"}), 400

    token, msg, blocked = verify_login(username, password, ip)
    if token:
        db = get_db()
        u = db.execute(
            "SELECT id,first_name,last_name,username,role,status FROM users WHERE username=?",
            (username,)
        ).fetchone()
        db.close()
        return jsonify({'token': token, 'user': dict(u), 'message': msg})
    return jsonify({'error': msg, 'blocked': blocked}), 401


@app.route('/api/logout', methods=['POST'])
@auth_required
def logout():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    revoke_token(token)
    log_action(request.user['user_id'], 'LOGOUT', 'Chiqdi', get_client_ip())
    return jsonify({'message': 'Chiqildi'})


@app.route('/api/register', methods=['POST'])
def register():
    data = request.json or {}
    required = ['first_name', 'last_name', 'phone', 'email', 'age', 'telegram',
                'specialization', 'experience']
    for f in required:
        if not data.get(f):
            return jsonify({'error': f"'{f}' maydoni bo'sh"}), 400

    if not (data.get('consent1') and data.get('consent2') and data.get('consent3')):
        return jsonify({'error': '3 ta rozilikni belgilash majburiy'}), 400

    email = sanitize(data.get('email', ''), 200)
    if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
        return jsonify({'error': "Email formati noto'g'ri"}), 400

    phone = re.sub(r'[^\d+]', '', data.get('phone', ''))
    if len(phone) < 9:
        return jsonify({'error': "Telefon raqami noto'g'ri"}), 400

    telegram = sanitize(data.get('telegram', ''), 64)

    db = get_db()
    try:
        existing = db.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
        if existing:
            db.close()
            return jsonify({'error': "Bu email allaqachon ro'yxatdan o'tgan"}), 400

        db.execute("""
            INSERT INTO users
                (first_name,last_name,phone,email,age,telegram,specialization,experience,status)
            VALUES (?,?,?,?,?,?,?,?,'pending')
        """, (
            sanitize(data['first_name'], 100), sanitize(data['last_name'], 100),
            phone, email, int(data.get('age', 0)),
            telegram,
            sanitize(data['specialization'], 200), sanitize(data['experience'], 200)
        ))
        user_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        db.execute("INSERT INTO user_requests (user_id,status) VALUES (?,'pending')", (user_id,))
        db.execute(
            "INSERT INTO system_logs (log_type,message) VALUES ('REGISTER',?)",
            (f"Yangi so'rov: {data['first_name']} {data['last_name']} - {phone}",)
        )
        db.commit()
        db.close()
        return jsonify({
            'message': "✅ So'rovingiz qabul qilindi! Admin tekshirib, Telegram orqali xabar yuboradi.",
            'user_id': user_id
        })
    except Exception as e:
        db.close()
        return jsonify({'error': "Ro'yxatdan o'tishda xatolik yuz berdi"}), 400


@app.route('/api/me', methods=['GET'])
@auth_required
def me():
    db = get_db()
    u = db.execute(
        "SELECT id,first_name,last_name,username,role,status,email,phone,telegram FROM users WHERE id=?",
        (request.user['user_id'],)
    ).fetchone()
    pro = is_pro(request.user['user_id'])
    db.close()
    return jsonify({'user': dict(u), 'is_pro': pro})


# ─── Admin routes ─────────────────────────────────────────────────────────
@app.route('/api/admin/dashboard', methods=['GET'])
@admin_required
def admin_dashboard():
    db = get_db()
    stats = {
        'total_users': db.execute("SELECT COUNT(*) FROM users WHERE role='user'").fetchone()[0],
        'pro_users': db.execute("SELECT COUNT(*) FROM users WHERE status='approved_pro'").fetchone()[0],
        'free_users': db.execute("SELECT COUNT(*) FROM users WHERE status='approved_free'").fetchone()[0],
        'pending_requests': db.execute("SELECT COUNT(*) FROM user_requests WHERE status='pending'").fetchone()[0],
        'blocked_ips': db.execute("SELECT COUNT(*) FROM blocked_ips").fetchone()[0],
        'blocked_users': db.execute("SELECT COUNT(*) FROM users WHERE status='blocked'").fetchone()[0],
        'today_logins': db.execute(
            "SELECT COUNT(*) FROM user_logs WHERE action='LOGIN' AND date(created_at)=date('now')"
        ).fetchone()[0],
        'total_ai_calls': db.execute("SELECT COUNT(*) FROM shats_logs").fetchone()[0],
        'total_scans': db.execute("SELECT COUNT(*) FROM scan_logs").fetchone()[0],
    }
    db.close()
    return jsonify(stats)


@app.route('/api/admin/stats-extended', methods=['GET'])
@admin_required
def admin_stats_extended():
    """Admin panel dashboardi uchun to'liq statistik ko'rsatkichlar."""
    db = get_db()
    stats = {
        'total_users': db.execute("SELECT COUNT(*) FROM users WHERE role='user'").fetchone()[0],
        'pro_users': db.execute("SELECT COUNT(*) FROM users WHERE status='approved_pro'").fetchone()[0],
        'free_users': db.execute("SELECT COUNT(*) FROM users WHERE status='approved_free'").fetchone()[0],
        'pending_requests': db.execute("SELECT COUNT(*) FROM user_requests WHERE status='pending'").fetchone()[0],
        'blocked_ips': db.execute("SELECT COUNT(*) FROM blocked_ips").fetchone()[0],
        'blocked_users': db.execute("SELECT COUNT(*) FROM users WHERE status='blocked'").fetchone()[0],
        'today_logins': db.execute(
            "SELECT COUNT(*) FROM user_logs WHERE action='LOGIN' AND date(created_at)=date('now')"
        ).fetchone()[0],
        'total_payments': db.execute("SELECT COUNT(*) FROM payments").fetchone()[0],
        'total_ai_calls': db.execute("SELECT COUNT(*) FROM shats_logs").fetchone()[0],
        'total_scans': db.execute("SELECT COUNT(*) FROM scan_logs").fetchone()[0],
        'telegram_unread': db.execute(
            "SELECT COUNT(*) FROM telegram_messages WHERE direction='in' AND is_read=0"
        ).fetchone()[0],
        'telegram_total': db.execute("SELECT COUNT(*) FROM telegram_messages").fetchone()[0],
    }
    db.close()
    return jsonify(stats)


@app.route('/api/admin/users', methods=['GET'])
@admin_required
def admin_users():
    db = get_db()
    users = db.execute("""
        SELECT u.id,u.first_name,u.last_name,u.phone,u.email,u.telegram,
               u.username,u.role,u.status,u.specialization,u.experience,u.created_at,
               u.password_given,
               ur.login_given
        FROM users u
        LEFT JOIN user_requests ur ON ur.user_id=u.id
        WHERE u.role='user'
        ORDER BY u.created_at DESC
    """).fetchall()
    db.close()
    return jsonify([dict(u) for u in users])


@app.route('/api/admin/requests', methods=['GET'])
@admin_required
def admin_requests():
    db = get_db()
    reqs = db.execute("""
        SELECT u.id,u.first_name,u.last_name,u.phone,u.email,u.age,u.telegram,
               u.specialization,u.experience,u.created_at,
               ur.id as req_id, ur.status
        FROM users u
        JOIN user_requests ur ON ur.user_id=u.id
        WHERE ur.status='pending'
        ORDER BY u.created_at DESC
    """).fetchall()
    db.close()
    return jsonify([dict(r) for r in reqs])


@app.route('/api/admin/approve', methods=['POST'])
@admin_required
def admin_approve():
    import bcrypt
    import random
    import string
    data = request.json or {}
    user_id = data.get('user_id')
    version = data.get('version', 'free')  # free | pro

    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if not user:
        db.close()
        return jsonify({'error': 'Foydalanuvchi topilmadi'}), 404

    base = re.sub(r'[^a-z0-9]', '', (user['first_name'] or 'user').lower())[:8]
    uid = db.execute("SELECT COUNT(*) FROM users WHERE username IS NOT NULL").fetchone()[0]
    login_name = f"{base}_{uid:04d}"

    # Kuchli parol yaratish
    password = (
        ''.join(random.choices(string.ascii_uppercase, k=2)) +
        ''.join(random.choices(string.digits, k=3)) +
        ''.join(random.choices('!@#$', k=2)) +
        ''.join(random.choices(string.ascii_lowercase, k=5))
    )
    password = ''.join(random.sample(password, len(password)))

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    status = 'approved_pro' if version == 'pro' else 'approved_free'

    db.execute("UPDATE users SET username=?, password_hash=?, status=?, password_given=? WHERE id=?",
               (login_name, hashed, status, password, user_id))
    db.execute("""
        UPDATE user_requests
        SET status='approved', reviewed_by=?, reviewed_at=CURRENT_TIMESTAMP, login_given=?
        WHERE user_id=?
    """, (request.user['user_id'], login_name, user_id))

    if version == 'pro':
        db.execute(
            "INSERT INTO pro_subscriptions (user_id, end_date, status) VALUES (?, datetime('now','+30 days'), 'active')",
            (user_id,)
        )

    db.execute("INSERT INTO user_actions (user_id,action_type,details) VALUES (?,?,?)",
               (request.user['user_id'], 'APPROVE_USER',
                f"User {user_id} tasdiqlandi. Login: {login_name}, Versiya: {version}"))
    db.commit()
    db.close()

    _send_telegram(user['telegram'], login_name, password, version)

    return jsonify({
        'message': f'✅ Tasdiqlandi! Login: {login_name}, Parol: {password}',
        'login': login_name,
        'password': password
    })


@app.route('/api/admin/reject', methods=['POST'])
@admin_required
def admin_reject():
    data = request.json or {}
    db = get_db()
    db.execute("UPDATE users SET status='rejected' WHERE id=?", (data['user_id'],))
    db.execute("""
        UPDATE user_requests
        SET status='rejected', reviewed_by=?, reviewed_at=CURRENT_TIMESTAMP, rejection_reason=?
        WHERE user_id=?
    """, (request.user['user_id'], sanitize(data.get('reason', ''), 500), data['user_id']))
    db.commit()
    db.close()
    return jsonify({'message': 'Rad etildi'})


@app.route('/api/admin/block-user', methods=['POST'])
@admin_required
def admin_block_user():
    data = request.json or {}
    db = get_db()
    db.execute("UPDATE users SET status='blocked' WHERE id=?", (data['user_id'],))
    db.execute("INSERT INTO user_actions (user_id,action_type,details) VALUES (?,?,?)",
               (request.user['user_id'], 'BLOCK_USER', f"User {data['user_id']} bloklandi"))
    db.commit()
    db.close()
    return jsonify({'message': 'Bloklandi'})


@app.route('/api/admin/unblock-user', methods=['POST'])
@admin_required
def admin_unblock_user():
    data = request.json or {}
    user_id = data['user_id']
    status = data.get('status', 'approved_free')
    if status not in ('approved_free', 'approved_pro'):
        return jsonify({'error': "Noto'g'ri status"}), 400
    db = get_db()
    db.execute("UPDATE users SET status=? WHERE id=?", (status, user_id))
    db.execute("INSERT INTO user_actions (user_id,action_type,details) VALUES (?,?,?)",
               (request.user['user_id'], 'UNBLOCK_USER',
                f"User {user_id} blokdan chiqarildi → {status}"))
    db.commit()
    db.close()
    return jsonify({'message': '✅ Blokdan chiqarildi'})


@app.route('/api/admin/upgrade-pro', methods=['POST'])
@admin_required
def admin_upgrade_pro():
    data = request.json or {}
    user_id = data['user_id']
    months = max(1, min(int(data.get('months', 1)), 12))

    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if not user:
        db.close()
        return jsonify({'error': 'Foydalanuvchi topilmadi'}), 404

    db.execute("UPDATE users SET status='approved_pro' WHERE id=?", (user_id,))
    db.execute("UPDATE pro_subscriptions SET status='cancelled' WHERE user_id=? AND status='active'",
               (user_id,))
    db.execute(
        f"INSERT INTO pro_subscriptions (user_id, end_date, status) VALUES (?, datetime('now','+{months} months'), 'active')",
        (user_id,)
    )
    db.execute("INSERT INTO user_actions (user_id,action_type,details) VALUES (?,?,?)",
               (request.user['user_id'], 'UPGRADE_PRO',
                f"User {user_id} ({user['username']}) PRO ga o'tkazildi. {months} oy."))
    db.commit()
    db.close()

    _send_telegram_upgrade(user['telegram'], user['username'], months)
    return jsonify({'message': f"✅ {user['username']} PRO ga o'tkazildi ({months} oy)", 'success': True})


@app.route('/api/admin/downgrade-free', methods=['POST'])
@admin_required
def admin_downgrade_free():
    data = request.json or {}
    user_id = data['user_id']
    db = get_db()
    db.execute("UPDATE users SET status='approved_free' WHERE id=?", (user_id,))
    db.execute("UPDATE pro_subscriptions SET status='cancelled' WHERE user_id=? AND status='active'",
               (user_id,))
    db.execute("INSERT INTO user_actions (user_id,action_type,details) VALUES (?,?,?)",
               (request.user['user_id'], 'DOWNGRADE_FREE', f"User {user_id} FREE ga tushirildi"))
    db.commit()
    db.close()
    return jsonify({'message': '✅ FREE ga tushirildi'})


@app.route('/api/admin/blocked-ips', methods=['GET'])
@admin_required
def admin_blocked_ips():
    db = get_db()
    ips = db.execute("SELECT * FROM blocked_ips ORDER BY blocked_at DESC").fetchall()
    db.close()
    return jsonify([dict(i) for i in ips])


@app.route('/api/admin/unblock-ip', methods=['POST'])
@admin_required
def admin_unblock_ip():
    data = request.json or {}
    ip = data.get('ip', '')
    db = get_db()
    db.execute("DELETE FROM blocked_ips WHERE ip_address=?", (ip,))
    db.execute("DELETE FROM ip_attempts WHERE ip_address=?", (ip,))
    db.execute("INSERT INTO user_actions (user_id,action_type,details) VALUES (?,?,?)",
               (request.user['user_id'], 'UNBLOCK_IP', f"IP blokdan chiqarildi: {ip}"))
    db.commit()
    db.close()
    return jsonify({'message': 'IP blokdan chiqarildi'})


@app.route('/api/admin/logs', methods=['GET'])
@admin_required
def admin_logs():
    db = get_db()
    logs = db.execute("""
        SELECT ua.id, ua.action_type, ua.details, ua.created_at, u.username, u.first_name
        FROM user_actions ua
        LEFT JOIN users u ON u.id=ua.user_id
        ORDER BY ua.created_at DESC LIMIT 200
    """).fetchall()
    db.close()
    return jsonify([dict(l) for l in logs])


@app.route('/api/admin/monitor', methods=['GET'])
@admin_required
def admin_monitor():
    db = get_db()
    recent = db.execute("""
        SELECT ul.id, ul.action, ul.ip_address, ul.created_at, u.username, u.first_name
        FROM user_logs ul
        LEFT JOIN users u ON u.id=ul.user_id
        ORDER BY ul.created_at DESC LIMIT 100
    """).fetchall()
    db.close()
    return jsonify([dict(r) for r in recent])


@app.route('/api/admin/announce', methods=['POST'])
@admin_required
def admin_announce():
    data = request.json or {}
    title = sanitize(data.get('title', ''), 200)
    content = sanitize(data.get('content', ''), 2000)
    db = get_db()
    db.execute("INSERT INTO announcements (title,content,created_by) VALUES (?,?,?)",
               (title, content, request.user['user_id']))
    db.commit()
    db.close()
    socketio.emit('announcement', {'title': title, 'content': content}, broadcast=True)
    return jsonify({'message': "E'lon yuborildi"})


@app.route('/api/admin/telegram-messages', methods=['GET'])
@admin_required
def admin_telegram_messages():
    db = get_db()
    msgs = db.execute("""
        SELECT id, chat_id, username, first_name, direction, message, is_read, created_at
        FROM telegram_messages
        ORDER BY created_at DESC LIMIT 200
    """).fetchall()
    db.close()
    return jsonify([dict(m) for m in msgs])


@app.route('/api/admin/telegram-mark-read', methods=['POST'])
@admin_required
def admin_telegram_mark_read():
    db = get_db()
    db.execute("UPDATE telegram_messages SET is_read=1 WHERE direction='in' AND is_read=0")
    db.commit()
    db.close()
    return jsonify({'message': "Belgilandi"})


@app.route('/api/admin/telegram-reply', methods=['POST'])
@admin_required
def admin_telegram_reply():
    data = request.json or {}
    chat_id = sanitize(str(data.get('chat_id', '')), 64)
    message = sanitize(data.get('message', ''), 2000)
    if not chat_id or not message:
        return jsonify({'error': "chat_id va message majburiy"}), 400

    ok = tg_send(chat_id, f"📨 <b>SHATS.KIBER admin javobi:</b>\n\n{message}")
    db = get_db()
    db.execute(
        "INSERT INTO telegram_messages (chat_id, username, first_name, direction, message, is_read) "
        "VALUES (?,?,?, 'out', ?, 1)",
        (chat_id, '', request.user.get('username', 'admin'), message)
    )
    db.commit()
    db.close()

    log_action(request.user['user_id'], 'TELEGRAM_REPLY', f'chat_id={chat_id}', get_client_ip())
    if not ok:
        return jsonify({'message': "Saqlandi, lekin Telegramga yuborilmadi (BOT_TOKEN yo'q?)", 'sent': False})
    return jsonify({'message': "✅ Yuborildi", 'sent': True})


# ─── BUG TUZATILDI: @app.route qo'shildi ──────────────────────────────────
@app.route('/api/admin/pro-users', methods=['GET'])
@admin_required
def admin_pro_users():
    db = get_db()
    users = db.execute("""
        SELECT u.id, u.first_name, u.last_name, u.username, u.telegram,
               u.status, u.created_at,
               ps.end_date as pro_until, ps.start_date as pro_from
        FROM users u
        LEFT JOIN pro_subscriptions ps ON ps.user_id=u.id AND ps.status='active'
        WHERE u.status='approved_pro' AND u.role='user'
        ORDER BY ps.end_date DESC
    """).fetchall()
    db.close()
    return jsonify([dict(u) for u in users])


@app.route('/api/admin/user-detail/<int:user_id>', methods=['GET'])
@admin_required
def admin_user_detail(user_id):
    db = get_db()
    user = db.execute("""
        SELECT u.id, u.first_name, u.last_name, u.phone, u.email, u.telegram,
               u.username, u.role, u.status, u.specialization, u.experience, u.created_at,
               ur.login_given, ur.reviewed_at,
               ps.end_date as pro_until, ps.status as sub_status
        FROM users u
        LEFT JOIN user_requests ur ON ur.user_id=u.id
        LEFT JOIN pro_subscriptions ps ON ps.user_id=u.id AND ps.status='active'
        WHERE u.id=?
    """, (user_id,)).fetchone()
    if not user:
        db.close()
        return jsonify({'error': 'Topilmadi'}), 404

    actions = db.execute("""
        SELECT action_type, details, created_at FROM user_actions
        WHERE user_id=? ORDER BY created_at DESC LIMIT 20
    """, (user_id,)).fetchall()

    scans = db.execute("SELECT COUNT(*) FROM scan_logs WHERE user_id=?", (user_id,)).fetchone()[0]
    ai_calls = db.execute("SELECT COUNT(*) FROM shats_logs WHERE user_id=?", (user_id,)).fetchone()[0]
    db.close()

    return jsonify({
        'user': dict(user),
        'actions': [dict(a) for a in actions],
        'stats': {'scans': scans, 'ai_calls': ai_calls}
    })


# ─── Scan tools (FREE) ────────────────────────────────────────────────────
@app.route('/api/scan/ping', methods=['POST'])
@auth_required
def ping_host():
    import subprocess
    data = request.json or {}
    host = sanitize(data.get('host', ''), 253)
    if not is_safe_host(host):
        return jsonify({'error': "Noto'g'ri host formati"}), 400
    try:
        result = subprocess.run(
            ['ping', '-c', '4', '-W', '2', host],
            capture_output=True, text=True, timeout=15
        )
        log_action(request.user['user_id'], 'PING', f'Target: {host}', get_client_ip())
        output = result.stdout or result.stderr
        return jsonify({'result': output[:3000]})
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Timeout: host javob bermadi'}), 408
    except Exception:
        return jsonify({'error': "Ping bajarishda xatolik"}), 500


@app.route('/api/scan/dns', methods=['POST'])
@auth_required
def dns_lookup():
    import socket
    import subprocess
    data = request.json or {}
    host = sanitize(data.get('host', ''), 253)
    if not is_safe_host(host):
        return jsonify({'error': "Noto'g'ri host formati"}), 400
    try:
        ip = socket.gethostbyname(host)
        nslookup = subprocess.run(['nslookup', host], capture_output=True, text=True, timeout=5)
        log_action(request.user['user_id'], 'DNS_LOOKUP', f'Target: {host}', get_client_ip())
        return jsonify({'ip': ip, 'details': nslookup.stdout[:2000]})
    except socket.gaierror:
        return jsonify({'error': 'Host topilmadi'}), 404
    except Exception:
        return jsonify({'error': "DNS so'rovda xatolik"}), 500


@app.route('/api/scan/ports', methods=['POST'])
@auth_required
def port_scan():
    import socket
    data = request.json or {}
    host = sanitize(data.get('host', '127.0.0.1'), 253)
    if not is_safe_host(host):
        return jsonify({'error': "Noto'g'ri host formati"}), 400

    pro_user = is_pro(request.user['user_id']) or request.user.get('role') == 'superadmin'
    max_ports = 65535 if pro_user else 20

    ports_input = data.get('ports', list(range(1, min(21, max_ports + 1))))
    if not isinstance(ports_input, list):
        return jsonify({'error': "Portlar ro'yxat formatida bo'lishi kerak"}), 400

    ports_to_scan = []
    for p in ports_input[:max_ports]:
        try:
            pn = int(p)
            if 1 <= pn <= 65535:
                ports_to_scan.append(pn)
        except (ValueError, TypeError):
            pass

    open_ports = []
    for port in ports_to_scan:
        try:
            s = socket.socket()
            s.settimeout(0.3)
            if s.connect_ex((host, port)) == 0:
                try:
                    service = socket.getservbyport(port)
                except Exception:
                    service = 'unknown'
                open_ports.append({'port': port, 'service': service})
            s.close()
        except Exception:
            pass

    log_action(request.user['user_id'], 'PORT_SCAN', f'Target: {host}, Ports: {len(ports_to_scan)}',
               get_client_ip())
    db = get_db()
    db.execute("INSERT INTO scan_logs (user_id,scan_type,target,result) VALUES (?,?,?,?)",
               (request.user['user_id'], 'port_scan', host, json.dumps(open_ports)))
    db.commit()
    db.close()
    return jsonify({'open_ports': open_ports, 'total_scanned': len(ports_to_scan)})


# ─── PRO tools ────────────────────────────────────────────────────────────
@app.route('/api/pro/generate-hash', methods=['POST'])
@pro_required
def generate_hash():
    import hashlib
    data = request.json or {}
    text = sanitize(data.get('text', ''), 1000)
    return jsonify({
        'md5': hashlib.md5(text.encode()).hexdigest(),
        'sha1': hashlib.sha1(text.encode()).hexdigest(),
        'sha256': hashlib.sha256(text.encode()).hexdigest(),
        'sha512': hashlib.sha512(text.encode()).hexdigest(),
    })


@app.route('/api/pro/hash-crack', methods=['POST'])
@pro_required
def hash_crack():
    import hashlib
    data = request.json or {}
    hash_val = sanitize(data.get('hash', ''), 128).lower()
    hash_type = data.get('type', 'md5')
    if hash_type not in ('md5', 'sha1', 'sha256'):
        return jsonify({'error': "Noto'g'ri hash turi"}), 400

    wordlist = [
        'password', '123456', 'admin', 'qwerty', 'letmein', 'monkey',
        'dragon', 'master', 'abc123', 'welcome', 'login', 'pass',
        'hello', 'test', '1234', '12345678', 'password1', 'iloveyou'
    ]
    fn = getattr(hashlib, hash_type)
    for word in wordlist:
        if fn(word.encode()).hexdigest() == hash_val:
            log_action(request.user['user_id'], 'HASH_CRACK', f'Type: {hash_type}, Found!',
                       get_client_ip())
            return jsonify({'found': True, 'password': word})

    return jsonify({'found': False, 'message': "Wordlist'da topilmadi"})


@app.route('/api/pro/jwt-analyze', methods=['POST'])
@pro_required
def jwt_analyze():
    import base64
    data = request.json or {}
    token = data.get('token', '')
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return jsonify({'error': "JWT format noto'g'ri"}), 400

        def b64d(s):
            s += '=' * (4 - len(s) % 4)
            return json.loads(base64.urlsafe_b64decode(s).decode())

        header = b64d(parts[0])
        payload = b64d(parts[1])
        vulnerabilities = []
        if header.get('alg') == 'none':
            vulnerabilities.append("alg:none — imzosiz token qabul qilinishi mumkin!")
        if header.get('alg') in ('HS256',) and payload.get('exp'):
            exp_ts = payload.get('exp', 0)
            if exp_ts < datetime.utcnow().timestamp():
                vulnerabilities.append("Token muddati tugagan (expired)")
        log_action(request.user['user_id'], 'JWT_ANALYZE', 'JWT tahlil qilindi', get_client_ip())
        return jsonify({'header': header, 'payload': payload, 'vulnerabilities': vulnerabilities})
    except Exception:
        return jsonify({'error': "JWT tahlilida xatolik"}), 400


@app.route('/api/pro/rsa-generate', methods=['POST'])
@pro_required
def rsa_generate():
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization
    data = request.json or {}
    bits = data.get('bits', 2048)
    if bits not in (1024, 2048, 4096):
        bits = 2048

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=bits)
    priv_pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption()
    ).decode()
    pub_pem = private_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()

    log_action(request.user['user_id'], 'RSA_GENERATE', f'{bits}-bit RSA yaratildi', get_client_ip())
    return jsonify({'private_key': priv_pem, 'public_key': pub_pem})


@app.route('/api/pro/subdomain-scan', methods=['POST'])
@pro_required
def subdomain_scan():
    import socket
    data = request.json or {}
    domain = sanitize(data.get('domain', ''), 253)
    if not is_safe_host(domain):
        return jsonify({'error': "Noto'g'ri domain formati"}), 400

    wordlist = [
        'www', 'mail', 'ftp', 'admin', 'api', 'dev', 'test', 'blog',
        'shop', 'app', 'cdn', 'static', 'media', 'portal', 'vpn',
        'remote', 'secure', 'panel', 'staging', 'beta'
    ]
    found = []
    for sub in wordlist:
        try:
            host = f"{sub}.{domain}"
            ip = socket.gethostbyname(host)
            found.append({'subdomain': host, 'ip': ip})
        except Exception:
            pass

    log_action(request.user['user_id'], 'SUBDOMAIN_SCAN', f'Domain: {domain}', get_client_ip())
    return jsonify({'found': found, 'total': len(found)})


@app.route('/api/pro/xss-payloads', methods=['GET'])
@pro_required
def xss_payloads():
    """Ta'lim uchun XSS payload namunalari"""
    payloads = [
        {"payload": "<script>alert('XSS')</script>", "type": "basic", "bypass": "asosiy"},
        {"payload": "<img src=x onerror=alert('XSS')>", "type": "event", "bypass": "HTML atribut"},
        {"payload": "<svg onload=alert('XSS')>", "type": "svg", "bypass": "SVG teg"},
        {"payload": "'><script>alert('XSS')</script>", "type": "breakout", "bypass": "Atributdan chiqish"},
        {"payload": "<details open ontoggle=alert('XSS')>", "type": "html5", "bypass": "HTML5 teg"},
    ]
    log_action(request.user['user_id'], 'XSS_PAYLOADS', 'XSS payloadlar olindi', get_client_ip())
    return jsonify({'payloads': payloads, 'note': "Faqat o'z tizimingizni test qiling!"})


@app.route('/api/pro/osint/email', methods=['POST'])
@pro_required
def osint_email():
    data = request.json or {}
    email = sanitize(data.get('email', ''), 200)
    if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
        return jsonify({'error': "Email formati noto'g'ri"}), 400
    log_action(request.user['user_id'], 'OSINT_EMAIL', f'Email: {email}', get_client_ip())
    return jsonify({
        'email': email,
        'note': "Real HIBP API ulash uchun HIBP_API_KEY env o'zgaruvchisi kerak.",
        'demo': True
    })


# ─── AI routes (PRO only) ─────────────────────────────────────────────────
@app.route('/api/ai/cyber', methods=['POST'])
@pro_required
def shats_cyber():
    import requests as req
    data = request.json or {}
    question = sanitize(data.get('question', ''), 1000)
    if not question:
        return jsonify({'error': "Savol bo'sh bo'lishi mumkin emas"}), 400

    user_id = request.user['user_id']

    db = get_db()
    history = db.execute(
        "SELECT question, answer FROM shats_memory WHERE user_id=? ORDER BY created_at DESC LIMIT 8",
        (user_id,)
    ).fetchall()
    db.close()

    messages = []
    for h in reversed(list(history)):
        messages.append({'role': 'user', 'content': h['question']})
        messages.append({'role': 'assistant', 'content': h['answer']})
    messages.append({'role': 'user', 'content': question})

    api_key = os.environ.get('ANTHROPIC_API_KEY', '')
    if not api_key:
        return jsonify({'error': "AI xizmati hozir mavjud emas (ANTHROPIC_API_KEY sozlanmagan)"}), 503

    try:
        resp = req.post(
            'https://api.anthropic.com/v1/messages',
            headers={
                'Content-Type': 'application/json',
                'x-api-key': api_key,
                'anthropic-version': '2023-06-01'
            },
            json={
                'model': 'claude-sonnet-4-6',
                'max_tokens': 1000,
                'system': (
                    "Siz SHATS Cyber — kiberxavfsizlik bo'yicha mutaxassis AI assistantsiz.\n"
                    "Faqat ta'lim maqsadida yordam bering. O'zbekcha javob bering.\n"
                    "TAQIQLANADI: real hujumlar, boshqalar tizimlariga ruxsatsiz kirish, "
                    "zararli dasturlar yaratish yo'l-yo'riq berish.\n"
                    "RUXSAT: CTF yechish, ta'lim, o'z tizimini test qilish, zaifliklarni o'rganish.\n\n"
                    "Quyida sizning bilim bazangiz berilgan:\n\n"
                    + KNOWLEDGE_BASE
                ),
                'messages': messages
            },
            timeout=30
        )
        resp_data = resp.json()
        if 'error' in resp_data:
            answer = "AI xatosi: " + resp_data['error'].get('message', "Noma'lum xato")
        else:
            answer = resp_data['content'][0]['text']
    except Exception as e:
        answer = f"AI hozir mavjud emas. Keyinroq urinib ko'ring."

    db = get_db()
    db.execute("INSERT INTO shats_memory (user_id,question,answer) VALUES (?,?,?)",
               (user_id, question, answer))
    db.execute("INSERT INTO shats_logs (user_id,ai_type,question,answer) VALUES (?,?,?,?)",
               (user_id, 'cyber', question, answer))
    db.commit()
    db.close()

    log_action(user_id, 'AI_CYBER', f'Q: {question[:50]}', get_client_ip())
    return jsonify({'answer': answer})


@app.route('/api/ai/code', methods=['POST'])
@pro_required
def shats_code():
    import requests as req
    data = request.json or {}
    question = sanitize(data.get('question', ''), 1000)
    if not question:
        return jsonify({'error': "Savol bo'sh bo'lishi mumkin emas"}), 400

    user_id = request.user['user_id']
    api_key = os.environ.get('ANTHROPIC_API_KEY', '')
    if not api_key:
        return jsonify({'error': "AI xizmati hozir mavjud emas (ANTHROPIC_API_KEY sozlanmagan)"}), 503

    try:
        resp = req.post(
            'https://api.anthropic.com/v1/messages',
            headers={
                'Content-Type': 'application/json',
                'x-api-key': api_key,
                'anthropic-version': '2023-06-01'
            },
            json={
                'model': 'claude-sonnet-4-6',
                'max_tokens': 1000,
                'system': (
                    "Siz SHATS Code — dasturlash bo'yicha mutaxassis AI assistantsiz.\n"
                    "Python, JavaScript, PHP, Java, C#, Go va boshqa tillarda yordam bering.\n"
                    "O'zbekcha javob bering. Aniq kod misollar keltiring.\n\n"
                    "Quyida sizning bilim bazangiz berilgan:\n\n"
                    + KNOWLEDGE_BASE
                ),
                'messages': [{'role': 'user', 'content': question}]
            },
            timeout=30
        )
        resp_data = resp.json()
        if 'error' in resp_data:
            answer = "AI xatosi: " + resp_data['error'].get('message', "Noma'lum xato")
        else:
            answer = resp_data['content'][0]['text']
    except Exception:
        answer = "AI hozir mavjud emas. Keyinroq urinib ko'ring."

    db = get_db()
    db.execute("INSERT INTO shats_logs (user_id,ai_type,question,answer) VALUES (?,?,?,?)",
               (user_id, 'code', question, answer))
    db.commit()
    db.close()

    log_action(user_id, 'AI_CODE', f'Q: {question[:50]}', get_client_ip())
    return jsonify({'answer': answer})


# ─── To'lov ───────────────────────────────────────────────────────────────
@app.route('/api/payment/initiate', methods=['POST'])
@auth_required
def initiate_payment():
    data = request.json or {}
    ptype = data.get('type', 'pro_sub')
    if ptype not in ('pro_sub', 'unblock_ip'):
        return jsonify({'error': "Noto'g'ri to'lov turi"}), 400
    amount = 150000 if ptype == 'pro_sub' else 100000

    db = get_db()
    db.execute("INSERT INTO payments (user_id,amount,payment_type,status) VALUES (?,?,?,'pending')",
               (request.user['user_id'], amount, ptype))
    db.commit()
    db.close()
    return jsonify({
        'message': "To'lov tizimi",
        'amount': amount,
        'click_url': f'https://my.click.uz/services/pay/?service_id=SHATS&amount={amount}',
        'payme_url': f'https://checkout.paycom.uz/SHATS_{amount}'
    })


# ─── WebSocket ────────────────────────────────────────────────────────────
@socketio.on('connect')
def ws_connect():
    token = request.args.get('token', '')
    user = verify_token(token)
    if user:
        join_room(f"user_{user['user_id']}")
        join_room('general')
        if user.get('role') == 'superadmin':
            join_room('admin_room')
        emit('connected', {'msg': f"Xush kelibsiz, {user['username']}!"})


@socketio.on('team_message')
def ws_team_message(data):
    token = data.get('token', '')
    user = verify_token(token)
    if not user:
        return
    team_id = int(data.get('team_id', 0))
    message = sanitize(data.get('message', ''), 1000)
    if not message:
        return

    db = get_db()
    db.execute("INSERT INTO team_messages (team_id,user_id,message) VALUES (?,?,?)",
               (team_id, user['user_id'], message))
    db.commit()
    u = db.execute("SELECT first_name,username FROM users WHERE id=?", (user['user_id'],)).fetchone()
    db.close()

    emit('new_message', {
        'team_id': team_id,
        'user': u['username'],
        'name': u['first_name'],
        'message': message,
        'time': datetime.now().strftime('%H:%M')
    }, room=f"team_{team_id}", broadcast=True)


@socketio.on('join_team')
def ws_join_team(data):
    token = data.get('token', '')
    user = verify_token(token)
    if user:
        join_room(f"team_{data.get('team_id')}")


# ─── Telegram helper ──────────────────────────────────────────────────────
def _send_telegram(telegram_username, login, password, version):
    ADMIN_ID = os.environ.get('TELEGRAM_ADMIN_ID', '')

    user_msg = (
        f"📨 <b>SHATS.KIBER dan xabar!</b>\n\n"
        f"✅ So'rovingiz <b>TASDIQLANDI!</b>\n\n"
        f"🔐 <b>Ma'lumotlaringiz:</b>\n"
        f"   Login: <code>{login}</code>\n"
        f"   Parol: <code>{password}</code>\n"
        f"   Versiya: {'PRO ⭐' if version == 'pro' else 'FREE'}\n\n"
        f"🔗 Kirish: https://shats.uz/login\n\n"
        f"⚠️ Parolni hech kimga bermang!\n"
        f"📞 Yordam: @shats_support"
    )
    admin_msg = (
        f"🔔 <b>Yangi foydalanuvchi tasdiqlandi!</b>\n"
        f"👤 Telegram: @{telegram_username}\n"
        f"🔑 Login: <code>{login}</code>\n"
        f"📦 Versiya: {'PRO ⭐' if version == 'pro' else 'FREE'}"
    )

    if telegram_username:
        tg_send(f"@{telegram_username.lstrip('@')}", user_msg)
    if ADMIN_ID:
        tg_send(ADMIN_ID, admin_msg)


def _send_telegram_upgrade(telegram_username, username, months):
    ADMIN_ID = os.environ.get('TELEGRAM_ADMIN_ID', '')
    msg = (
        f"⭐ <b>SHATS.KIBER — PRO Versiya!</b>\n\n"
        f"🎉 Hisobingiz <b>PRO versiyaga o'tkazildi!</b>\n\n"
        f"👤 Login: <code>{username}</code>\n"
        f"📅 Muddat: {months} oy\n\n"
        f"✅ Eski login va parolingiz O'ZGARMAGAN!\n"
        f"📞 Yordam: @shats_support"
    )
    if telegram_username:
        tg_send(f"@{telegram_username.lstrip('@')}", msg)
    if ADMIN_ID:
        tg_send(ADMIN_ID, f"⭐ {username} PRO ga o'tkazildi ({months} oy)")


# ─── Ishga tushirish ──────────────────────────────────────────────────────
if __name__ == '__main__':
    init_db()
    start_bot(socketio)
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    port = int(os.environ.get("PORT", 8080))
    print(f"🚀 SHATS.KIBER server ishga tushdi: http://localhost:{port}")
    print(f"👑 Admin panel: http://localhost:{port}/admin.html")
    print(f"🔐 Admin login: superadmin / (SUPERADMIN_PASSWORD .env dan)")
    socketio.run(app, host='0.0.0.0', port=port, debug=debug_mode)
