"""
CYBER SHATS V1.3 — Hacker Lab (Amaliyot Paneli) moduli

Bu panel foydalanuvchi tanlagan yo'nalishga moslashadigan amaliy bo'lim.
- Pro foydalanuvchi: 100,000 CODE to'lab kirish huquqini sotib oladi
- Cyber Pro / VIP: bepul kiradi
- Free: kira olmaydi

Xavfsizlik: terminal simulyatori xavfsiz — real tizimga ulanmaydi, faqat
oldindan belgilangan buyruqlarga javob beradi. "Xavfli" deb belgilangan
buyruq kiritilsa, admin'ga signal yuboriladi (foydalanuvchi ID'si bilan).
Admin "Bloklash" tugmasini bossa: foydalanuvchi Hacker Lab'dan bloklanadi,
email orqali xabar boradi, va 10,000,000 CODE jarima yoziladi.
"""
from db import query_one, query_all, execute, log_action
from pricing import get_price


# =================================================================
# ROZILIK (CONSENT)
# =================================================================

def has_consented(user_id: int) -> bool:
    row = query_one("SELECT id FROM hacker_lab_consent WHERE user_id=?", (user_id,))
    return bool(row)


def record_consent(user_id: int, ip: str = ""):
    execute(
        "INSERT OR IGNORE INTO hacker_lab_consent (user_id, ip) VALUES (?,?)",
        (user_id, ip)
    )
    log_action(user_id, "hacker_lab_consent_given", ip=ip)


# =================================================================
# KIRISH HUQUQI (ACCESS)
# =================================================================

def has_access(user_id: int) -> bool:
    row = query_one("SELECT id FROM hacker_lab_access WHERE user_id=?", (user_id,))
    return bool(row)


def get_access_info(user_id: int):
    return query_one("SELECT * FROM hacker_lab_access WHERE user_id=?", (user_id,))


def grant_free_access_if_eligible(user_id: int):
    """Cyber Pro / VIP foydalanuvchiga avtomatik bepul kirish huquqi beradi."""
    user = query_one("SELECT plan FROM users WHERE id=?", (user_id,))
    if not user or user["plan"] not in ("cyber_pro", "vip"):
        return False
    if has_access(user_id):
        return True
    execute(
        "INSERT INTO hacker_lab_access (user_id, granted_via, paid_amount) VALUES (?,?,0)",
        (user_id, "plan")
    )
    return True


def purchase_access(user_id: int) -> tuple[bool, str]:
    """Pro foydalanuvchi 100,000 CODE to'lab Hacker Lab kirish huquqini sotib oladi."""
    user = query_one("SELECT plan FROM users WHERE id=?", (user_id,))
    if not user:
        return False, "Foydalanuvchi topilmadi."
    if user["plan"] in ("cyber_pro", "vip"):
        grant_free_access_if_eligible(user_id)
        return True, "Sizning planingiz uchun Hacker Lab bepul ochiq."
    if user["plan"] != "pro":
        return False, "Hacker Lab faqat Pro, Cyber Pro va SHATS CYBER PRO foydalanuvchilar uchun."
    if has_access(user_id):
        return False, "Sizda allaqachon kirish huquqi bor."

    from coins import spend_coins, _treasury_fund_in
    cost = get_price("hacker_lab_pro_price")
    ok, msg = spend_coins(user_id, cost, "hacker_lab_access")
    if not ok:
        return False, msg
    _treasury_fund_in(cost, "hacker_lab_access", user_id)
    execute(
        "INSERT INTO hacker_lab_access (user_id, granted_via, paid_amount) VALUES (?,?,?)",
        (user_id, "paid", cost)
    )
    log_action(user_id, "hacker_lab_access_purchased", details=f"cost:{cost}")
    return True, f"Hacker Lab ochildi! {cost:,} CODE to'landi."


# =================================================================
# BLOK HOLATI
# =================================================================

def is_blocked(user_id: int) -> bool:
    row = query_one("SELECT hacker_lab_blocked FROM users WHERE id=?", (user_id,))
    return bool(row and row["hacker_lab_blocked"])


def can_enter(user_id: int) -> tuple[bool, str]:
    """Foydalanuvchi Hacker Lab'ga kira oladimi — barcha shartlarni tekshiradi."""
    if is_blocked(user_id):
        return False, "Siz xavfsizlik qoidalarini buzganingiz uchun Hacker Lab'dan bloklangansiz."
    if not has_consented(user_id):
        return False, "consent_required"
    grant_free_access_if_eligible(user_id)
    if not has_access(user_id):
        return False, "access_required"
    return True, "OK"


# =================================================================
# XAVFSIZLIK MONITORINGI — "xavfli" buyruqlar
# =================================================================

# Bu so'zlar/naqshlar terminalga kiritilsa "xavfli urinish" deb hisoblanadi.
# E'tibor bering: bu faqat MONITORING uchun — buyruqning o'zi hech qachon
# bajarilmaydi (sandbox to'liq statik), shuning uchun real zarar yo'q,
# lekin niyatni kuzatish uchun foydali signal.
DANGEROUS_PATTERNS = [
    "rm -rf /", "rm -rf /*", ":(){ :|:& };:", "dd if=/dev/zero of=/dev/sda",
    "mkfs.", "> /dev/sda", "chmod -r 777 /", "wget http", "curl http",
    "nc -e", "/bin/sh -i", "/bin/bash -i", "exec(", "eval(",
    "drop database", "drop table", "; drop ", "shutdown -h now",
    "format c:", "del /f /s /q",
]


def check_command_safety(command: str) -> bool:
    """True qaytaradi agar buyruq xavfli deb belgilangan bo'lsa."""
    cmd_lower = command.lower().strip()
    return any(pattern in cmd_lower for pattern in DANGEROUS_PATTERNS)


def report_dangerous_command(user_id: int, command: str, direction_id: int = None):
    """Xavfli buyruq aniqlanganda admin uchun signal yaratadi."""
    user = query_one("SELECT custom_id FROM users WHERE id=?", (user_id,))
    cid = user["custom_id"] if user else ""
    event_id = execute(
        """INSERT INTO hacker_lab_security_events
           (user_id, custom_id, command, direction_id, status)
           VALUES (?,?,?,?,'pending')""",
        (user_id, cid, command[:500], direction_id)
    )
    # Adminlarga sayt-ichi bildirishnoma
    admins = query_all("SELECT id FROM users WHERE role IN ('admin','super_admin')")
    for a in admins:
        execute(
            "INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
            (a["id"], "⚠️ Hacker Lab: xavfli urinish",
             f"Foydalanuvchi #{cid} xavfli buyruq kiritdi: {command[:80]}", "error")
        )
        try:
            import webpush_mod
            webpush_mod.send_push_to_user(
                a["id"], "⚠️ Hacker Lab xavfsizlik signali",
                f"ID #{cid}: {command[:60]}", "/admin/hacker-lab-security"
            )
        except Exception:
            pass
    log_action(user_id, "hacker_lab_dangerous_command", details=command[:200])
    return event_id


def get_pending_security_events():
    return query_all(
        """SELECT e.*, u.ism, u.familiya, u.email, d.name_uz as direction_name
           FROM hacker_lab_security_events e
           JOIN users u ON u.id = e.user_id
           LEFT JOIN directions d ON d.id = e.direction_id
           WHERE e.status='pending'
           ORDER BY e.id DESC"""
    )


def get_all_security_events(limit: int = 100):
    return query_all(
        """SELECT e.*, u.ism, u.familiya, u.email, d.name_uz as direction_name
           FROM hacker_lab_security_events e
           JOIN users u ON u.id = e.user_id
           LEFT JOIN directions d ON d.id = e.direction_id
           ORDER BY e.id DESC LIMIT ?""",
        (limit,)
    )


def dismiss_event(event_id: int, admin_id: int):
    """Admin: bu signal yolg'on signal yoki muammo emas deb belgilaydi."""
    execute(
        "UPDATE hacker_lab_security_events SET status='dismissed', reviewed_by=?, reviewed_at=datetime('now') WHERE id=?",
        (admin_id, event_id)
    )


def block_user_for_violation(event_id: int, admin_id: int) -> tuple[bool, str]:
    """
    Admin "Bloklash" tugmasini bosganda:
    - Foydalanuvchi Hacker Lab'dan bloklanadi (butun hisob emas)
    - 10,000,000 CODE jarima yoziladi (mavjud balansdan, hatto manfiy bo'lsa ham)
    - Email orqali xabar yuboriladi (agar email yuborish sozlangan bo'lsa)
    - Saytda ham bildirishnoma
    """
    event = query_one("SELECT * FROM hacker_lab_security_events WHERE id=?", (event_id,))
    if not event:
        return False, "Voqea topilmadi."
    user_id = event["user_id"]
    user = query_one("SELECT id, email, custom_id, code_balance FROM users WHERE id=?", (user_id,))
    if not user:
        return False, "Foydalanuvchi topilmadi."

    fine = get_price("hacker_lab_violation_fine")

    # Blok qo'yish
    execute("UPDATE users SET hacker_lab_blocked=1 WHERE id=?", (user_id,))

    # Jarima — balansdan ayiramiz (manfiy bo'lishi ham mumkin, bu qasddan: og'ir jarima)
    execute("UPDATE users SET code_balance = code_balance - ? WHERE id=?", (fine, user_id))
    execute(
        "INSERT INTO code_transactions (user_id, amount, reason, ref_id) VALUES (?,?,?,?)",
        (user_id, -fine, "hacker_lab_violation_fine", event_id)
    )

    # Voqeani yopish
    execute(
        "UPDATE hacker_lab_security_events SET status='blocked', reviewed_by=?, reviewed_at=datetime('now') WHERE id=?",
        (admin_id, event_id)
    )

    # Bildirishnoma (sayt + push)
    execute(
        "INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
        (user_id, "Hacker Lab — bloklandingiz",
         f"Xavfsizlik qoidalarini buzganingiz uchun Hacker Lab'dan bloklandingiz. "
         f"Hisobingizdan {fine:,} CODE jarima yozildi.", "error")
    )
    try:
        import webpush_mod
        webpush_mod.send_push_to_user(
            user_id, "Hacker Lab — bloklandingiz",
            f"Xavfsizlik qoidasi buzilgani uchun {fine:,} CODE jarima yozildi.", "/hacker-lab"
        )
    except Exception:
        pass

    # Email yuborish (agar SMTP sozlangan bo'lsa — utils.py'dagi funksiyadan foydalanamiz)
    email_sent = False
    try:
        from utils import send_email
        email_sent = send_email(
            user["email"],
            "CYBER SHATS — Hacker Lab xavfsizlik buzilishi",
            f"Hurmatli foydalanuvchi (ID #{user['custom_id']}),\n\n"
            f"Siz Hacker Lab xavfsizlik qoidalarini buzganingiz aniqlandi.\n"
            f"Natijada:\n"
            f"- Hacker Lab'ga kirish huquqingiz bekor qilindi\n"
            f"- Hisobingizdan {fine:,} CODE jarima yozildi\n\n"
            f"Savollar bo'lsa, administratsiya bilan bog'laning.\n\nCYBER SHATS"
        )
    except Exception:
        pass

    log_action(admin_id, "hacker_lab_user_blocked",
               details=f"user:{user_id},fine:{fine},email_sent:{email_sent}")
    return True, f"Foydalanuvchi bloklandi, {fine:,} CODE jarima yozildi" + (", email yuborildi." if email_sent else " (email yuborilmadi — SMTP sozlanmagan).")


def unblock_user(user_id: int, admin_id: int):
    """Admin foydalanuvchini Hacker Lab blokidan chiqarishi mumkin."""
    execute("UPDATE users SET hacker_lab_blocked=0 WHERE id=?", (user_id,))
    execute(
        "INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
        (user_id, "Hacker Lab — blok bekor qilindi",
         "Hacker Lab'ga kirish huquqingiz tiklandi.", "success")
    )
    log_action(admin_id, "hacker_lab_user_unblocked", details=f"user:{user_id}")


# =================================================================
# JAMOA BO'LIB ISHLASH — yo'nalish ichidagi fikr almashish
# (soddalashtirilgan, to'liq ijtimoiy tarmoq keyingi bosqichda)
# =================================================================

def get_direction_posts(direction_id: int, limit: int = 50):
    return query_all(
        """SELECT p.*, u.ism, u.familiya, u.avatar, u.plan,
                  (SELECT COUNT(*) FROM hacker_lab_post_replies r WHERE r.post_id = p.id) as replies_count
           FROM hacker_lab_posts p
           JOIN users u ON u.id = p.user_id
           WHERE p.direction_id = ?
           ORDER BY p.id DESC LIMIT ?""",
        (direction_id, limit)
    )


def get_post(post_id: int):
    return query_one(
        """SELECT p.*, u.ism, u.familiya, u.avatar, u.plan
           FROM hacker_lab_posts p JOIN users u ON u.id = p.user_id
           WHERE p.id = ?""",
        (post_id,)
    )


def get_post_replies(post_id: int):
    return query_all(
        """SELECT r.*, u.ism, u.familiya, u.avatar
           FROM hacker_lab_post_replies r JOIN users u ON u.id = r.user_id
           WHERE r.post_id = ? ORDER BY r.id ASC""",
        (post_id,)
    )


def create_post(user_id: int, direction_id: int, title: str, body: str,
                file_path: str = None, file_type: str = None) -> tuple[bool, str]:
    title = (title or "").strip()
    if not title:
        return False, "Sarlavha majburiy."
    execute(
        """INSERT INTO hacker_lab_posts (direction_id, user_id, title, body, file_path, file_type)
           VALUES (?,?,?,?,?,?)""",
        (direction_id, user_id, title, (body or "").strip(), file_path, file_type)
    )
    return True, "Post yaratildi."


def create_reply(user_id: int, post_id: int, body: str) -> tuple[bool, str]:
    body = (body or "").strip()
    if not body:
        return False, "Javob matni bo'sh bo'lishi mumkin emas."
    execute(
        "INSERT INTO hacker_lab_post_replies (post_id, user_id, body) VALUES (?,?,?)",
        (post_id, user_id, body)
    )
    return True, "Javob qo'shildi."
