# ============================================================
# CYBER SHATS — Umumiy yordamchi funksiyalar
# ============================================================
import datetime
from flask import jsonify


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
