# ============================================================
# CYBER SHATS — Flask asosiy ilova fayli
# Barcha route'lar shu yerda joylashgan.
# ============================================================
import os
import random
import string
import datetime

from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, abort, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

from config import Config
from db import get_db, close_db, query_one, query_all, execute, log_action
from auth import login_required, admin_required, get_current_user, api_login_required
from utils import api_response, time_ago_uz, fmt_duration
from ai import call_ai_assistant, is_ai_configured

app = Flask(__name__)
app.config.from_object(Config)
app.teardown_appcontext(close_db)
app.jinja_env.globals.update(zip=zip)


# ---------------------------------------------------------------
# CONTEXT PROCESSOR — barcha shablonlarga umumiy ma'lumot yuboradi
# ---------------------------------------------------------------
@app.context_processor
def inject_globals():
    user = get_current_user()
    try:
        total_users = query_one("SELECT COUNT(*) c FROM users")["c"]
    except Exception:
        total_users = 0
    online_now = random.randint(140, 480)
    today_new = random.randint(8, 40)
    notif_count = 0
    if user:
        try:
            notif_count = query_one("SELECT COUNT(*) c FROM notifications WHERE user_id=? AND is_read=0", (user["id"],))["c"]
        except Exception:
            notif_count = 0
    build_date = datetime.date(2026, 1, 1)
    uptime_days = (datetime.date.today() - build_date).days
    return dict(
        current_user=user,
        site_name=Config.SITE_NAME,
        site_domain=Config.SITE_DOMAIN,
        hud_online=online_now,
        hud_today=today_new,
        hud_total=total_users,
        hud_version="v2.6.1",
        hud_ip=request.remote_addr or "10.0.0.1",
        uptime_days=uptime_days,
        notif_count=notif_count,
        ai_configured=is_ai_configured(),
        now=datetime.datetime.now(),
        time_ago_uz=time_ago_uz,
        fmt_duration=fmt_duration,
    )


# ---------------------------------------------------------------
# YORDAMCHI FUNKSIYALAR
# ---------------------------------------------------------------
def gen_code(n=8):
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=n))


def get_directions():
    return query_all("SELECT * FROM directions ORDER BY sort_order")


def award_xp(user_id, amount):
    execute("UPDATE users SET xp = xp + ? WHERE id=?", (amount, user_id))
    user = query_one("SELECT xp FROM users WHERE id=?", (user_id,))
    new_level = max(1, user["xp"] // 500 + 1)
    execute("UPDATE users SET level=? WHERE id=?", (new_level, user_id))


def generate_certificate_pdf(cert):
    """Sertifikat uchun haqiqiy PDF fayl yaratadi (reportlab + QR kod)."""
    import qrcode
    import io
    from reportlab.lib.pagesizes import landscape, A4
    from reportlab.lib.units import mm
    from reportlab.lib.colors import HexColor
    from reportlab.pdfgen import canvas as pdf_canvas
    from reportlab.lib.utils import ImageReader

    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "generated")
    os.makedirs(out_dir, exist_ok=True)
    pdf_path = os.path.join(out_dir, f"cert_{cert['cert_code']}.pdf")

    green = HexColor("#00ff41")
    bg = HexColor("#000010")
    muted = HexColor("#00cc99")

    c = pdf_canvas.Canvas(pdf_path, pagesize=landscape(A4))
    w, h = landscape(A4)
    c.setFillColor(bg)
    c.rect(0, 0, w, h, fill=1, stroke=0)
    c.setStrokeColor(green)
    c.setLineWidth(2)
    c.rect(14 * mm, 14 * mm, w - 28 * mm, h - 28 * mm, fill=0, stroke=1)
    c.setLineWidth(0.6)
    c.rect(20 * mm, 20 * mm, w - 40 * mm, h - 40 * mm, fill=0, stroke=1)

    c.setFillColor(green)
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(w / 2, h - 38 * mm, "C Y B E R   S H A T S")

    c.setFont("Helvetica-Bold", 30)
    c.drawCentredString(w / 2, h - 60 * mm, "SERTIFIKAT")

    c.setFillColor(HexColor("#e0ffe8"))
    c.setFont("Helvetica", 12)
    c.drawCentredString(w / 2, h - 78 * mm, "Mazkur sertifikat quyidagi shaxsga taqdim etiladi:")

    c.setFillColor(green)
    c.setFont("Helvetica-Bold", 22)
    full_name = f"{cert['ism']} {cert['familiya']}".strip()
    c.drawCentredString(w / 2, h - 92 * mm, full_name)

    c.setFillColor(HexColor("#00ccff"))
    c.setFont("Helvetica", 14)
    c.drawCentredString(w / 2, h - 106 * mm, f"« {cert['course_title']} »")

    c.setFillColor(muted)
    c.setFont("Helvetica", 10)
    c.drawCentredString(w / 2, h - 116 * mm,
                         f"kursini muvaffaqiyatli yakunlagani uchun ({cert['duration_weeks']} haftalik dastur)")

    qr_img = qrcode.make(f"https://{Config.SITE_DOMAIN}/certificate/{cert['cert_code']}")
    buf = io.BytesIO()
    qr_img.save(buf, format="PNG")
    buf.seek(0)
    qr_reader = ImageReader(buf)
    qr_size = 28 * mm
    c.drawImage(qr_reader, w - 50 * mm, 26 * mm, qr_size, qr_size)

    c.setFillColor(muted)
    c.setFont("Helvetica", 9)
    c.drawString(26 * mm, 34 * mm, f"Sertifikat kodi: {cert['cert_code']}")
    c.drawString(26 * mm, 29 * mm, f"Berilgan sana: {str(cert['issued_at'])[:10]}")
    c.drawString(26 * mm, 24 * mm, f"https://{Config.SITE_DOMAIN}")

    c.showPage()
    c.save()
    return pdf_path


# =================================================================
# OMMAVIY (PUBLIC) SAHIFALAR
# =================================================================
@app.route("/")
def index():
    directions = get_directions()
    courses = query_all(
        "SELECT c.*, d.name_uz as direction_name, d.slug as direction_slug FROM courses c "
        "JOIN directions d ON d.id=c.direction_id ORDER BY c.students_count DESC LIMIT 6"
    )
    news = query_all("SELECT * FROM news ORDER BY published_at DESC LIMIT 4")
    total_students = query_one("SELECT COUNT(*) c FROM users WHERE role='student'")["c"]
    total_courses = query_one("SELECT COUNT(*) c FROM courses")["c"]
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    return render_template("index.html", directions=directions, courses=courses, news=news,
                            total_students=total_students, total_courses=total_courses)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = query_one("SELECT * FROM users WHERE email=?", (email,))
        if user and check_password_hash(user["password_hash"], password):
            if user["is_blocked"]:
                flash("Hisobingiz administrator tomonidan bloklangan.", "error")
                return redirect(url_for("login"))
            session.clear()
            session["user_id"] = user["id"]
            session.permanent = True
            log_action(user["id"], "login", ip=request.remote_addr)
            flash(f"Xush kelibsiz, {user['ism']}!", "success")
            nxt = request.args.get("next")
            return redirect(nxt or url_for("dashboard"))
        flash("Email yoki parol noto'g'ri.", "error")
        return redirect(url_for("login"))
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        ism = request.form.get("ism", "").strip()
        familiya = request.form.get("familiya", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not ism or not email or len(password) < 6:
            flash("Iltimos, barcha maydonlarni to'g'ri to'ldiring (parol kamida 6 belgi).", "error")
            return redirect(url_for("register"))
        existing = query_one("SELECT id FROM users WHERE email=?", (email,))
        if existing:
            flash("Bu email bilan foydalanuvchi allaqachon mavjud.", "error")
            return redirect(url_for("register"))
        uid = execute(
            "INSERT INTO users (ism, familiya, email, password_hash, role) VALUES (?,?,?,?,?)",
            (ism, familiya, email, generate_password_hash(password), "student"),
        )
        execute("INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
                (uid, "Xush kelibsiz!", "CYBER SHATS platformasiga muvaffaqiyatli ro'yxatdan o'tdingiz.", "success"))
        session.clear()
        session["user_id"] = uid
        log_action(uid, "register", ip=request.remote_addr)
        flash("Ro'yxatdan o'tish muvaffaqiyatli! Xush kelibsiz.", "success")
        return redirect(url_for("dashboard"))
    return render_template("register.html")


@app.route("/logout")
def logout():
    if session.get("user_id"):
        log_action(session["user_id"], "logout", ip=request.remote_addr)
    session.clear()
    flash("Tizimdan muvaffaqiyatli chiqdingiz.", "info")
    return redirect(url_for("index"))


@app.route("/pricing")
def pricing():
    return render_template("pricing.html")


@app.route("/robots.txt")
def robots_txt():
    content = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /admin\n"
        "Disallow: /api/\n"
        "Disallow: /dashboard\n"
        "Disallow: /profile\n"
        f"Sitemap: https://{Config.SITE_DOMAIN}/sitemap.xml\n"
    )
    return content, 200, {"Content-Type": "text/plain"}


@app.route("/sitemap.xml")
def sitemap_xml():
    courses = query_all("SELECT slug FROM courses WHERE is_active=1")
    urls = ["/", "/login", "/register", "/pricing", "/courses", "/news", "/library", "/forum"]
    xml = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        xml.append(f"<url><loc>https://{Config.SITE_DOMAIN}{u}</loc></url>")
    for c in courses:
        xml.append(f"<url><loc>https://{Config.SITE_DOMAIN}/courses/{c['slug']}</loc></url>")
    xml.append("</urlset>")
    return "\n".join(xml), 200, {"Content-Type": "application/xml"}


# =================================================================
# DASHBOARD (asosiy interfeys — orbit hub)
# =================================================================
@app.route("/dashboard")
@login_required
def dashboard():
    user = get_current_user()
    directions = get_directions()
    enrollments = query_all(
        "SELECT e.*, c.title, c.slug, c.icon, c.lessons_count FROM enrollments e "
        "JOIN courses c ON c.id=e.course_id WHERE e.user_id=? ORDER BY e.started_at DESC LIMIT 4",
        (user["id"],),
    )
    notif_count = query_one("SELECT COUNT(*) c FROM notifications WHERE user_id=? AND is_read=0", (user["id"],))["c"]
    recent_news = query_all("SELECT * FROM news ORDER BY published_at DESC LIMIT 3")
    return render_template("dashboard.html", directions=directions, enrollments=enrollments,
                            notif_count=notif_count, recent_news=recent_news)


@app.route("/directions")
@login_required
def directions():
    return render_template("directions.html", directions=get_directions())


# =================================================================
# KURSLAR
# =================================================================
@app.route("/courses")
@login_required
def courses():
    d_slug = request.args.get("d", "")
    search = request.args.get("q", "").strip()
    level = request.args.get("level", "")
    sql = ("SELECT c.*, d.name_uz as direction_name, d.slug as direction_slug FROM courses c "
           "JOIN directions d ON d.id=c.direction_id WHERE c.is_active=1")
    args = []
    if d_slug:
        sql += " AND d.slug=?"
        args.append(d_slug)
    if search:
        sql += " AND c.title LIKE ?"
        args.append(f"%{search}%")
    if level:
        sql += " AND c.level=?"
        args.append(level)
    sql += " ORDER BY c.students_count DESC LIMIT 60"
    course_list = query_all(sql, tuple(args))
    return render_template("courses.html", courses=course_list, directions=get_directions(),
                            active_d=d_slug, search=search, active_level=level)


@app.route("/courses/<slug>")
@login_required
def course_detail(slug):
    course = query_one(
        "SELECT c.*, d.name_uz as direction_name, d.slug as direction_slug FROM courses c "
        "JOIN directions d ON d.id=c.direction_id WHERE c.slug=?", (slug,)
    )
    if not course:
        abort(404)
    modules = query_all("SELECT * FROM modules WHERE course_id=? ORDER BY order_num", (course["id"],))
    for m in modules:
        m["lessons"] = query_all("SELECT * FROM lessons WHERE module_id=? ORDER BY order_num", (m["id"],))
    user = get_current_user()
    enrollment = query_one("SELECT * FROM enrollments WHERE user_id=? AND course_id=?", (user["id"], course["id"]))
    test = query_one("SELECT * FROM tests WHERE course_id=?", (course["id"],))
    return render_template("course_detail.html", course=course, modules=modules, enrollment=enrollment, test=test)


@app.route("/courses/<slug>/enroll", methods=["POST"])
@login_required
def enroll_course(slug):
    user = get_current_user()
    course = query_one("SELECT * FROM courses WHERE slug=?", (slug,))
    if not course:
        abort(404)
    existing = query_one("SELECT id FROM enrollments WHERE user_id=? AND course_id=?", (user["id"], course["id"]))
    if not existing:
        execute("INSERT INTO enrollments (user_id, course_id, progress_percent) VALUES (?,?,0)",
                (user["id"], course["id"]))
        execute("UPDATE courses SET students_count = students_count + 1 WHERE id=?", (course["id"],))
        log_action(user["id"], "enroll", details=course["title"], ip=request.remote_addr)
        flash(f"«{course['title']}» kursiga muvaffaqiyatli yozildingiz!", "success")
    first_lesson = query_one("SELECT id FROM lessons WHERE course_id=? ORDER BY order_num LIMIT 1", (course["id"],))
    if first_lesson:
        return redirect(url_for("lesson", slug=slug, lesson_id=first_lesson["id"]))
    return redirect(url_for("course_detail", slug=slug))


@app.route("/courses/<slug>/lesson/<int:lesson_id>")
@login_required
def lesson(slug, lesson_id):
    course = query_one("SELECT * FROM courses WHERE slug=?", (slug,))
    if not course:
        abort(404)
    current = query_one("SELECT * FROM lessons WHERE id=? AND course_id=?", (lesson_id, course["id"]))
    if not current:
        abort(404)
    all_lessons = query_all("SELECT * FROM lessons WHERE course_id=? ORDER BY order_num", (course["id"],))
    user = get_current_user()
    done_ids = {r["lesson_id"] for r in query_all(
        "SELECT lesson_id FROM lesson_progress WHERE user_id=? AND is_done=1", (user["id"],))}
    idx = next((i for i, l in enumerate(all_lessons) if l["id"] == lesson_id), 0)
    prev_lesson = all_lessons[idx - 1] if idx > 0 else None
    next_lesson = all_lessons[idx + 1] if idx < len(all_lessons) - 1 else None
    enrollment = query_one("SELECT * FROM enrollments WHERE user_id=? AND course_id=?", (user["id"], course["id"]))
    if not enrollment:
        execute("INSERT INTO enrollments (user_id, course_id, progress_percent) VALUES (?,?,0)",
                (user["id"], course["id"]))
    return render_template("lesson.html", course=course, lesson=current, all_lessons=all_lessons,
                            done_ids=done_ids, prev_lesson=prev_lesson, next_lesson=next_lesson)


@app.route("/courses/<slug>/lesson/<int:lesson_id>/materials")
@login_required
def lesson_materials(slug, lesson_id):
    course = query_one("SELECT * FROM courses WHERE slug=?", (slug,))
    current = query_one("SELECT * FROM lessons WHERE id=? AND course_id=?", (lesson_id, course["id"])) if course else None
    if not course or not current:
        abort(404)
    return render_template("lesson_materials.html", course=course, lesson=current)


@app.route("/courses/<slug>/lesson/<int:lesson_id>/complete", methods=["POST"])
@login_required
def complete_lesson(slug, lesson_id):
    user = get_current_user()
    course = query_one("SELECT * FROM courses WHERE slug=?", (slug,))
    if not course:
        return api_response(False, error="Kurs topilmadi", status=404)
    execute("INSERT OR IGNORE INTO lesson_progress (user_id, lesson_id, is_done) VALUES (?,?,1)",
            (user["id"], lesson_id))
    execute("UPDATE lesson_progress SET is_done=1 WHERE user_id=? AND lesson_id=?", (user["id"], lesson_id))
    total = query_one("SELECT COUNT(*) c FROM lessons WHERE course_id=?", (course["id"],))["c"]
    done = query_one(
        "SELECT COUNT(*) c FROM lesson_progress lp JOIN lessons l ON l.id=lp.lesson_id "
        "WHERE lp.user_id=? AND l.course_id=? AND lp.is_done=1", (user["id"], course["id"]))["c"]
    pct = int((done / total) * 100) if total else 0
    enrollment = query_one("SELECT * FROM enrollments WHERE user_id=? AND course_id=?", (user["id"], course["id"]))
    if enrollment:
        execute("UPDATE enrollments SET progress_percent=? WHERE id=?", (pct, enrollment["id"]))
        if pct == 100 and not enrollment["completed_at"]:
            execute("UPDATE enrollments SET completed_at=? WHERE id=?", (datetime.datetime.now().isoformat(), enrollment["id"]))
            cert_code = f"CS-{gen_code(10)}"
            execute("INSERT INTO certificates (user_id, course_id, cert_code) VALUES (?,?,?)",
                    (user["id"], course["id"], cert_code))
            execute("INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
                    (user["id"], "Sertifikat tayyor!", f"«{course['title']}» kursini yakunladingiz.", "success"))
    award_xp(user["id"], 25)
    log_action(user["id"], "complete_lesson", details=f"lesson:{lesson_id}", ip=request.remote_addr)
    return api_response(True, data={"progress_percent": pct})


# =================================================================
# AMALIYOT / HACKER LAB — FAQAT VIZUAL SIMULYATSIYA (xavfsizlik uchun)
# Bu sahifalarda HAQIQIY ekspluatatsiya kodi yo'q — barcha "hujum"
# faqat oldindan yozilgan JS skript orqali frontendda ko'rsatiladi.
# =================================================================
@app.route("/courses/<slug>/practice/<int:lesson_id>")
@login_required
def practice(slug, lesson_id):
    course = query_one("SELECT * FROM courses WHERE slug=?", (slug,))
    current = query_one("SELECT * FROM lessons WHERE id=? AND course_id=?", (lesson_id, course["id"])) if course else None
    if not course or not current:
        abort(404)
    return render_template("practice.html", course=course, lesson=current)


@app.route("/hacker-lab")
@login_required
def hacker_lab():
    return render_template("hacker_lab.html")


@app.route("/tests")
@login_required
def tests():
    user = get_current_user()
    test_list = query_all(
        "SELECT t.*, c.title as course_title, c.slug as course_slug, "
        "(SELECT COUNT(*) FROM test_questions WHERE test_id=t.id) as q_count "
        "FROM tests t LEFT JOIN courses c ON c.id=t.course_id ORDER BY t.id"
    )
    attempted = {r["test_id"]: r for r in query_all(
        "SELECT test_id, MAX(score) as best_score, total FROM test_attempts WHERE user_id=? GROUP BY test_id",
        (user["id"],))}
    return render_template("tests.html", tests=test_list, attempted=attempted)


@app.route("/tests/<int:test_id>")
@login_required
def test_take(test_id):
    test = query_one("SELECT t.*, c.title as course_title FROM tests t LEFT JOIN courses c ON c.id=t.course_id WHERE t.id=?", (test_id,))
    if not test:
        abort(404)
    questions = query_all("SELECT * FROM test_questions WHERE test_id=? ORDER BY order_num", (test_id,))
    return render_template("test_take.html", test=test, questions=questions)


@app.route("/tests/<int:test_id>/submit", methods=["POST"])
@login_required
def test_submit(test_id):
    user = get_current_user()
    questions = query_all("SELECT * FROM test_questions WHERE test_id=?", (test_id,))
    score = 0
    for q in questions:
        chosen = request.form.get(f"q_{q['id']}", "")
        if chosen == q["correct_option"]:
            score += 1
    total = len(questions)
    execute("INSERT INTO test_attempts (user_id, test_id, score, total) VALUES (?,?,?,?)",
            (user["id"], test_id, score, total))
    award_xp(user["id"], score * 10)
    log_action(user["id"], "test_submit", details=f"test:{test_id} score:{score}/{total}", ip=request.remote_addr)
    flash(f"Test yakunlandi! Natija: {score}/{total}", "success" if score >= total * 0.6 else "warn")
    return redirect(url_for("results"))


# =================================================================
# NATIJALAR / PROFIL / BILDIRISHNOMALAR / SERTIFIKAT
# =================================================================
@app.route("/results")
@login_required
def results():
    user = get_current_user()
    enrollments = query_all(
        "SELECT e.*, c.title, c.slug, c.icon FROM enrollments e JOIN courses c ON c.id=e.course_id "
        "WHERE e.user_id=? ORDER BY e.started_at DESC", (user["id"],))
    avg_progress = int(sum(e["progress_percent"] for e in enrollments) / len(enrollments)) if enrollments else 0
    certificates = query_all(
        "SELECT cert.*, c.title as course_title FROM certificates cert JOIN courses c ON c.id=cert.course_id "
        "WHERE cert.user_id=? ORDER BY cert.issued_at DESC", (user["id"],))
    attempts = query_all(
        "SELECT ta.*, t.title as test_title FROM test_attempts ta JOIN tests t ON t.id=ta.test_id "
        "WHERE ta.user_id=? ORDER BY ta.completed_at DESC LIMIT 10", (user["id"],))
    badges = query_all(
        "SELECT b.* FROM user_badges ub JOIN badges b ON b.id=ub.badge_id WHERE ub.user_id=?", (user["id"],))
    return render_template("results.html", enrollments=enrollments, avg_progress=avg_progress,
                            certificates=certificates, attempts=attempts, badges=badges)


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user = get_current_user()
    if request.method == "POST":
        ism = request.form.get("ism", user["ism"]).strip()
        familiya = request.form.get("familiya", user["familiya"]).strip()
        bio = request.form.get("bio", "").strip()
        execute("UPDATE users SET ism=?, familiya=?, bio=? WHERE id=?", (ism, familiya, bio, user["id"]))
        flash("Profil ma'lumotlari yangilandi.", "success")
        return redirect(url_for("profile"))
    enrollments = query_all(
        "SELECT e.*, c.title, c.slug FROM enrollments e JOIN courses c ON c.id=e.course_id WHERE e.user_id=?",
        (user["id"],))
    badges = query_all(
        "SELECT b.* FROM user_badges ub JOIN badges b ON b.id=ub.badge_id WHERE ub.user_id=?", (user["id"],))
    return render_template("profile.html", enrollments=enrollments, badges=badges)


@app.route("/notifications")
@login_required
def notifications():
    user = get_current_user()
    items = query_all("SELECT * FROM notifications WHERE user_id=? ORDER BY created_at DESC LIMIT 40", (user["id"],))
    execute("UPDATE notifications SET is_read=1 WHERE user_id=?", (user["id"],))
    return render_template("notifications.html", items=items)


@app.route("/certificate/<cert_code>")
@login_required
def certificate(cert_code):
    cert = query_one(
        "SELECT cert.*, c.title as course_title, c.duration_weeks, u.ism, u.familiya FROM certificates cert "
        "JOIN courses c ON c.id=cert.course_id JOIN users u ON u.id=cert.user_id WHERE cert.cert_code=?",
        (cert_code,))
    if not cert:
        abort(404)
    return render_template("certificate.html", cert=cert)


@app.route("/certificate/<cert_code>/download")
@login_required
def certificate_download(cert_code):
    cert = query_one(
        "SELECT cert.*, c.title as course_title, c.duration_weeks, u.ism, u.familiya FROM certificates cert "
        "JOIN courses c ON c.id=cert.course_id JOIN users u ON u.id=cert.user_id WHERE cert.cert_code=?",
        (cert_code,))
    if not cert:
        abort(404)
    pdf_path = generate_certificate_pdf(cert)
    return send_file(pdf_path, as_attachment=True, download_name=f"sertifikat-{cert_code}.pdf")


# =================================================================
# AI YORDAMCHI
# =================================================================
AI_TYPES = [
    {"id": "umumiy", "name": "Umumiy AI", "icon": "bot"},
    {"id": "kod", "name": "Kod Yozuvchi", "icon": "code"},
    {"id": "cyber", "name": "Cyber Security", "icon": "shield"},
    {"id": "design", "name": "Design AI", "icon": "layers"},
    {"id": "cloud", "name": "Cloud AI", "icon": "cloud"},
    {"id": "tarix", "name": "Tarix AI", "icon": "book"},
]


@app.route("/ai")
@login_required
def ai_assistant():
    atype = request.args.get("type", "umumiy")
    user = get_current_user()
    history = query_all(
        "SELECT * FROM ai_messages WHERE user_id=? AND assistant_type=? ORDER BY id ASC LIMIT 50",
        (user["id"], atype))
    return render_template("ai_assistant.html", ai_types=AI_TYPES, active_type=atype, history=history)


@app.route("/api/ai/chat", methods=["POST"])
@api_login_required
def api_ai_chat():
    user = get_current_user()
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    atype = data.get("type", "umumiy")
    if not message:
        return api_response(False, error="Xabar bo'sh bo'lishi mumkin emas", status=400)

    history = query_all(
        "SELECT role, content FROM ai_messages WHERE user_id=? AND assistant_type=? ORDER BY id ASC LIMIT 20",
        (user["id"], atype))
    execute("INSERT INTO ai_messages (user_id, assistant_type, role, content) VALUES (?,?,?,?)",
            (user["id"], atype, "user", message))

    reply, is_live = call_ai_assistant(atype, message, history)

    execute("INSERT INTO ai_messages (user_id, assistant_type, role, content) VALUES (?,?,?,?)",
            (user["id"], atype, "assistant", reply))
    award_xp(user["id"], 2)
    log_action(user["id"], "ai_chat", details=f"type:{atype}", ip=request.remote_addr)
    return api_response(True, data={"reply": reply, "is_live": is_live})


# =================================================================
# FORUM
# =================================================================
@app.route("/forum")
@login_required
def forum():
    category = request.args.get("cat", "")
    sql = ("SELECT p.*, u.ism, u.familiya, u.avatar FROM forum_posts p JOIN users u ON u.id=p.user_id")
    args = ()
    if category:
        sql += " WHERE p.category=?"
        args = (category,)
    sql += " ORDER BY p.created_at DESC LIMIT 50"
    posts = query_all(sql, args)
    categories = query_all("SELECT category, COUNT(*) as c FROM forum_posts GROUP BY category")
    return render_template("forum.html", posts=posts, categories=categories, active_cat=category)


@app.route("/forum/new", methods=["POST"])
@login_required
def forum_new():
    user = get_current_user()
    title = request.form.get("title", "").strip()
    body = request.form.get("body", "").strip()
    category = request.form.get("category", "umumiy")
    if not title or not body:
        flash("Sarlavha va matn to'ldirilishi shart.", "error")
        return redirect(url_for("forum"))
    pid = execute("INSERT INTO forum_posts (user_id, title, body, category) VALUES (?,?,?,?)",
                  (user["id"], title, body, category))
    award_xp(user["id"], 10)
    log_action(user["id"], "forum_new", details=title, ip=request.remote_addr)
    flash("Mavzu muvaffaqiyatli yaratildi.", "success")
    return redirect(url_for("forum_post", post_id=pid))


@app.route("/forum/<int:post_id>")
@login_required
def forum_post(post_id):
    post = query_one(
        "SELECT p.*, u.ism, u.familiya, u.avatar FROM forum_posts p JOIN users u ON u.id=p.user_id WHERE p.id=?",
        (post_id,))
    if not post:
        abort(404)
    execute("UPDATE forum_posts SET views = views + 1 WHERE id=?", (post_id,))
    replies = query_all(
        "SELECT r.*, u.ism, u.familiya, u.avatar, u.role FROM forum_replies r JOIN users u ON u.id=r.user_id "
        "WHERE r.post_id=? ORDER BY r.created_at ASC", (post_id,))
    return render_template("forum_post.html", post=post, replies=replies)


@app.route("/forum/<int:post_id>/reply", methods=["POST"])
@login_required
def forum_reply(post_id):
    user = get_current_user()
    body = request.form.get("body", "").strip()
    if body:
        execute("INSERT INTO forum_replies (post_id, user_id, body) VALUES (?,?,?)", (post_id, user["id"], body))
        execute("UPDATE forum_posts SET replies_count = replies_count + 1 WHERE id=?", (post_id,))
        award_xp(user["id"], 5)
        log_action(user["id"], "forum_reply", details=f"post:{post_id}", ip=request.remote_addr)
    return redirect(url_for("forum_post", post_id=post_id))


# =================================================================
# E-KUTUBXONA / YANGILIKLAR / GAMIFIKATSIYA
# =================================================================
@app.route("/library")
@login_required
def library():
    category = request.args.get("cat", "")
    sql = "SELECT * FROM books"
    args = ()
    if category:
        sql += " WHERE category=?"
        args = (category,)
    sql += " ORDER BY id DESC"
    books = query_all(sql, args)
    return render_template("library.html", books=books, active_cat=category)


@app.route("/news")
@login_required
def news():
    category = request.args.get("cat", "")
    sql = "SELECT * FROM news"
    args = ()
    if category:
        sql += " WHERE category=?"
        args = (category,)
    sql += " ORDER BY published_at DESC LIMIT 40"
    items = query_all(sql, args)
    return render_template("news.html", items=items, active_cat=category)


@app.route("/gamification")
@login_required
def gamification():
    user = get_current_user()
    leaderboard = query_all("SELECT id, ism, familiya, xp, level FROM users WHERE role='student' ORDER BY xp DESC LIMIT 20")
    my_rank_row = query_one(
        "SELECT COUNT(*)+1 as rnk FROM users WHERE role='student' AND xp > (SELECT xp FROM users WHERE id=?)",
        (user["id"],))
    all_badges = query_all("SELECT * FROM badges")
    earned_ids = {r["badge_id"] for r in query_all("SELECT badge_id FROM user_badges WHERE user_id=?", (user["id"],))}
    next_level_xp = (user["level"]) * 500
    return render_template("gamification.html", leaderboard=leaderboard, my_rank=my_rank_row["rnk"],
                            all_badges=all_badges, earned_ids=earned_ids, next_level_xp=next_level_xp)


# =================================================================
# MENTOR PANELI
# =================================================================
@app.route("/mentor")
@admin_required
def mentor():
    students = query_all(
        "SELECT u.id, u.ism, u.familiya, u.email, u.xp, u.level, "
        "(SELECT COUNT(*) FROM enrollments WHERE user_id=u.id) as course_count, "
        "(SELECT AVG(progress_percent) FROM enrollments WHERE user_id=u.id) as avg_progress "
        "FROM users u WHERE u.role='student' ORDER BY u.xp DESC LIMIT 50"
    )
    return render_template("mentor.html", students=students)


# =================================================================
# SOZLAMALAR
# =================================================================
@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    user = get_current_user()
    if request.method == "POST":
        action = request.form.get("action")
        if action == "change_password":
            old_pw = request.form.get("old_password", "")
            new_pw = request.form.get("new_password", "")
            if not check_password_hash(user["password_hash"], old_pw):
                flash("Joriy parol noto'g'ri.", "error")
            elif len(new_pw) < 6:
                flash("Yangi parol kamida 6 belgidan iborat bo'lishi kerak.", "error")
            else:
                execute("UPDATE users SET password_hash=? WHERE id=?", (generate_password_hash(new_pw), user["id"]))
                log_action(user["id"], "change_password", ip=request.remote_addr)
                flash("Parol muvaffaqiyatli o'zgartirildi.", "success")
        elif action == "delete_account":
            log_action(user["id"], "delete_account_request", ip=request.remote_addr)
            session.clear()
            flash("Hisobingiz o'chirish so'rovi qabul qilindi.", "info")
            return redirect(url_for("index"))
        return redirect(url_for("settings"))
    return render_template("settings.html")


# =================================================================
# ADMIN PANEL — bitta yaxlit boshqaruv markazi
# =================================================================
@app.route("/admin")
@admin_required
def admin_dashboard():
    stats = {
        "users": query_one("SELECT COUNT(*) c FROM users")["c"],
        "courses": query_one("SELECT COUNT(*) c FROM courses")["c"],
        "directions": query_one("SELECT COUNT(*) c FROM directions")["c"],
        "lessons": query_one("SELECT COUNT(*) c FROM lessons")["c"],
        "tests": query_one("SELECT COUNT(*) c FROM test_attempts")["c"],
        "active_today": random.randint(80, 320),
    }
    recent_users = query_all("SELECT * FROM users ORDER BY created_at DESC LIMIT 8")
    recent_logs = query_all(
        "SELECT al.*, u.ism, u.familiya FROM action_logs al LEFT JOIN users u ON u.id=al.user_id "
        "ORDER BY al.created_at DESC LIMIT 12")
    top_courses = query_all(
        "SELECT c.title, c.students_count, d.name_uz as direction_name FROM courses c "
        "JOIN directions d ON d.id=c.direction_id ORDER BY c.students_count DESC LIMIT 6")
    # 7 kunlik faollik grafigi uchun sintetik (ammo izchil) qatorlar
    day_labels = [(datetime.date.today() - datetime.timedelta(days=i)).strftime("%d.%m") for i in range(6, -1, -1)]
    activity_series = [random.randint(60, 260) for _ in range(7)]
    source_labels = ["Qidiruv", "Ijtimoiy tarmoq", "Referal", "To'g'ridan-to'g'ri"]
    source_series = [42, 28, 14, 16]
    plan_counts = query_all("SELECT plan, COUNT(*) c FROM users GROUP BY plan")
    return render_template(
        "admin_dashboard.html", stats=stats, recent_users=recent_users, recent_logs=recent_logs,
        top_courses=top_courses, day_labels=day_labels, activity_series=activity_series,
        source_labels=source_labels, source_series=source_series, plan_counts=plan_counts,
    )


@app.route("/admin/users/<int:user_id>/toggle-block", methods=["POST"])
@admin_required
def admin_toggle_block(user_id):
    user = query_one("SELECT * FROM users WHERE id=?", (user_id,))
    if user:
        execute("UPDATE users SET is_blocked=? WHERE id=?", (0 if user["is_blocked"] else 1, user_id))
        log_action(session["user_id"], "admin_toggle_block", details=f"user:{user_id}", ip=request.remote_addr)
    return redirect(url_for("admin_dashboard"))


# =================================================================
# XATOLIK SAHIFALARI
# =================================================================
@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(e):
    return render_template("500.html"), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
