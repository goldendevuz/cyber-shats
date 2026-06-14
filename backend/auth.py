import bcrypt
import jwt
import os
import uuid
from datetime import datetime, timedelta
from database import get_db

SECRET_KEY = os.environ.get('SECRET_KEY', 'SHATS_SUPER_SECRET_2026_CHANGE_IN_PROD')
MAX_ATTEMPTS = 3
BLOCK_COST = 100000  # so'm
TOKEN_EXPIRY_HOURS = 8


def check_ip_blocked(ip: str) -> bool:
    db = get_db()
    row = db.execute("SELECT 1 FROM blocked_ips WHERE ip_address=?", (ip,)).fetchone()
    db.close()
    return row is not None


def record_ip_attempt(ip: str):
    """3 marta xato → IP bloklanadi. (True, attempts) qaytaradi agar blok bo'lsa."""
    db = get_db()
    row = db.execute("SELECT attempts FROM ip_attempts WHERE ip_address=?", (ip,)).fetchone()
    if row:
        attempts = row['attempts'] + 1
        db.execute(
            "UPDATE ip_attempts SET attempts=?, last_attempt=CURRENT_TIMESTAMP WHERE ip_address=?",
            (attempts, ip)
        )
    else:
        attempts = 1
        db.execute("INSERT INTO ip_attempts (ip_address, attempts) VALUES (?,?)", (ip, attempts))
    db.commit()

    if attempts >= MAX_ATTEMPTS:
        db.execute(
            "INSERT OR IGNORE INTO blocked_ips (ip_address, reason) VALUES (?,?)",
            (ip, f'{MAX_ATTEMPTS} marta xato parol kiritildi')
        )
        db.execute(
            "INSERT INTO system_logs (log_type,message,ip_address) VALUES ('BLOCK','IP avtomatik bloklandi',?)",
            (ip,)
        )
        db.commit()
        db.close()
        return True, attempts

    db.close()
    return False, attempts


def clear_ip_attempts(ip: str):
    db = get_db()
    db.execute("DELETE FROM ip_attempts WHERE ip_address=?", (ip,))
    db.commit()
    db.close()


def verify_login(username: str, password: str, ip: str):
    """Foydalanuvchi login tekshiruvi.
    Returns: (token | None, message, is_blocked)
    """
    # Input tozalash
    username = (username or '').strip()[:64]
    password = (password or '')

    db = get_db()
    user = db.execute(
        "SELECT * FROM users WHERE username=?", (username,)
    ).fetchone()
    db.close()

    if not user:
        blocked, attempts = record_ip_attempt(ip)
        return None, f"Login yoki parol noto'g'ri. Urinishlar: {attempts}/{MAX_ATTEMPTS}", blocked

    status = user['status']
    if status == 'blocked':
        return None, "Hisobingiz bloklangan. Admin bilan bog'laning.", False
    if status == 'pending':
        return None, "Hisobingiz admin tasdiqlashini kutmoqda.", False
    if status == 'rejected':
        return None, "Hisobingiz rad etilgan.", False

    # Parol bcrypt tekshiruv
    stored_hash = user['password_hash']
    if not stored_hash or not bcrypt.checkpw(password.encode(), stored_hash.encode()):
        blocked, attempts = record_ip_attempt(ip)
        if blocked:
            return None, "❌ IP manzilingiz BLOKLANDI! Blokdan chiqarish uchun 100,000 so'm to'lang.", True
        return None, f"Login yoki parol noto'g'ri. Urinishlar: {attempts}/{MAX_ATTEMPTS}", False

    # Muvaffaqiyatli
    clear_ip_attempts(ip)
    log_action(user['id'], 'LOGIN', f'IP: {ip}', ip)

    jti = str(uuid.uuid4())
    payload = {
        'jti': jti,
        'user_id': user['id'],
        'username': user['username'],
        'role': user['role'],
        'status': user['status'],
        'exp': datetime.utcnow() + timedelta(hours=TOKEN_EXPIRY_HOURS)
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    return token, "Muvaffaqiyatli kirildi!", False


def verify_token(token: str):
    try:
        data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        # Revoke tekshiruv
        jti = data.get('jti')
        if jti:
            db = get_db()
            revoked = db.execute("SELECT 1 FROM revoked_tokens WHERE jti=?", (jti,)).fetchone()
            db.close()
            if revoked:
                return None
        return data
    except Exception:
        return None


def revoke_token(token: str):
    """Logout uchun token-ni bekor qilish."""
    try:
        data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'], options={"verify_exp": False})
        jti = data.get('jti')
        if jti:
            db = get_db()
            db.execute("INSERT OR IGNORE INTO revoked_tokens (jti) VALUES (?)", (jti,))
            db.commit()
            db.close()
    except Exception:
        pass


def log_action(user_id, action_type, details, ip=None):
    db = get_db()
    db.execute(
        "INSERT INTO user_actions (user_id,action_type,details) VALUES (?,?,?)",
        (user_id, action_type, details)
    )
    if ip:
        db.execute(
            "INSERT INTO user_logs (user_id,action,ip_address) VALUES (?,?,?)",
            (user_id, action_type, ip)
        )
    db.commit()
    db.close()


def is_pro(user_id: int) -> bool:
    db = get_db()
    user = db.execute("SELECT status FROM users WHERE id=?", (user_id,)).fetchone()
    sub = db.execute(
        "SELECT 1 FROM pro_subscriptions WHERE user_id=? AND status='active' AND end_date > CURRENT_TIMESTAMP",
        (user_id,)
    ).fetchone()
    db.close()
    if user and user['status'] in ('approved_pro', 'superadmin'):
        return True
    return sub is not None
