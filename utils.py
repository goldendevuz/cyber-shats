# ============================================================
# CYBER SHATS — Umumiy yordamchi funksiyalar
# ============================================================
import datetime
from flask import jsonify


# O'zbekiston (Toshkent) vaqt zonasi — UTC+5, yil davomida o'zgarmaydi (DST yo'q)
TASHKENT_OFFSET = datetime.timedelta(hours=5)


def to_tashkent(iso_str, fmt="%d.%m.%Y %H:%M"):
    """
    Bazadagi UTC vaqtni (datetime('now') SQLite UTC qaytaradi) O'zbekiston
    mahalliy vaqtiga (UTC+5) o'tkazib, berilgan formatda matn qaytaradi.
    Bo'sh yoki noto'g'ri qiymat uchun bo'sh satr qaytaradi.
    """
    if not iso_str:
        return ""
    try:
        dt = datetime.datetime.fromisoformat(str(iso_str).replace("Z", ""))
    except Exception:
        return str(iso_str)
    local_dt = dt + TASHKENT_OFFSET
    return local_dt.strftime(fmt)


def api_response(success=True, data=None, error=None, status=200):
    """Loyihaning standart API javob formati: {success, data, error, ts}"""
    body = {
        "success": success,
        "data": data,
        "error": error,
        "ts": datetime.datetime.utcnow().isoformat() + "Z",
    }
    return jsonify(body), status


def time_ago_uz(iso_str):
    """ISO vaqtni 'N daqiqa oldin' kabi o'zbekcha formatga o'tkazadi."""
    try:
        dt = datetime.datetime.fromisoformat(str(iso_str).replace("Z", ""))
    except Exception:
        return ""
    now = datetime.datetime.now()
    diff = now - dt
    secs = diff.total_seconds()
    if secs < 60:
        return "hozir"
    if secs < 3600:
        return f"{int(secs // 60)} daqiqa oldin"
    if secs < 86400:
        return f"{int(secs // 3600)} soat oldin"
    if secs < 86400 * 30:
        return f"{int(secs // 86400)} kun oldin"
    return dt.strftime("%d.%m.%Y")


def fmt_duration(seconds):
    seconds = int(seconds or 0)
    m = seconds // 60
    s = seconds % 60
    if m >= 60:
        return f"{m // 60} soat {m % 60} daq"
    return f"{m} daq {s} sek" if s else f"{m} daq"


def send_email(to_email: str, subject: str, body: str) -> bool:
    """
    SMTP orqali oddiy matnli email yuboradi.
    .env faylda SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD sozlanishi shart.
    Sozlanmagan bo'lsa, jim ravishda False qaytaradi (xato chiqarmaydi).
    """
    import os
    smtp_host = os.environ.get("SMTP_HOST", "")
    smtp_port = os.environ.get("SMTP_PORT", "587")
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_password = os.environ.get("SMTP_PASSWORD", "")

    if not smtp_host or not smtp_user or not smtp_password or not to_email:
        return False

    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        msg = MIMEMultipart()
        msg["From"] = smtp_user
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        with smtplib.SMTP(smtp_host, int(smtp_port), timeout=10) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
        return True
    except Exception:
        return False
