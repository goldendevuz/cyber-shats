"""
CYBER SHATS V1.3 — Admin e'lonlari moduli
Admin tomonidan e'lon yuborilganda barcha foydalanuvchilar (yoki tanlangan plan)
brauzerda real-vaqtda ovozli xabar bilan ko'radi va eshitadi.
"""
from db import query_one, query_all, execute


def create_announcement(admin_id: int, title: str, body: str, priority: str = "normal",
                        target_plans: str = "all", voice_enabled: bool = True) -> tuple[bool, str, int]:
    title = (title or "").strip()
    body = (body or "").strip()
    if not title:
        return False, "Sarlavha majburiy.", 0
    if priority not in ("normal", "important", "urgent"):
        priority = "normal"
    if target_plans not in ("all", "free", "pro", "cyber_pro"):
        target_plans = "all"
    ann_id = execute(
        """INSERT INTO announcements
           (title, body, priority, target_plans, voice_enabled, created_by)
           VALUES (?,?,?,?,?,?)""",
        (title, body, priority, target_plans, 1 if voice_enabled else 0, admin_id)
    )
    # Har bir mos foydalanuvchiga ham notification yuboramiz
    if target_plans == "all":
        users = query_all("SELECT id FROM users WHERE is_blocked=0")
    else:
        users = query_all("SELECT id FROM users WHERE is_blocked=0 AND plan=?", (target_plans,))
    for u in users:
        execute(
            "INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
            (u["id"], title, body, "announcement")
        )

    # Saytdan chiqib ketgan foydalanuvchilarga ham Web Push orqali yetkazish
    try:
        import webpush_mod
        webpush_mod.send_push_broadcast(title, body, url="/dashboard", target_plans=target_plans)
    except Exception:
        pass  # Push sozlanmagan bo'lsa ham e'lon o'zi muvaffaqiyatli yaratiladi

    return True, "E'lon yuborildi.", ann_id


def get_active_announcements_for_user(user_id: int):
    """Foydalanuvchi hali ko'rmagan faol e'lonlar."""
    user = query_one("SELECT plan FROM users WHERE id=?", (user_id,))
    if not user:
        return []
    plan = user["plan"]
    return query_all(
        """SELECT a.* FROM announcements a
           WHERE a.is_active=1
                 AND (a.expires_at IS NULL OR a.expires_at > datetime('now'))
                 AND (a.target_plans='all' OR a.target_plans=?)
                 AND NOT EXISTS (SELECT 1 FROM announcement_views v WHERE v.announcement_id=a.id AND v.user_id=?)
           ORDER BY
               CASE a.priority WHEN 'urgent' THEN 0 WHEN 'important' THEN 1 ELSE 2 END,
               a.id DESC""",
        (plan, user_id)
    )


def mark_announcement_viewed(user_id: int, announcement_id: int):
    execute(
        "INSERT OR IGNORE INTO announcement_views (announcement_id, user_id) VALUES (?,?)",
        (announcement_id, user_id)
    )


def list_all_announcements(limit: int = 100):
    """Admin uchun barcha e'lonlar ro'yxati."""
    return query_all(
        """SELECT a.*, u.ism, u.familiya,
                  (SELECT COUNT(*) FROM announcement_views v WHERE v.announcement_id=a.id) as view_count
           FROM announcements a
           JOIN users u ON u.id = a.created_by
           ORDER BY a.id DESC LIMIT ?""",
        (limit,)
    )


def toggle_announcement(announcement_id: int):
    a = query_one("SELECT is_active FROM announcements WHERE id=?", (announcement_id,))
    if a:
        execute("UPDATE announcements SET is_active=? WHERE id=?",
                (0 if a["is_active"] else 1, announcement_id))


def delete_announcement(announcement_id: int):
    execute("DELETE FROM announcement_views WHERE announcement_id=?", (announcement_id,))
    execute("DELETE FROM announcements WHERE id=?", (announcement_id,))
