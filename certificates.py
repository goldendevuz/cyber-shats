"""
CYBER SHATS V1.3 — Sertifikat tizimi moduli

Sertifikat olish jarayoni:
1. Foydalanuvchi yo'nalishdagi BARCHA kurslarni bitirgan bo'lishi kerak
2. Sertifikat imtihoni uchun 5,000 CODE to'laydi (g'aznaga tushadi)
3. 50 ta test (15 daqiqa) + 15 ta amaliy (30 daqiqa) topshiradi
4. 60%+ ball olsa o'tdi deb hisoblanadi
5. O'tgan foydalanuvchi sertifikat arizasini yuboradi (ID, yo'nalish, ball avtomatik)
6. Ariza admin va g'aznachiga ko'rinadi, admin tasdiqlaydi

Eslatma: Sertifikat faqat IT yo'nalishlar bitirgalarga beriladi
        (Cyber Pro yo'nalishlari - til/matematika/office - hozircha sertifikatsiz).
"""
from db import query_one, query_all, execute, log_action
from coins import spend_coins, _treasury_fund_in
from pricing import get_price


# Faqat shu yo'nalishlar sertifikatga ega bo'ladi (IT-related)
IT_DIRECTION_SLUGS = ["cyber-security", "dasturlash", "smm", "tarmoq", "etika-hacking",
                       "pentesting", "web-dev", "mobile-dev", "ai-ml", "devops"]


def is_it_direction(direction_slug: str) -> bool:
    """Faqat IT yo'nalishlar uchun sertifikat berish mumkin."""
    return direction_slug in IT_DIRECTION_SLUGS or "cyber" in direction_slug.lower() or "dastur" in direction_slug.lower()


def get_user_direction_progress(user_id: int, direction_id: int) -> dict:
    """Foydalanuvchining yo'nalishdagi barcha kurslar bo'yicha progressi."""
    courses = query_all(
        "SELECT id, title FROM courses WHERE direction_id=? AND is_active=1",
        (direction_id,)
    )
    if not courses:
        return {"total_courses": 0, "completed": 0, "all_done": False, "courses": []}
    completed = 0
    course_status = []
    for course in courses:
        enr = query_one(
            "SELECT progress_percent FROM enrollments WHERE user_id=? AND course_id=?",
            (user_id, course["id"])
        )
        progress = enr["progress_percent"] if enr else 0
        if progress >= 100:
            completed += 1
        course_status.append({
            "id": course["id"],
            "title": course["title"],
            "progress": progress,
            "done": progress >= 100,
        })
    return {
        "total_courses": len(courses),
        "completed": completed,
        "all_done": completed == len(courses),
        "courses": course_status,
    }


def can_apply_for_certificate(user_id: int, direction_id: int) -> tuple[bool, str]:
    """Sertifikat olish uchun shartlar bajarilganmi?"""
    direction = query_one("SELECT slug, name_uz FROM directions WHERE id=?", (direction_id,))
    if not direction:
        return False, "Yo'nalish topilmadi."

    if not is_it_direction(direction["slug"]):
        return False, f"Sertifikat faqat IT yo'nalishlari uchun beriladi. {direction['name_uz']} sertifikatsiz."

    progress = get_user_direction_progress(user_id, direction_id)
    if not progress["all_done"]:
        return False, f"Avval yo'nalishdagi barcha kurslarni bitiring ({progress['completed']}/{progress['total_courses']})."

    # Ariza allaqachon yuborilganmi
    existing = query_one(
        "SELECT id, status FROM certificate_applications WHERE user_id=? AND direction_id=? AND status IN ('pending','approved','issued') ORDER BY id DESC LIMIT 1",
        (user_id, direction_id)
    )
    if existing:
        return False, f"Bu yo'nalish bo'yicha arizangiz allaqachon mavjud (status: {existing['status']})."

    return True, "Sertifikat imtihoniga tayyor."


def pay_for_certificate_exam(user_id: int, direction_id: int) -> tuple[bool, str]:
    """Sertifikat imtihoni uchun to'lov. G'azna jamg'armasiga tushadi."""
    can, msg = can_apply_for_certificate(user_id, direction_id)
    if not can:
        return False, msg

    # Allaqachon to'langanmi
    paid = query_one(
        "SELECT id FROM code_transactions WHERE user_id=? AND reason='certificate_exam' AND ref_id=?",
        (user_id, direction_id)
    )
    if paid:
        return True, "To'lov allaqachon amalga oshirilgan. Imtihonni boshlashingiz mumkin."

    fee = get_price("certificate_exam_fee")
    ok, msg = spend_coins(user_id, fee, "certificate_exam", ref_id=direction_id)
    if not ok:
        return False, msg
    _treasury_fund_in(fee, "certificate_fee", user_id)
    log_action(user_id, "certificate_exam_paid", details=f"dir:{direction_id},amount:{fee}")
    return True, f"To'lov muvaffaqiyatli ({fee:,} CODE). Imtihonni boshlashingiz mumkin."


def has_paid_for_exam(user_id: int, direction_id: int) -> bool:
    paid = query_one(
        "SELECT id FROM code_transactions WHERE user_id=? AND reason='certificate_exam' AND ref_id=?",
        (user_id, direction_id)
    )
    return bool(paid)


def submit_exam_results(user_id: int, direction_id: int,
                        test_score: int, test_total: int,
                        practice_score: int, practice_total: int) -> tuple[bool, str, int]:
    """Imtihon yakuni — ball saqlanadi va passed/failed aniqlanadi.
    Returns (passed, message, attempt_id)"""
    total = test_score + practice_score
    max_total = test_total + practice_total
    passed = (total * 100 / max_total) >= 60 if max_total > 0 else False
    fee = get_price("certificate_exam_fee")
    attempt_id = execute(
        """INSERT INTO direction_exam_attempts
           (user_id, direction_id, test_score, test_total, practice_score, practice_total,
            total_score, max_total, passed, paid_amount, finished_at)
           VALUES (?,?,?,?,?,?,?,?,?,?, datetime('now'))""",
        (user_id, direction_id, test_score, test_total, practice_score, practice_total,
         total, max_total, 1 if passed else 0, fee)
    )
    log_action(user_id, "certificate_exam_finished",
               details=f"dir:{direction_id},score:{total}/{max_total},passed:{passed}")
    return passed, "Imtihon yakunlandi.", attempt_id


def create_certificate_application(user_id: int, direction_id: int, attempt_id: int) -> tuple[bool, str]:
    """O'tgan imtihondan keyin sertifikat arizasi yaratish."""
    attempt = query_one("SELECT * FROM direction_exam_attempts WHERE id=? AND user_id=?",
                        (attempt_id, user_id))
    if not attempt:
        return False, "Imtihon urinishi topilmadi."
    if not attempt["passed"]:
        return False, "Sertifikat olish uchun imtihondan o'tishingiz kerak (60%+)."

    existing = query_one(
        "SELECT id FROM certificate_applications WHERE user_id=? AND direction_id=? AND status IN ('pending','approved','issued')",
        (user_id, direction_id)
    )
    if existing:
        return False, "Bu yo'nalish bo'yicha arizangiz allaqachon mavjud."

    user = query_one("SELECT custom_id FROM users WHERE id=?", (user_id,))
    cid = user["custom_id"] if user else ""

    execute(
        """INSERT INTO certificate_applications
           (user_id, direction_id, custom_id, exam_score, exam_total, paid_amount, status)
           VALUES (?,?,?,?,?,?, 'pending')""",
        (user_id, direction_id, cid, attempt["total_score"], attempt["max_total"], attempt["paid_amount"])
    )
    log_action(user_id, "certificate_application_submitted", details=f"dir:{direction_id}")
    return True, "Sertifikat arizasi yuborildi. Admin tasdiqlashini kuting."


def get_user_applications(user_id: int):
    return query_all(
        """SELECT ca.*, d.name_uz as direction_name, d.slug as direction_slug
           FROM certificate_applications ca
           JOIN directions d ON d.id = ca.direction_id
           WHERE ca.user_id = ?
           ORDER BY ca.id DESC""",
        (user_id,)
    )


def get_all_applications(status: str = None):
    """Admin uchun barcha arizalar."""
    if status:
        return query_all(
            """SELECT ca.*, d.name_uz as direction_name, u.ism, u.familiya, u.email
               FROM certificate_applications ca
               JOIN directions d ON d.id = ca.direction_id
               JOIN users u ON u.id = ca.user_id
               WHERE ca.status = ? ORDER BY ca.id DESC""",
            (status,)
        )
    return query_all(
        """SELECT ca.*, d.name_uz as direction_name, u.ism, u.familiya, u.email
           FROM certificate_applications ca
           JOIN directions d ON d.id = ca.direction_id
           JOIN users u ON u.id = ca.user_id
           ORDER BY ca.id DESC"""
    )


def review_application(app_id: int, reviewer_id: int, decision: str, note: str = "") -> tuple[bool, str]:
    """Admin arizani tasdiqlaydi yoki rad etadi. decision: 'approved' / 'rejected'"""
    if decision not in ("approved", "rejected"):
        return False, "Noto'g'ri qaror."
    app_row = query_one("SELECT * FROM certificate_applications WHERE id=?", (app_id,))
    if not app_row:
        return False, "Ariza topilmadi."
    if app_row["status"] != "pending":
        return False, f"Bu ariza allaqachon ko'rib chiqilgan (holat: {app_row['status']})."

    if decision == "approved":
        # Sertifikat raqami yaratish: CS-YYYY-NNNNNN
        import datetime, random
        cert_number = f"CS-{datetime.datetime.now().year}-{random.randint(100000, 999999)}"
        execute(
            """UPDATE certificate_applications
               SET status='issued', admin_note=?, reviewed_at=datetime('now'),
                   reviewed_by=?, certificate_number=?
               WHERE id=?""",
            (note, reviewer_id, cert_number, app_id)
        )
        execute(
            "INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
            (app_row["user_id"], "Sertifikat berildi!",
             f"Sertifikat raqami: {cert_number}. Tabriklaymiz!", "success")
        )
        try:
            import webpush_mod
            webpush_mod.send_push_to_user(
                app_row["user_id"], "Sertifikat berildi! 🎓",
                f"Sertifikat raqami: {cert_number}. Tabriklaymiz!", "/certificates"
            )
        except Exception:
            pass
        log_action(reviewer_id, "cert_app_approved", details=f"app:{app_id},cert:{cert_number}")
        return True, f"Tasdiqlandi. Sertifikat raqami: {cert_number}"
    else:
        execute(
            "UPDATE certificate_applications SET status='rejected', admin_note=?, reviewed_at=datetime('now'), reviewed_by=? WHERE id=?",
            (note, reviewer_id, app_id)
        )
        execute(
            "INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
            (app_row["user_id"], "Sertifikat arizasi rad etildi",
             f"Sabab: {note or 'Malumotlar yetarli emas'}", "error")
        )
        try:
            import webpush_mod
            webpush_mod.send_push_to_user(
                app_row["user_id"], "Sertifikat arizasi rad etildi",
                f"Sabab: {note or 'Malumotlar yetarli emas'}", "/certificates"
            )
        except Exception:
            pass
        log_action(reviewer_id, "cert_app_rejected", details=f"app:{app_id}")
        return True, "Ariza rad etildi."
