"""
CYBER SHATS V1.3 — Web Push Notifications moduli

Foydalanuvchi saytga ruxsat bersa, brauzer/qurilma push-obunasi
(endpoint + kalitlar) saqlanadi. Keyinchalik server istalgan vaqtda
o'sha qurilmaga bildirishnoma yubora oladi — SAYT YOPIQ BO'LSA HAM
(faqat qurilma yoqilgan va internetga ulangan bo'lishi kerak).

Talab: HTTPS (yoki localhost test uchun). Productionda SSL sertifikat shart.
"""
import json
from db import query_one, query_all, execute
from config import Config

try:
    from pywebpush import webpush, WebPushException
    PYWEBPUSH_AVAILABLE = True
except ImportError:
    PYWEBPUSH_AVAILABLE = False


def is_push_configured() -> bool:
    return bool(Config.VAPID_PUBLIC_KEY and Config.VAPID_PRIVATE_KEY and PYWEBPUSH_AVAILABLE)


def save_subscription(user_id: int, endpoint: str, p256dh: str, auth: str, user_agent: str = "") -> tuple[bool, str]:
    """Foydalanuvchining push obunasini saqlaydi (yoki yangilaydi)."""
    if not endpoint or not p256dh or not auth:
        return False, "Noto'g'ri obuna ma'lumotlari."
    existing = query_one("SELECT id FROM push_subscriptions WHERE endpoint=?", (endpoint,))
    if existing:
        execute(
            "UPDATE push_subscriptions SET user_id=?, p256dh=?, auth=?, user_agent=?, is_active=1, last_used_at=datetime('now') WHERE endpoint=?",
            (user_id, p256dh, auth, user_agent, endpoint)
        )
    else:
        execute(
            "INSERT INTO push_subscriptions (user_id, endpoint, p256dh, auth, user_agent) VALUES (?,?,?,?,?)",
            (user_id, endpoint, p256dh, auth, user_agent)
        )
    return True, "Obuna saqlandi."


def remove_subscription(endpoint: str):
    execute("DELETE FROM push_subscriptions WHERE endpoint=?", (endpoint,))


def get_user_subscriptions(user_id: int):
    return query_all(
        "SELECT * FROM push_subscriptions WHERE user_id=? AND is_active=1",
        (user_id,)
    )


def has_active_subscription(user_id: int) -> bool:
    row = query_one(
        "SELECT id FROM push_subscriptions WHERE user_id=? AND is_active=1 LIMIT 1",
        (user_id,)
    )
    return bool(row)


def send_push_to_user(user_id: int, title: str, body: str, url: str = "/", icon: str = None) -> dict:
    """Foydalanuvchining barcha qurilmalariga push xabar yuboradi.
    Saytdan chiqib ketgan bo'lsa ham — qurilmasi yoqilgan va internetda bo'lsa keladi.
    Returns: {"sent": int, "failed": int}"""
    if not is_push_configured():
        return {"sent": 0, "failed": 0, "error": "Push sozlanmagan"}

    subs = get_user_subscriptions(user_id)
    sent, failed = 0, 0
    payload = json.dumps({
        "title": title,
        "body": body,
        "url": url,
        "icon": icon or "/static/img/icon-192.png",
    })

    for sub in subs:
        subscription_info = {
            "endpoint": sub["endpoint"],
            "keys": {"p256dh": sub["p256dh"], "auth": sub["auth"]},
        }
        try:
            webpush(
                subscription_info=subscription_info,
                data=payload,
                vapid_private_key=Config.VAPID_PRIVATE_KEY,
                vapid_claims={"sub": Config.VAPID_CLAIM_EMAIL},
            )
            execute("UPDATE push_subscriptions SET last_used_at=datetime('now') WHERE id=?", (sub["id"],))
            sent += 1
        except WebPushException as e:
            failed += 1
            # 410/404 — obuna eskirgan, o'chirib tashlaymiz
            status = getattr(e.response, "status_code", None) if e.response else None
            if status in (404, 410):
                remove_subscription(sub["endpoint"])
        except Exception:
            failed += 1

    return {"sent": sent, "failed": failed}


def send_push_to_users(user_ids: list, title: str, body: str, url: str = "/") -> dict:
    """Bir nechta foydalanuvchiga push yuborish (masalan e'lon)."""
    total_sent, total_failed = 0, 0
    for uid in user_ids:
        r = send_push_to_user(uid, title, body, url)
        total_sent += r.get("sent", 0)
        total_failed += r.get("failed", 0)
    return {"sent": total_sent, "failed": total_failed}


def send_push_broadcast(title: str, body: str, url: str = "/", target_plans: str = "all") -> dict:
    """Hamma (yoki tanlangan plan) foydalanuvchilarga push yuborish — e'lonlar uchun."""
    if target_plans == "all":
        rows = query_all(
            "SELECT DISTINCT user_id FROM push_subscriptions WHERE is_active=1"
        )
    else:
        rows = query_all(
            """SELECT DISTINCT ps.user_id FROM push_subscriptions ps
               JOIN users u ON u.id = ps.user_id
               WHERE ps.is_active=1 AND u.plan=?""",
            (target_plans,)
        )
    user_ids = [r["user_id"] for r in rows]
    return send_push_to_users(user_ids, title, body, url)
