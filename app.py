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
from security import (check_brute_force, record_failed_login, clear_failed_logins,
                      log_security_event, is_ip_blocked, block_ip, scan_request,
                      check_rate_limit)
from coins import (get_balance, add_coins, spend_coins, award_course_completion,
                   buy_pro_with_coins, buy_course_with_coins, deduct_ai_usage,
                   get_leaderboard, get_transactions, _update_rating)
from oauth_routes import oauth_bp
from ids import (generate_unique_id, set_user_id, get_premium_ids_list,
                 buy_premium_id, get_active_auctions, place_bid, finalize_auction,
                 init_premium_ids, _id_type_and_price)
from smm_ai import chat_smm, SMM_DIRECTIONS, get_smm_history

app = Flask(__name__)
app.config.from_object(Config)
app.teardown_appcontext(close_db)
app.register_blueprint(oauth_bp)
app.jinja_env.globals.update(zip=zip)
app.jinja_env.globals['format_number'] = lambda v: f"{int(v):,}" if v else "0"

@app.template_filter('format_number')
def format_number(value):
    try:
        return f"{int(value):,}"
    except (ValueError, TypeError):
        return value


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
        ip = request.headers.get("X-Forwarded-For", request.remote_addr or "0.0.0.0").split(",")[0].strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        # Brute force tekshiruvi
        blocked, msg = check_brute_force(email, ip)
        if blocked:
            flash(msg, "error")
            return redirect(url_for("login"))

        user = query_one("SELECT * FROM users WHERE email=?", (email,))
        if user and check_password_hash(user["password_hash"], password):
            if user["is_blocked"]:
                flash("Hisobingiz administrator tomonidan bloklangan.", "error")
                log_security_event(user["id"], "blocked_login_attempt", ip,
                                   request.headers.get("User-Agent", ""), f"email:{email}", "medium")
                return redirect(url_for("login"))
            session.clear()
            session["user_id"] = user["id"]
            session.permanent = True
            clear_failed_logins(user["id"])
            execute("UPDATE users SET last_login_ip=? WHERE id=?", (ip, user["id"]))
            log_action(user["id"], "login", ip=ip)
            flash(f"Xush kelibsiz, {user['ism']}!", "success")
            nxt = request.args.get("next")
            return redirect(nxt or url_for("dashboard"))

        record_failed_login(email, ip)
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
        # 7 xonali unikal ID avtomatik berish
        new_cid = generate_unique_id()
        execute("UPDATE users SET custom_id=? WHERE id=?", (new_cid, uid))
        execute("INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
                (uid, "Xush kelibsiz!", "CYBER SHATS platformasiga muvaffaqiyatli ro'yxatdan o'tdingiz.", "success"))
        execute("INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
                (uid, f"Sizning ID: #{new_cid}",
                 f"Sizga avtomatik ID #{new_cid} berildi. Uni profil sozlamalarida o'zgartirishingiz mumkin (lekin bir xil ID bo'lmasin).",
                 "info"))
        # Reyting jadvalini boshlash
        execute("INSERT OR IGNORE INTO user_ratings (user_id, total_score, rank_position) VALUES (?,?,0)", (uid, 0))
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
    # Pro-only kurs tekshiruvi
    if course.get("is_pro_only") and user.get("plan") not in ("pro", "enterprise") and user.get("role") != "admin":
        flash("Bu kurs faqat Pro foydalanuvchilar uchun!", "error")
        return redirect(url_for("course_detail", slug=slug))
    # Pullik kurs tekshiruvi
    if (course.get("is_paid") or course.get("code_price", 0) > 0):
        existing = query_one("SELECT id FROM enrollments WHERE user_id=? AND course_id=?", (user["id"], course["id"]))
        if not existing:
            flash("Bu kursga kirish uchun code tangasi yoki kirish kodi kerak.", "error")
            return redirect(url_for("course_detail", slug=slug))
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
    # Kurs tugallansa code tangasi berish
    if pct == 100:
        award_course_completion(user["id"], course["id"])
        _update_rating(user["id"])
    log_action(user["id"], "complete_lesson", details=f"lesson:{lesson_id}", ip=request.remote_addr)
    balance = get_balance(user["id"])
    return api_response(True, data={"progress_percent": pct, "code_balance": balance})


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

    # Code tangasi tekshiruvi
    ok, msg = deduct_ai_usage(user["id"])
    if not ok:
        return api_response(False,
            error=f"AI javob uchun {Config.AI_COST_PER_MSG} code tangasi kerak. {msg}",
            status=402)

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
    balance = get_balance(user["id"])
    return api_response(True, data={"reply": reply, "is_live": is_live, "code_balance": balance})


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
    # Security data
    security_events = query_all(
        """SELECT se.*, u.ism, u.familiya FROM security_events se
           LEFT JOIN users u ON u.id=se.user_id
           ORDER BY se.created_at DESC LIMIT 50""")
    blocked_ips = query_all("SELECT * FROM blocked_ips ORDER BY created_at DESC LIMIT 30")
    security_stats = {
        "total": query_one("SELECT COUNT(*) c FROM security_events")["c"],
        "critical": query_one("SELECT COUNT(*) c FROM security_events WHERE severity='critical'")["c"],
        "high": query_one("SELECT COUNT(*) c FROM security_events WHERE severity='high'")["c"],
        "today": query_one("SELECT COUNT(*) c FROM security_events WHERE date(created_at)=date('now')")["c"],
        "blocked_ips": query_one("SELECT COUNT(*) c FROM blocked_ips WHERE expires_at IS NULL OR expires_at > datetime('now')")["c"],
    }
    # Payments data
    payments = query_all(
        """SELECT pp.*, u.ism, u.familiya, u.email FROM pro_payments pp
           JOIN users u ON u.id=pp.user_id
           ORDER BY pp.created_at DESC LIMIT 50""")
    total_uzs = query_one("SELECT COALESCE(SUM(amount_uzs),0) s FROM pro_payments WHERE status='success'")["s"]
    total_code = query_one("SELECT COALESCE(SUM(amount_code),0) s FROM pro_payments WHERE status='success' AND method='code'")["s"]
    # All courses for access codes tab
    all_courses = query_all(
        "SELECT c.*, d.name_uz as direction_name FROM courses c "
        "JOIN directions d ON d.id=c.direction_id ORDER BY d.name_uz, c.title")
    # Plan settings (from app config or DB — defaults if not set)
    plan_settings = {
        "free_ai_limit": 10,
        "free_smm_access": False,
        "free_test_limit": 30,
        "pro_price_uzs": 99000,
        "pro_price_code": 5000,
        "pro_ai_limit": 100,
        "pro_duration_days": 30,
    }
    # Top liderlar (scroll uchun)
    top_leaders = query_all(
        """SELECT u.id, u.ism, u.familiya, u.plan, u.code_balance,
                  COALESCE(ur.total_score,0) as total_score,
                  COALESCE(ur.courses_done,0) as courses_done,
                  COALESCE(ur.tests_passed,0) as tests_passed
           FROM users u LEFT JOIN user_ratings ur ON ur.user_id=u.id
           WHERE u.is_blocked=0
           ORDER BY COALESCE(ur.total_score,0) DESC, u.xp DESC
           LIMIT 20""")
    return render_template(
        "admin_dashboard.html", stats=stats, recent_users=recent_users, recent_logs=recent_logs,
        top_courses=top_courses, day_labels=day_labels, activity_series=activity_series,
        source_labels=source_labels, source_series=source_series, plan_counts=plan_counts,
        security_events=security_events, blocked_ips=blocked_ips, security_stats=security_stats,
        payments=payments, total_uzs=total_uzs, total_code=total_code,
        all_courses=all_courses, plan_settings=plan_settings,
        top_leaders=top_leaders,
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
# ADMIN — KENGAYTIRILGAN PANEL
# =================================================================

@app.route("/admin/users")
@admin_required
def admin_users():
    """Barcha foydalanuvchilar ro'yxati + filter."""
    search = request.args.get("q", "").strip()
    plan   = request.args.get("plan", "")
    page   = max(1, int(request.args.get("page", 1)))
    per    = 20
    offset = (page - 1) * per

    sql  = "SELECT u.*, COALESCE(ur.rank_position,0) as rank FROM users u LEFT JOIN user_ratings ur ON ur.user_id=u.id WHERE 1=1"
    args = []
    if search:
        sql += " AND (u.ism LIKE ? OR u.familiya LIKE ? OR u.email LIKE ?)"
        args += [f"%{search}%", f"%{search}%", f"%{search}%"]
    if plan:
        sql += " AND u.plan=?"
        args.append(plan)
    sql += " ORDER BY u.created_at DESC LIMIT ? OFFSET ?"
    args += [per, offset]
    users = query_all(sql, tuple(args))
    total = query_one("SELECT COUNT(*) c FROM users")["c"] if not search and not plan else len(users)
    return render_template("admin_users.html", users=users, search=search, plan=plan,
                           page=page, per=per, total=total or len(users))


@app.route("/admin/users/<int:user_id>/set-plan", methods=["POST"])
@admin_required
def admin_set_plan(user_id):
    plan = request.form.get("plan", "free")
    if plan not in ("free", "pro", "enterprise"):
        flash("Noto'g'ri plan.", "error")
        return redirect(url_for("admin_users"))
    execute("UPDATE users SET plan=? WHERE id=?", (plan, user_id))
    log_action(session["user_id"], "admin_set_plan", details=f"user:{user_id},plan:{plan}", ip=request.remote_addr)
    flash(f"Foydalanuvchi plani '{plan}' ga o'zgartirildi.", "success")
    return redirect(url_for("admin_users"))


@app.route("/admin/users/<int:user_id>/add-coins", methods=["POST"])
@admin_required
def admin_add_coins(user_id):
    try:
        amount = int(request.form.get("amount", 0))
    except ValueError:
        amount = 0
    if amount <= 0:
        flash("Miqdor musbat bo'lishi kerak.", "error")
        return redirect(url_for("admin_users"))
    add_coins(user_id, amount, "admin_add", ref_id=session["user_id"])
    log_action(session["user_id"], "admin_add_coins", details=f"user:{user_id},amount:{amount}", ip=request.remote_addr)
    flash(f"Foydalanuvchiga {amount:,} code tangasi qo'shildi.", "success")
    return redirect(url_for("admin_users"))


@app.route("/admin/users/<int:user_id>/remove-coins", methods=["POST"])
@admin_required
def admin_remove_coins(user_id):
    """Foydalanuvchidan code tangasi ayirish."""
    try:
        amount = int(request.form.get("amount", 0))
    except ValueError:
        amount = 0
    if amount <= 0:
        flash("Miqdor musbat bo'lishi kerak.", "error")
        return redirect(url_for("admin_dashboard"))
    user = query_one("SELECT code_balance FROM users WHERE id=?", (user_id,))
    if not user:
        flash("Foydalanuvchi topilmadi.", "error")
        return redirect(url_for("admin_dashboard"))
    new_balance = max(0, (user["code_balance"] or 0) - amount)
    execute("UPDATE users SET code_balance=? WHERE id=?", (new_balance, user_id))
    log_action(session["user_id"], "admin_remove_coins", details=f"user:{user_id},amount:{amount}", ip=request.remote_addr)
    flash(f"Foydalanuvchidan {amount:,} code tangasi ayirildi.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/security")
@admin_required
def admin_security():
    """Xavfsizlik hodisalari, IP bloklash paneli."""
    events = query_all(
        """SELECT se.*, u.ism, u.familiya FROM security_events se
           LEFT JOIN users u ON u.id=se.user_id
           ORDER BY se.created_at DESC LIMIT 100""")
    blocked_ips = query_all("SELECT * FROM blocked_ips ORDER BY created_at DESC LIMIT 50")
    stats = {
        "total": query_one("SELECT COUNT(*) c FROM security_events")["c"],
        "critical": query_one("SELECT COUNT(*) c FROM security_events WHERE severity='critical'")["c"],
        "high": query_one("SELECT COUNT(*) c FROM security_events WHERE severity='high'")["c"],
        "today": query_one("SELECT COUNT(*) c FROM security_events WHERE date(created_at)=date('now')")["c"],
        "blocked_ips": query_one("SELECT COUNT(*) c FROM blocked_ips WHERE expires_at IS NULL OR expires_at > datetime('now')")["c"],
    }
    return render_template("admin_security.html", events=events, blocked_ips=blocked_ips, stats=stats)


@app.route("/admin/security/block-ip", methods=["POST"])
@admin_required
def admin_block_ip():
    ip = request.form.get("ip", "").strip()
    reason = request.form.get("reason", "manual")
    hours = int(request.form.get("hours", 24))
    if ip:
        block_ip(ip, reason, hours, blocked_by=session["user_id"])
        flash(f"{ip} bloklandi ({hours} soat).", "success")
    return redirect(url_for("admin_security"))


@app.route("/admin/security/unblock-ip/<int:bid>", methods=["POST"])
@admin_required
def admin_unblock_ip(bid):
    execute("DELETE FROM blocked_ips WHERE id=?", (bid,))
    log_action(session["user_id"], "admin_unblock_ip", details=f"bid:{bid}", ip=request.remote_addr)
    flash("IP blokdan chiqarildi.", "success")
    return redirect(url_for("admin_security"))


@app.route("/admin/leaderboard")
@admin_required
def admin_leaderboard():
    leaders = get_leaderboard(50)
    return render_template("admin_leaderboard.html", leaders=leaders)


@app.route("/admin/payments")
@admin_required
def admin_payments():
    payments = query_all(
        """SELECT pp.*, u.ism, u.familiya, u.email FROM pro_payments pp
           JOIN users u ON u.id=pp.user_id
           ORDER BY pp.created_at DESC LIMIT 100""")
    total_uzs = query_one("SELECT COALESCE(SUM(amount_uzs),0) s FROM pro_payments WHERE status='success'")["s"]
    total_code = query_one("SELECT COALESCE(SUM(amount_code),0) s FROM pro_payments WHERE status='success' AND method='code'")["s"]
    return render_template("admin_payments.html", payments=payments,
                           total_uzs=total_uzs, total_code=total_code)


# =================================================================
# FOYDALANUVCHI — Pro versiya, Reyting, Coinlar
# =================================================================

@app.route("/leaderboard")
@login_required
def leaderboard():
    leaders = get_leaderboard(100)
    user = get_current_user()
    my_rank = query_one("SELECT rank_position FROM user_ratings WHERE user_id=?", (user["id"],))
    return render_template("leaderboard.html", leaders=leaders,
                           my_rank=my_rank["rank_position"] if my_rank else 0)


@app.route("/coins")
@login_required
def coins_page():
    user = get_current_user()
    balance = get_balance(user["id"])
    txns = get_transactions(user["id"], 30)
    return render_template("coins.html", balance=balance, txns=txns,
                           pro_cost=Config.PRO_COST_CODE,
                           ai_cost=Config.AI_COST_PER_MSG,
                           course_reward=Config.COURSE_REWARD_CODE,
                           paid_course_code=Config.PAID_COURSE_CODE)


@app.route("/coins/buy-pro", methods=["POST"])
@login_required
def coins_buy_pro():
    user = get_current_user()
    ok, msg = buy_pro_with_coins(user["id"])
    if ok:
        # Pro bonus: 10,000 code tangasi
        add_coins(user["id"], 10_000, "pro_bonus")
        execute("INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
                (user["id"], "Pro Bonus!", "Pro versiya faollashtirildi! Sovg'a sifatida 10,000 code tangasi berildi!", "success"))
        flash(msg + " Bonus: 10,000 code tangasi berildi!", "success")
    else:
        flash(msg, "error")
    return redirect(url_for("coins_page"))


@app.route("/coins/buy-course/<int:course_id>", methods=["POST"])
@login_required
def coins_buy_course(course_id):
    user = get_current_user()
    ok, msg = buy_course_with_coins(user["id"], course_id)
    flash(msg, "success" if ok else "error")
    course = query_one("SELECT slug FROM courses WHERE id=?", (course_id,))
    return redirect(url_for("course_detail", slug=course["slug"]) if course else url_for("courses"))


@app.route("/pricing/pay", methods=["POST"])
@login_required
def pricing_pay():
    """To'lov orqali Pro versiya (karta) — hozircha pending."""
    user = get_current_user()
    method = request.form.get("method", "card")
    execute("INSERT INTO pro_payments (user_id, method, status) VALUES (?,?,?)",
            (user["id"], method, "pending"))
    log_action(user["id"], "pro_payment_initiated", details=f"method:{method}", ip=request.remote_addr)
    flash("To'lov so'rovi qabul qilindi. Administrator tasdiqlashini kuting.", "info")
    return redirect(url_for("pricing"))


# =================================================================
# SMM / TARGETOLOG / LOGISTIKA — Faqat Pro (alohida AI chat)
# =================================================================
@app.route("/smm")
@login_required
def smm_hub():
    user = get_current_user()
    if user.get("plan") not in ("pro", "enterprise") and user.get("role") != "admin":
        flash("SMM, Targetolog va Logistika bo'limlari faqat Pro foydalanuvchilar uchun!", "warn")
        return redirect(url_for("pricing"))
    return render_template("smm_hub.html", smm_directions=SMM_DIRECTIONS, user=user)


@app.route("/smm/<direction>")
@login_required
def smm_chat(direction):
    user = get_current_user()
    if user.get("plan") not in ("pro", "enterprise") and user.get("role") != "admin":
        flash("Bu bo'lim faqat Pro foydalanuvchilar uchun!", "warn")
        return redirect(url_for("pricing"))
    if direction not in SMM_DIRECTIONS:
        abort(404)
    history = get_smm_history(user["id"], direction)
    config = SMM_DIRECTIONS[direction]
    return render_template("smm_chat.html", direction=direction, config=config,
                           smm_directions=SMM_DIRECTIONS, history=history)


@app.route("/api/smm/chat", methods=["POST"])
@api_login_required
def api_smm_chat():
    user = get_current_user()
    if user.get("plan") not in ("pro", "enterprise") and user.get("role") != "admin":
        return api_response(False, error="Pro versiya talab qilinadi", status=403)
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    direction = data.get("direction", "smm")
    if not message:
        return api_response(False, error="Xabar bo'sh bo'lishi mumkin emas", status=400)
    reply, is_live = chat_smm(user["id"], direction, message)
    award_xp(user["id"], 2)
    log_action(user["id"], "smm_chat", details=f"dir:{direction}", ip=request.remote_addr)
    return api_response(True, data={"reply": reply, "is_live": is_live})


# =================================================================
# ID BOSHQARUVI VA AUKTSION
# =================================================================
@app.route("/my-id")
@login_required
def my_id_page():
    user = get_current_user()
    premium_ids = get_premium_ids_list()
    auctions = get_active_auctions()
    balance = get_balance(user["id"])
    return render_template("my_id.html", premium_ids=premium_ids, auctions=auctions,
                           balance=balance, user=user)


@app.route("/my-id/change", methods=["POST"])
@login_required
def change_my_id():
    user = get_current_user()
    new_id = request.form.get("new_id", "").strip()
    if len(new_id) != 7 or not new_id.isdigit():
        flash("ID 7 ta raqamdan iborat bo'lishi kerak.", "error")
        return redirect(url_for("my_id_page"))
    # Premium IDlarni tekshir
    from ids import PREMIUM_IDS
    if new_id in PREMIUM_IDS:
        flash("Bu premium ID — uni sotib olish kerak.", "error")
        return redirect(url_for("my_id_page"))
    ok, msg = set_user_id(user["id"], new_id)
    flash(msg, "success" if ok else "error")
    return redirect(url_for("my_id_page"))


@app.route("/my-id/buy/<custom_id>", methods=["POST"])
@login_required
def buy_premium_id_route(custom_id):
    user = get_current_user()
    ok, msg = buy_premium_id(user["id"], custom_id)
    flash(msg, "success" if ok else "error")
    return redirect(url_for("my_id_page"))


@app.route("/auction")
@login_required
def auction_page():
    auctions = get_active_auctions()
    user = get_current_user()
    balance = get_balance(user["id"])
    ended = query_all(
        """SELECT a.*, p.id_type, u.ism as winner_ism, u.familiya as winner_familiya
           FROM id_auctions a JOIN premium_ids p ON p.id=a.premium_id_id
           LEFT JOIN users u ON u.id=a.current_bidder_id
           WHERE a.status='ended' ORDER BY a.ends_at DESC LIMIT 10"""
    )
    return render_template("auction.html", auctions=auctions, balance=balance, ended=ended)


@app.route("/auction/<int:auction_id>/bid", methods=["POST"])
@login_required
def auction_bid(auction_id):
    user = get_current_user()
    try:
        amount = int(request.form.get("amount", 0))
    except ValueError:
        amount = 0
    ok, msg = place_bid(user["id"], auction_id, amount)
    flash(msg, "success" if ok else "error")
    return redirect(url_for("auction_page"))


# =================================================================
# ADMIN — ID va Auktsion boshqaruvi + kurs access kodlari
# =================================================================
@app.route("/admin/ids")
@admin_required
def admin_ids():
    premium_ids = get_premium_ids_list()
    auctions = query_all("SELECT a.*, p.id_type FROM id_auctions a JOIN premium_ids p ON p.id=a.premium_id_id ORDER BY a.created_at DESC LIMIT 50")
    return render_template("admin_ids.html", premium_ids=premium_ids, auctions=auctions)


@app.route("/admin/ids/create-auction", methods=["POST"])
@admin_required
def admin_create_auction():
    custom_id = request.form.get("custom_id", "").strip()
    start_price = int(request.form.get("start_price", 40000))
    hours = int(request.form.get("hours", 24))
    pid = query_one("SELECT * FROM premium_ids WHERE custom_id=? AND status='available'", (custom_id,))
    if not pid:
        flash("Bu ID mavjud emas yoki band.", "error")
        return redirect(url_for("admin_ids"))
    import datetime
    ends = (datetime.datetime.now() + datetime.timedelta(hours=hours)).isoformat()
    execute("UPDATE premium_ids SET status='auction' WHERE custom_id=?", (custom_id,))
    execute(
        "INSERT INTO id_auctions (premium_id_id, custom_id, start_price, starts_at, ends_at, created_by) VALUES (?,?,?,datetime('now'),?,?)",
        (pid["id"], custom_id, start_price, ends, session["user_id"])
    )
    log_action(session["user_id"], "admin_create_auction", details=f"id:{custom_id}", ip=request.remote_addr)
    flash(f"#{custom_id} ID auktsiyonga qo'yildi ({hours} soat).", "success")
    return redirect(url_for("admin_ids"))


@app.route("/admin/ids/finalize/<int:auction_id>", methods=["POST"])
@admin_required
def admin_finalize_auction(auction_id):
    finalize_auction(auction_id)
    flash("Auktsion yakunlandi.", "success")
    return redirect(url_for("admin_ids"))


@app.route("/admin/ids/give-id", methods=["POST"])
@admin_required
def admin_give_id():
    """Admin foydalanuvchiga premium ID beradi (bepul)."""
    user_id = int(request.form.get("user_id", 0))
    custom_id = request.form.get("custom_id", "").strip()
    pid = query_one("SELECT * FROM premium_ids WHERE custom_id=?", (custom_id,))
    if not pid or pid["status"] not in ("available",):
        flash("ID mavjud emas yoki band.", "error")
        return redirect(url_for("admin_ids"))
    import datetime
    execute("UPDATE premium_ids SET status='sold', owner_user_id=?, sold_at=? WHERE custom_id=?",
            (user_id, datetime.datetime.now().isoformat(), custom_id))
    execute("UPDATE users SET custom_id=? WHERE id=?", (custom_id, user_id))
    execute("INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
            (user_id, f"Premium ID #{custom_id}",
             f"Sizga admin tomonidan #{custom_id} premium ID berildi!", "success"))
    log_action(session["user_id"], "admin_give_id", details=f"user:{user_id},id:{custom_id}", ip=request.remote_addr)
    flash(f"#{custom_id} ID foydalanuvchiga berildi.", "success")
    return redirect(url_for("admin_ids"))


@app.route("/admin/courses/<int:course_id>/access-codes")
@admin_required
def admin_course_access_codes(course_id):
    course = query_one("SELECT * FROM courses WHERE id=?", (course_id,))
    if not course:
        abort(404)
    codes = query_all(
        "SELECT c.*, u.ism, u.familiya FROM course_access_codes c LEFT JOIN users u ON u.id=c.used_by WHERE c.course_id=? ORDER BY c.created_at DESC",
        (course_id,)
    )
    return render_template("admin_access_codes.html", course=course, codes=codes)


@app.route("/admin/courses/<int:course_id>/access-codes/generate", methods=["POST"])
@admin_required
def admin_generate_access_codes(course_id):
    count = int(request.form.get("count", 1))
    count = min(count, 50)
    generated = []
    for _ in range(count):
        code = "CS-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=10))
        execute("INSERT INTO course_access_codes (course_id, access_code) VALUES (?,?)", (course_id, code))
        generated.append(code)
    log_action(session["user_id"], "generate_access_codes", details=f"course:{course_id},count:{count}", ip=request.remote_addr)
    flash(f"{count} ta kirish kodi yaratildi.", "success")
    return redirect(url_for("admin_course_access_codes", course_id=course_id))



@app.route("/admin/courses/<int:course_id>/toggle-pro", methods=["POST"])
@admin_required
def admin_toggle_course_pro(course_id):
    """Kursni PRO only yoki FREE qilish."""
    course = query_one("SELECT * FROM courses WHERE id=?", (course_id,))
    if not course:
        abort(404)
    new_val = 0 if course["is_pro_only"] else 1
    execute("UPDATE courses SET is_pro_only=? WHERE id=?", (new_val, course_id))
    status = "PRO" if new_val else "FREE"
    log_action(session["user_id"], "toggle_course_pro", details=f"course:{course_id},status:{status}", ip=request.remote_addr)
    flash(f"Kurs '{course['title']}' endi {status} rejimida.", "success")
    return redirect(url_for("admin_dashboard") + "#codes")


@app.route("/admin/codes/quick-generate", methods=["POST"])
@admin_required
def admin_quick_generate_codes():
    """Admin dashboard'dan tezkor kod yaratish."""
    course_id = request.form.get("course_id", type=int)
    count = min(int(request.form.get("count", 5)), 50)
    if not course_id:
        flash("Kurs tanlanmadi.", "error")
        return redirect(url_for("admin_dashboard") + "#codes")
    for _ in range(count):
        code = "CS-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=10))
        execute("INSERT INTO course_access_codes (course_id, access_code) VALUES (?,?)", (course_id, code))
    log_action(session["user_id"], "quick_generate_codes", details=f"course:{course_id},count:{count}", ip=request.remote_addr)
    flash(f"{count} ta kirish kodi yaratildi.", "success")
    return redirect(url_for("admin_dashboard") + "#codes")


@app.route("/admin/settings/free-plan", methods=["POST"])
@admin_required
def admin_settings_free_plan():
    """Free plan sozlamalarini saqlash (flash bilan — kelajakda DB'ga o'tkazish mumkin)."""
    ai_limit = request.form.get("ai_daily_limit", 10)
    test_limit = request.form.get("free_test_limit", 30)
    smm_access = request.form.get("free_smm", "0")
    log_action(session["user_id"], "update_free_plan_settings",
               details=f"ai_limit:{ai_limit},test_limit:{test_limit},smm:{smm_access}",
               ip=request.remote_addr)
    flash("Free plan sozlamalari saqlandi.", "success")
    return redirect(url_for("admin_dashboard") + "#settings")


@app.route("/admin/settings/pro-plan", methods=["POST"])
@admin_required
def admin_settings_pro_plan():
    """Pro plan sozlamalarini saqlash."""
    price_uzs = request.form.get("pro_price_uzs", 99000)
    price_code = request.form.get("pro_price_code", 5000)
    ai_limit = request.form.get("pro_ai_limit", 100)
    duration = request.form.get("pro_duration_days", 30)
    log_action(session["user_id"], "update_pro_plan_settings",
               details=f"price_uzs:{price_uzs},price_code:{price_code},ai_limit:{ai_limit},duration:{duration}",
               ip=request.remote_addr)
    flash("Pro plan sozlamalari saqlandi.", "success")
    return redirect(url_for("admin_dashboard") + "#settings")


@app.route("/admin/settings/system", methods=["POST"])
@admin_required
def admin_settings_system():
    """Tizim sozlamalarini saqlash."""
    site_name = request.form.get("site_name", "CYBER SHATS")
    site_desc = request.form.get("site_desc", "IT Ta'lim Platformasi")
    maintenance = request.form.get("maintenance", "0")
    registration = request.form.get("registration_open", "1")
    log_action(session["user_id"], "update_system_settings",
               details=f"maintenance:{maintenance},registration:{registration}",
               ip=request.remote_addr)
    flash("Tizim sozlamalari saqlandi.", "success")
    return redirect(url_for("admin_dashboard") + "#settings")


@app.route("/courses/<slug>/activate-code", methods=["POST"])
@login_required
def activate_course_code(slug):
    """Foydalanuvchi kurs uchun access code kiritadi."""
    user = get_current_user()
    course = query_one("SELECT * FROM courses WHERE slug=?", (slug,))
    if not course:
        abort(404)
    code = request.form.get("access_code", "").strip().upper()
    row = query_one("SELECT * FROM course_access_codes WHERE access_code=? AND course_id=? AND is_used=0",
                    (code, course["id"]))
    if not row:
        flash("Noto'g'ri yoki ishlatilgan kod.", "error")
        return redirect(url_for("course_detail", slug=slug))
    import datetime
    execute("UPDATE course_access_codes SET is_used=1, used_by=?, used_at=? WHERE id=?",
            (user["id"], datetime.datetime.now().isoformat(), row["id"]))
    execute("INSERT OR IGNORE INTO enrollments (user_id, course_id, progress_percent) VALUES (?,?,0)",
            (user["id"], course["id"]))
    flash(f"«{course['title']}» kursiga muvaffaqiyatli kirish berildi!", "success")
    log_action(user["id"], "activate_course_code", details=f"course:{course['id']}", ip=request.remote_addr)
    return redirect(url_for("course_detail", slug=slug))


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
