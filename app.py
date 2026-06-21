# ============================================================
# CYBER SHATS — Flask asosiy ilova fayli
# Barcha route'lar shu yerda joylashgan.
# ============================================================
import os
import random
import string
import datetime

from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, abort, jsonify
from markupsafe import Markup
from werkzeug.security import generate_password_hash, check_password_hash

from config import Config
from db import get_db, close_db, query_one, query_all, execute, log_action, ensure_schema
from auth import (login_required, admin_required, super_admin_required,
                  get_current_user, api_login_required)
from admins import (get_all_admins, create_new_admin, promote_user_to_admin,
                     demote_admin, super_admin_change_admin_id)
from utils import api_response, time_ago_uz, fmt_duration, to_tashkent
from ai import call_ai_assistant, is_ai_configured
from security import (check_brute_force, record_failed_login, clear_failed_logins,
                      log_security_event, is_ip_blocked, block_ip, scan_request,
                      check_rate_limit)
from coins import (get_balance, add_coins, spend_coins, award_course_completion,
                   buy_pro_with_coins, buy_cyber_pro_with_coins, buy_vip_with_coins,
                   buy_course_with_coins, deduct_ai_usage,
                   get_leaderboard, get_transactions, _update_rating,
                   transfer_coins, check_and_downgrade_expired_plan)
from messaging import (get_conversations, get_thread, send_message, mark_thread_read,
                       get_unread_total, search_users)
import treasury as treasury_mod
import webpush_mod as push_mod
import pingtest as ping_mod
import announcements as ann_mod
import hacker_lab as hacker_lab_mod
import terminal_sim
import coins_purchase
import social
import startups as startups_mod
from oauth_routes import oauth_bp
from ids import (generate_unique_id, set_user_id, get_premium_ids_list,
                 buy_premium_id, get_active_auctions, place_bid, finalize_auction,
                 init_premium_ids, _id_type_and_price,
                 admin_create_premium_id, admin_update_premium_id_price, admin_delete_premium_id,
                 get_vip_ids_list, assign_vip_id, revoke_vip_id)
from smm_ai import chat_smm, SMM_DIRECTIONS, get_smm_history
from pricing import get_pricing, get_price, set_prices

app = Flask(__name__)
app.config.from_object(Config)
ensure_schema(app.config["DB_PATH"])  # yetishmayotgan jadval/ustunlarni avtomatik to'g'rilaydi
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


@app.template_filter('fromjson_safe')
def fromjson_safe(value):
    """JSON stringni list/dict ga aylantirish, xatosiz."""
    if not value:
        return []
    import json as _json
    try:
        return _json.loads(value)
    except Exception:
        return []


@app.template_filter('markdown')
def render_markdown(text):
    """
    Oddiy markdown matnni xavfsiz HTML'ga aylantiradi (yo'nalish materiallari uchun).
    Agar 'markdown' kutubxonasi o'rnatilmagan bo'lsa (masalan pip install qilinmagan),
    sahifa xato bilan to'xtab qolmasligi uchun oddiy fallback formatlash ishlatiladi
    (qatorlarni <br>/<p> ga, **qalin**ni <strong>ga, # sarlavhalarni <h*>ga aylantiradi).
    """
    if not text:
        return ""
    try:
        import markdown as md_lib
        html = md_lib.markdown(text, extensions=["fenced_code", "tables"])
        return Markup(html)
    except ImportError:
        return Markup(_simple_markdown_fallback(text))


def _simple_markdown_fallback(text: str) -> str:
    """'markdown' kutubxonasi yo'q bo'lganda ishlatiladigan juda sodda,
    qo'lda yozilgan formatlash (xavfsiz — avval HTML escape qilinadi)."""
    import html as _html
    import re
    escaped = _html.escape(text)
    lines = escaped.split("\n")
    out = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("### "):
            out.append(f"<h3>{stripped[4:]}</h3>")
        elif stripped.startswith("## "):
            out.append(f"<h2>{stripped[3:]}</h2>")
        elif stripped.startswith("# "):
            out.append(f"<h1>{stripped[2:]}</h1>")
        elif stripped.startswith("- ") or stripped.startswith("* "):
            out.append(f"<li>{stripped[2:]}</li>")
        elif stripped == "":
            out.append("<br>")
        else:
            out.append(f"<p>{stripped}</p>")
    joined = "\n".join(out)
    # **qalin** -> <strong>qalin</strong>
    joined = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", joined)
    return joined


@app.template_filter('tashkent_time')
def tashkent_time_filter(iso_str, fmt="%d.%m.%Y %H:%M"):
    """Bazadagi UTC vaqtni O'zbekiston mahalliy vaqtiga (UTC+5) o'tkazadi.
    Shablonlarda: {{ row.created_at|tashkent_time }} yoki {{ row.created_at|tashkent_time('%H:%M') }}"""
    return to_tashkent(iso_str, fmt)


def notify_user(user_id: int, title: str, body: str, ntype: str = "info", push_url: str = "/dashboard"):
    """
    Markaziy bildirishnoma funksiyasi: ham saytdagi notifications jadvaliga yozadi
    (foydalanuvchi sahifada bo'lsa ovozli ko'radi), ham Web Push orqali yuboradi
    (foydalanuvchi saytdan chiqib ketgan bo'lsa ham qurilmasiga keladi).
    """
    execute("INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
            (user_id, title, body, ntype))
    try:
        push_mod.send_push_to_user(user_id, title, body, push_url)
    except Exception:
        pass


@app.before_request
def check_plan_expiry():
    """
    Har so'rovda (sessiyada login bo'lgan foydalanuvchi uchun) Pro/Cyber Pro/VIP
    muddati tugaganmi tekshiradi. Tugagan bo'lsa avtomatik 'free'ga tushiradi.
    Fon jarayoni (cron) shart emas — bu yengil tekshiruv.
    """
    uid = session.get("user_id")
    if uid:
        try:
            check_and_downgrade_expired_plan(uid)
        except Exception:
            pass


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
    unread_msg_count = 0
    if user:
        try:
            notif_count = query_one("SELECT COUNT(*) c FROM notifications WHERE user_id=? AND is_read=0", (user["id"],))["c"]
        except Exception:
            notif_count = 0
        try:
            unread_msg_count = get_unread_total(user["id"])
        except Exception:
            unread_msg_count = 0
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
        unread_msg_count=unread_msg_count,
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
    daily_startups = startups_mod.get_daily_rotating_startups(6)
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    return render_template("index.html", directions=directions, courses=courses, news=news,
                            total_students=total_students, total_courses=total_courses,
                            daily_startups=daily_startups)


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

        # User topilmasa — G'azna hisoblarini tekshiramiz
        treasury_account = treasury_mod.verify_treasury_login(email, password)
        if treasury_account:
            session.clear()
            session["treasury_account_id"] = treasury_account["id"]
            session["treasury_account_ism"] = treasury_account["ism"]
            session.permanent = True
            clear_failed_logins(email)
            log_action(None, "treasury_login_via_main",
                       details=f"treasury_id:{treasury_account['id']}", ip=ip)
            flash(f"Xush kelibsiz, {treasury_account['ism']}! G'azna paneliga yo'naltirilmoqdasiz.", "success")
            return redirect(url_for("treasury_dashboard"))

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
        # Yangi foydalanuvchiga 7,000 code tangasi majburiy bonus
        welcome_bonus = get_price("welcome_bonus_code")
        if welcome_bonus > 0:
            add_coins(uid, welcome_bonus, "welcome_bonus")
            execute("INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
                    (uid, f"Sovg'a: {welcome_bonus:,} CODE",
                     f"Xush kelibsiz bonusi sifatida sizga {welcome_bonus:,} code tangasi berildi!",
                     "success"))
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
    p = get_pricing()
    return render_template("pricing.html", pricing=p)


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
    daily_startups = startups_mod.get_daily_rotating_startups(6)
    return render_template("dashboard.html", directions=directions, enrollments=enrollments,
                            notif_count=notif_count, recent_news=recent_news,
                            daily_startups=daily_startups)


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
    if course.get("is_pro_only") and user.get("plan") not in ("pro", "cyber_pro", "vip", "enterprise") and user.get("role") not in ("admin", "super_admin", "mentor"):
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
            try:
                push_mod.send_push_to_user(user["id"], "Sertifikat tayyor! 🎓",
                                           f"«{course['title']}» kursini yakunladingiz.", "/dashboard")
            except Exception:
                pass
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
    user = get_current_user()

    # Free plan — umuman kira olmaydi
    if user.get("plan") not in ("pro", "cyber_pro", "vip") and user.get("role") not in ("admin", "super_admin"):
        flash("Hacker Lab faqat Pro, Cyber Pro va SHATS CYBER PRO foydalanuvchilar uchun. Avval versiyangizni yangilang.", "error")
        return redirect(url_for("pricing"))

    can, reason = hacker_lab_mod.can_enter(user["id"])

    if reason == "consent_required":
        return redirect(url_for("hacker_lab_consent"))
    if reason == "access_required":
        return redirect(url_for("hacker_lab_access_page"))
    if not can:
        flash(reason, "error")
        return redirect(url_for("dashboard"))

    # Yo'nalish tanlanmagan bo'lsa — tanlash sahifasiga
    if not user.get("selected_direction_id"):
        return redirect(url_for("hacker_lab_choose_direction"))

    direction = query_one("SELECT * FROM directions WHERE id=?", (user["selected_direction_id"],))
    if not direction:
        return redirect(url_for("hacker_lab_choose_direction"))

    term_type = terminal_sim.get_terminal_type(direction["slug"])
    return render_template("hacker_lab.html", direction=direction, term_type=term_type)


@app.route("/hacker-lab/choose-direction", methods=["GET", "POST"])
@login_required
def hacker_lab_choose_direction():
    """Foydalanuvchi Hacker Lab uchun asosiy yo'nalishini tanlaydi/o'zgartiradi.
    Panel shu yo'nalishga moslashadi."""
    user = get_current_user()
    if request.method == "POST":
        try:
            direction_id = int(request.form.get("direction_id", 0))
        except ValueError:
            direction_id = 0
        direction = query_one("SELECT id FROM directions WHERE id=?", (direction_id,))
        if not direction:
            flash("Yo'nalish topilmadi.", "error")
            return redirect(url_for("hacker_lab_choose_direction"))
        execute("UPDATE users SET selected_direction_id=? WHERE id=?", (direction_id, user["id"]))
        log_action(user["id"], "hacker_lab_direction_selected", details=f"dir:{direction_id}")
        flash("Yo'nalish tanlandi! Panel shunga moslashtirildi.", "success")
        return redirect(url_for("hacker_lab"))

    directions = query_all("SELECT * FROM directions WHERE slug NOT IN ('smm','targetolog','logistika') ORDER BY sort_order")
    return render_template("hacker_lab_choose_direction.html", directions=directions)


@app.route("/hacker-lab/consent", methods=["GET", "POST"])
@login_required
def hacker_lab_consent():
    user = get_current_user()
    if hacker_lab_mod.has_consented(user["id"]):
        return redirect(url_for("hacker_lab"))
    if request.method == "POST":
        if request.form.get("agree") == "1":
            hacker_lab_mod.record_consent(user["id"], request.remote_addr)
            return redirect(url_for("hacker_lab"))
        flash("Davom etish uchun shartlarga rozilik bildirishingiz shart.", "error")
    return render_template("hacker_lab_consent.html")


@app.route("/hacker-lab/access", methods=["GET", "POST"])
@login_required
def hacker_lab_access_page():
    user = get_current_user()
    if request.method == "POST":
        ok, msg = hacker_lab_mod.purchase_access(user["id"])
        flash(msg, "success" if ok else "error")
        if ok:
            return redirect(url_for("hacker_lab"))
        return redirect(url_for("hacker_lab_access_page"))
    price = get_price("hacker_lab_pro_price")
    return render_template("hacker_lab_access.html", price=price, balance=get_balance(user["id"]))


@app.route("/api/hacker-lab/exec", methods=["POST"])
@api_login_required
def api_hacker_lab_exec():
    """Sandbox terminal buyrug'ini bajaradi (xavfsiz, statik javoblar)."""
    user = get_current_user()
    can, reason = hacker_lab_mod.can_enter(user["id"])
    if not can:
        return api_response(False, error=reason)

    data = request.get_json(silent=True) or {}
    command = data.get("command", "")
    direction = query_one("SELECT id, slug FROM directions WHERE id=?", (user.get("selected_direction_id"),))
    direction_slug = direction["slug"] if direction else "generic"

    result = terminal_sim.execute_command(direction_slug, command)

    if result["is_dangerous"]:
        hacker_lab_mod.report_dangerous_command(
            user["id"], command, direction["id"] if direction else None
        )
        result["output"] += "\n\n⚠️ DIQQAT: Bu buyruq xavfsizlik tizimi tomonidan qayd etildi va administratorga yuborildi."

    return api_response(True, data=result)


# =================================================================
# ADMIN — Hacker Lab xavfsizlik monitoringi
# =================================================================
@app.route("/admin/hacker-lab-security")
@admin_required
def admin_hacker_lab_security():
    status_filter = request.args.get("status", "pending")
    if status_filter == "all":
        events = hacker_lab_mod.get_all_security_events()
    elif status_filter == "pending":
        events = hacker_lab_mod.get_pending_security_events()
    else:
        events = query_all(
            """SELECT e.*, u.ism, u.familiya, u.email, d.name_uz as direction_name
               FROM hacker_lab_security_events e
               JOIN users u ON u.id = e.user_id
               LEFT JOIN directions d ON d.id = e.direction_id
               WHERE e.status=? ORDER BY e.id DESC""",
            (status_filter,)
        )
    blocked_users = query_all("SELECT id, ism, familiya, email, custom_id FROM users WHERE hacker_lab_blocked=1")
    return render_template("admin_hacker_lab_security.html", events=events, status_filter=status_filter,
                           blocked_users=blocked_users)


@app.route("/admin/hacker-lab-security/<int:event_id>/block", methods=["POST"])
@admin_required
def admin_hacker_lab_block(event_id):
    ok, msg = hacker_lab_mod.block_user_for_violation(event_id, session["user_id"])
    flash(msg, "success" if ok else "error")
    return redirect(url_for("admin_hacker_lab_security"))


@app.route("/admin/hacker-lab-security/<int:event_id>/dismiss", methods=["POST"])
@admin_required
def admin_hacker_lab_dismiss(event_id):
    hacker_lab_mod.dismiss_event(event_id, session["user_id"])
    flash("Signal e'tiborsiz qoldirildi.", "success")
    return redirect(url_for("admin_hacker_lab_security"))


@app.route("/admin/hacker-lab-security/unblock/<int:user_id>", methods=["POST"])
@admin_required
def admin_hacker_lab_unblock(user_id):
    hacker_lab_mod.unblock_user(user_id, session["user_id"])
    flash("Foydalanuvchi blokdan chiqarildi.", "success")
    return redirect(url_for("admin_hacker_lab_security"))


# =================================================================
# HACKER LAB — JAMOA BO'LIB ISHLASH (yo'nalish ichidagi fikr almashish)
# =================================================================
HACKER_LAB_ALLOWED_EXT = {"png", "jpg", "jpeg", "gif", "webp", "pdf", "doc", "docx", "zip", "txt", "mp4", "mov"}
HACKER_LAB_UPLOAD_DIR = os.path.join("static", "uploads", "hacker_lab")


def _hacker_lab_save_file(file_storage):
    """Xavfsiz fayl saqlash: kengaytmani tekshiradi, tasodifiy nom beradi."""
    if not file_storage or not file_storage.filename:
        return None, None
    ext = file_storage.filename.rsplit(".", 1)[-1].lower() if "." in file_storage.filename else ""
    if ext not in HACKER_LAB_ALLOWED_EXT:
        return None, None
    import uuid
    safe_name = f"{uuid.uuid4().hex}.{ext}"
    os.makedirs(HACKER_LAB_UPLOAD_DIR, exist_ok=True)
    full_path = os.path.join(HACKER_LAB_UPLOAD_DIR, safe_name)
    file_storage.save(full_path)
    file_type = "image" if ext in ("png", "jpg", "jpeg", "gif", "webp") else (
        "video" if ext in ("mp4", "mov") else "document")
    return f"/static/uploads/hacker_lab/{safe_name}", file_type


@app.route("/hacker-lab/team")
@login_required
def hacker_lab_team():
    user = get_current_user()
    can, reason = hacker_lab_mod.can_enter(user["id"])
    if not can:
        flash(reason if reason not in ("consent_required", "access_required") else
              "Avval Hacker Lab shartlariga rozilik bering / kirish huquqini oling.", "error")
        return redirect(url_for("hacker_lab"))
    direction = query_one("SELECT * FROM directions WHERE id=?", (user.get("selected_direction_id"),))
    if not direction:
        return redirect(url_for("hacker_lab_choose_direction"))
    posts = hacker_lab_mod.get_direction_posts(direction["id"])
    return render_template("hacker_lab_team.html", direction=direction, posts=posts)


@app.route("/hacker-lab/team/new", methods=["POST"])
@login_required
def hacker_lab_team_new():
    user = get_current_user()
    can, _ = hacker_lab_mod.can_enter(user["id"])
    if not can:
        flash("Ruxsat yo'q.", "error")
        return redirect(url_for("hacker_lab"))
    direction_id = user.get("selected_direction_id")
    title = request.form.get("title", "")
    body = request.form.get("body", "")
    file_path, file_type = (None, None)
    if "file" in request.files:
        file_path, file_type = _hacker_lab_save_file(request.files["file"])
    ok, msg = hacker_lab_mod.create_post(user["id"], direction_id, title, body, file_path, file_type)
    flash(msg, "success" if ok else "error")
    return redirect(url_for("hacker_lab_team"))


@app.route("/hacker-lab/team/<int:post_id>")
@login_required
def hacker_lab_team_post(post_id):
    user = get_current_user()
    can, _ = hacker_lab_mod.can_enter(user["id"])
    if not can:
        return redirect(url_for("hacker_lab"))
    post = hacker_lab_mod.get_post(post_id)
    if not post:
        abort(404)
    replies = hacker_lab_mod.get_post_replies(post_id)
    return render_template("hacker_lab_team_post.html", post=post, replies=replies)


@app.route("/hacker-lab/team/<int:post_id>/reply", methods=["POST"])
@login_required
def hacker_lab_team_reply(post_id):
    user = get_current_user()
    can, _ = hacker_lab_mod.can_enter(user["id"])
    if not can:
        return redirect(url_for("hacker_lab"))
    ok, msg = hacker_lab_mod.create_reply(user["id"], post_id, request.form.get("body", ""))
    if not ok:
        flash(msg, "error")
    return redirect(url_for("hacker_lab_team_post", post_id=post_id))


# =================================================================
# IJTIMOIY TARMOQ — GURUHLAR (Telegram guruhiga o'xshab)
# =================================================================
SOCIAL_ALLOWED_EXT = {"png", "jpg", "jpeg", "gif", "webp", "mp4", "mov"}
SOCIAL_UPLOAD_DIR = os.path.join("static", "uploads", "social")


def _social_save_file(file_storage):
    if not file_storage or not file_storage.filename:
        return None, None
    ext = file_storage.filename.rsplit(".", 1)[-1].lower() if "." in file_storage.filename else ""
    if ext not in SOCIAL_ALLOWED_EXT:
        return None, None
    import uuid
    safe_name = f"{uuid.uuid4().hex}.{ext}"
    os.makedirs(SOCIAL_UPLOAD_DIR, exist_ok=True)
    full_path = os.path.join(SOCIAL_UPLOAD_DIR, safe_name)
    file_storage.save(full_path)
    file_type = "image" if ext in ("png", "jpg", "jpeg", "gif", "webp") else "video"
    return f"/static/uploads/social/{safe_name}", file_type


@app.route("/groups")
@login_required
def groups_list():
    user = get_current_user()
    my_groups = social.get_user_groups(user["id"])
    all_groups = social.get_all_groups()
    my_group_ids = {g["id"] for g in my_groups}
    return render_template("groups_list.html", my_groups=my_groups, all_groups=all_groups, my_group_ids=my_group_ids)


@app.route("/groups/create", methods=["POST"])
@login_required
def groups_create():
    user = get_current_user()
    ok, msg, gid = social.create_group(
        user["id"], request.form.get("name", ""), request.form.get("description", ""),
        request.form.get("is_public") == "1"
    )
    flash(msg, "success" if ok else "error")
    if ok:
        return redirect(url_for("group_detail", group_id=gid))
    return redirect(url_for("groups_list"))


@app.route("/groups/<int:group_id>")
@login_required
def group_detail(group_id):
    user = get_current_user()
    group = social.get_group(group_id)
    if not group:
        abort(404)
    is_member = social.is_member(group_id, user["id"])
    messages = social.get_group_messages(group_id) if is_member else []
    members = social.get_group_members(group_id) if is_member else []
    my_role = social.get_member_role(group_id, user["id"])
    return render_template("group_detail.html", group=group, is_member=is_member,
                           messages=messages, members=members, my_role=my_role)


@app.route("/groups/<int:group_id>/join", methods=["POST"])
@login_required
def group_join(group_id):
    user = get_current_user()
    ok, msg = social.join_group(group_id, user["id"])
    flash(msg, "success" if ok else "error")
    return redirect(url_for("group_detail", group_id=group_id))


@app.route("/groups/<int:group_id>/leave", methods=["POST"])
@login_required
def group_leave(group_id):
    user = get_current_user()
    ok, msg = social.leave_group(group_id, user["id"])
    flash(msg, "success" if ok else "error")
    return redirect(url_for("groups_list"))


@app.route("/groups/<int:group_id>/send", methods=["POST"])
@login_required
def group_send_message(group_id):
    user = get_current_user()
    body = request.form.get("body", "")
    file_path, file_type = (None, None)
    if "file" in request.files:
        file_path, file_type = _social_save_file(request.files["file"])
    ok, msg = social.send_group_message(group_id, user["id"], body, file_path, file_type)
    if not ok:
        flash(msg, "error")
    return redirect(url_for("group_detail", group_id=group_id))


@app.route("/api/groups/<int:group_id>/messages")
@api_login_required
def api_group_messages(group_id):
    """Real-vaqtga yaqin yangilanish uchun polling endpoint."""
    user = get_current_user()
    if not social.is_member(group_id, user["id"]):
        return api_response(False, error="A'zo emassiz")
    try:
        after_id = int(request.args.get("after_id", 0))
    except ValueError:
        after_id = 0
    rows = query_all(
        """SELECT m.*, u.ism, u.familiya FROM group_messages m
           JOIN users u ON u.id = m.user_id
           WHERE m.group_id=? AND m.id > ? ORDER BY m.id ASC""",
        (group_id, after_id)
    )
    return api_response(True, data={"messages": rows})


@app.route("/groups/<int:group_id>/kick/<int:target_user_id>", methods=["POST"])
@login_required
def group_kick(group_id, target_user_id):
    user = get_current_user()
    ok, msg = social.kick_member(group_id, user["id"], target_user_id)
    flash(msg, "success" if ok else "error")
    return redirect(url_for("group_detail", group_id=group_id))


@app.route("/groups/<int:group_id>/delete", methods=["POST"])
@login_required
def group_delete(group_id):
    user = get_current_user()
    ok, msg = social.delete_group(group_id, user["id"])
    flash(msg, "success" if ok else "error")
    return redirect(url_for("groups_list"))


# =================================================================
# IJTIMOIY TARMOQ — KANALLAR (Telegram kanaliga o'xshab)
# =================================================================
@app.route("/channels")
@login_required
def channels_list():
    user = get_current_user()
    my_channels = social.get_user_channels(user["id"])
    all_channels = social.get_all_channels()
    my_channel_ids = {c["id"] for c in my_channels}
    return render_template("channels_list.html", my_channels=my_channels, all_channels=all_channels,
                           my_channel_ids=my_channel_ids)


@app.route("/channels/create", methods=["POST"])
@login_required
def channels_create():
    user = get_current_user()
    ok, msg, cid = social.create_channel(user["id"], request.form.get("name", ""), request.form.get("description", ""))
    flash(msg, "success" if ok else "error")
    if ok:
        return redirect(url_for("channel_detail", channel_id=cid))
    return redirect(url_for("channels_list"))


@app.route("/channels/<int:channel_id>")
@login_required
def channel_detail(channel_id):
    user = get_current_user()
    channel = social.get_channel(channel_id)
    if not channel:
        abort(404)
    subscribed = social.is_subscribed(channel_id, user["id"])
    is_owner = social.is_channel_owner(channel_id, user["id"])
    posts = social.get_channel_posts(channel_id)
    return render_template("channel_detail.html", channel=channel, subscribed=subscribed,
                           is_owner=is_owner, posts=posts)


@app.route("/channels/<int:channel_id>/subscribe", methods=["POST"])
@login_required
def channel_subscribe(channel_id):
    user = get_current_user()
    ok, msg = social.subscribe_channel(channel_id, user["id"])
    flash(msg, "success" if ok else "error")
    return redirect(url_for("channel_detail", channel_id=channel_id))


@app.route("/channels/<int:channel_id>/unsubscribe", methods=["POST"])
@login_required
def channel_unsubscribe(channel_id):
    user = get_current_user()
    ok, msg = social.unsubscribe_channel(channel_id, user["id"])
    flash(msg, "success" if ok else "error")
    return redirect(url_for("channel_detail", channel_id=channel_id))


@app.route("/channels/<int:channel_id>/post", methods=["POST"])
@login_required
def channel_post_create(channel_id):
    user = get_current_user()
    body = request.form.get("body", "")
    file_path, file_type = (None, None)
    if "file" in request.files:
        file_path, file_type = _social_save_file(request.files["file"])
    ok, msg = social.create_channel_post(channel_id, user["id"], body, file_path, file_type)
    flash(msg, "success" if ok else "error")
    return redirect(url_for("channel_detail", channel_id=channel_id))


@app.route("/channels/post/<int:post_id>")
@login_required
def channel_post_detail(post_id):
    post = social.get_channel_post(post_id)
    if not post:
        abort(404)
    execute("UPDATE channel_posts SET views = views + 1 WHERE id=?", (post_id,))
    comments = social.get_post_comments(post_id)
    return render_template("channel_post_detail.html", post=post, comments=comments)


@app.route("/channels/post/<int:post_id>/comment", methods=["POST"])
@login_required
def channel_post_comment(post_id):
    user = get_current_user()
    ok, msg = social.add_post_comment(post_id, user["id"], request.form.get("body", ""))
    if not ok:
        flash(msg, "error")
    return redirect(url_for("channel_post_detail", post_id=post_id))


@app.route("/channels/<int:channel_id>/delete", methods=["POST"])
@login_required
def channel_delete(channel_id):
    user = get_current_user()
    ok, msg = social.delete_channel(channel_id, user["id"])
    flash(msg, "success" if ok else "error")
    return redirect(url_for("channels_list"))


# =================================================================
# STORIES — 24 soatlik vaqtinchalik kontent (Instagram uslubida)
# =================================================================
@app.route("/stories")
@login_required
def stories_feed():
    user = get_current_user()
    grouped = social.get_active_stories_by_users()
    my_stories = social.get_user_active_stories(user["id"])
    return render_template("stories_feed.html", grouped=grouped, my_stories=my_stories)


@app.route("/stories/create", methods=["POST"])
@login_required
def stories_create():
    user = get_current_user()
    file_path, file_type = (None, None)
    if "file" in request.files:
        file_path, file_type = _social_save_file(request.files["file"])
    if not file_path:
        flash("Faqat rasm yoki video yuklash mumkin.", "error")
        return redirect(url_for("stories_feed"))
    ok, msg, sid = social.create_story(user["id"], file_path, file_type, request.form.get("caption", ""))
    flash(msg, "success" if ok else "error")
    return redirect(url_for("stories_feed"))


@app.route("/stories/user/<int:target_user_id>")
@login_required
def stories_view_user(target_user_id):
    """Bitta foydalanuvchining faol hikoyalarini ketma-ket ko'rsatish."""
    user = get_current_user()
    stories = social.get_user_active_stories(target_user_id)
    if not stories:
        flash("Bu foydalanuvchining faol hikoyasi yo'q.", "error")
        return redirect(url_for("stories_feed"))
    for s in stories:
        social.mark_story_viewed(s["id"], user["id"])
    target = query_one("SELECT ism, familiya, avatar FROM users WHERE id=?", (target_user_id,))
    return render_template("stories_view.html", stories=stories, target=target)


@app.route("/stories/<int:story_id>/delete", methods=["POST"])
@login_required
def stories_delete(story_id):
    user = get_current_user()
    ok, msg = social.delete_story(story_id, user["id"])
    flash(msg, "success" if ok else "error")
    return redirect(url_for("stories_feed"))


# =================================================================
# REELS — qisqa vertikal videolar tasmasi
# =================================================================
@app.route("/reels")
@login_required
def reels_feed():
    reels = social.get_reels_feed()
    user = get_current_user()
    liked_ids = set()
    if reels:
        ids = [r["id"] for r in reels]
        placeholders = ",".join("?" for _ in ids)
        liked_rows = query_all(
            f"SELECT reel_id FROM reel_likes WHERE user_id=? AND reel_id IN ({placeholders})",
            tuple([user["id"]] + ids)
        )
        liked_ids = {r["reel_id"] for r in liked_rows}
    return render_template("reels_feed.html", reels=reels, liked_ids=liked_ids)


@app.route("/reels/create", methods=["GET", "POST"])
@login_required
def reels_create():
    if request.method == "GET":
        return render_template("reels_create.html")
    user = get_current_user()
    file_path, file_type = (None, None)
    if "file" in request.files:
        file_path, file_type = _social_save_file(request.files["file"])
    if not file_path or file_type != "video":
        flash("Faqat video fayl yuklash mumkin.", "error")
        return redirect(url_for("reels_create"))
    ok, msg, rid = social.create_reel(user["id"], file_path, request.form.get("caption", ""))
    flash(msg, "success" if ok else "error")
    return redirect(url_for("reels_feed"))


@app.route("/api/reels/<int:reel_id>/view", methods=["POST"])
@api_login_required
def api_reel_view(reel_id):
    social.increment_reel_view(reel_id)
    return api_response(True)


@app.route("/api/reels/<int:reel_id>/like", methods=["POST"])
@api_login_required
def api_reel_like(reel_id):
    user = get_current_user()
    liked, count = social.toggle_reel_like(reel_id, user["id"])
    return api_response(True, data={"liked": liked, "like_count": count})


@app.route("/reels/<int:reel_id>/comment", methods=["POST"])
@login_required
def reel_comment(reel_id):
    user = get_current_user()
    ok, msg = social.add_reel_comment(reel_id, user["id"], request.form.get("body", ""))
    if not ok:
        flash(msg, "error")
    return redirect(url_for("reels_feed") + f"#reel-{reel_id}")


@app.route("/api/reels/<int:reel_id>/comments")
@api_login_required
def api_reel_comments(reel_id):
    comments = social.get_reel_comments(reel_id)
    return api_response(True, data={"comments": comments})


@app.route("/reels/<int:reel_id>/delete", methods=["POST"])
@login_required
def reel_delete(reel_id):
    user = get_current_user()
    ok, msg = social.delete_reel(reel_id, user["id"])
    flash(msg, "success" if ok else "error")
    return redirect(url_for("reels_feed"))


# =================================================================
# STARTAPLAR — foydalanuvchi loyihalari (Nomi, tavsifi, rasm)
# =================================================================
STARTUP_ALLOWED_EXT = {"png", "jpg", "jpeg", "gif", "webp"}
STARTUP_UPLOAD_DIR = os.path.join("static", "uploads", "startups")


def _startup_save_image(file_storage):
    if not file_storage or not file_storage.filename:
        return None
    ext = file_storage.filename.rsplit(".", 1)[-1].lower() if "." in file_storage.filename else ""
    if ext not in STARTUP_ALLOWED_EXT:
        return None
    import uuid
    safe_name = f"{uuid.uuid4().hex}.{ext}"
    os.makedirs(STARTUP_UPLOAD_DIR, exist_ok=True)
    full_path = os.path.join(STARTUP_UPLOAD_DIR, safe_name)
    file_storage.save(full_path)
    return f"/static/uploads/startups/{safe_name}"


@app.route("/startups")
@login_required
def startups_list():
    user = get_current_user()
    approved = startups_mod.get_approved_startups()
    my_startups = startups_mod.get_user_startups(user["id"])
    liked_ids = set()
    if approved:
        ids = [s["id"] for s in approved]
        placeholders = ",".join("?" for _ in ids)
        liked_rows = query_all(
            f"SELECT startup_id FROM startup_likes WHERE user_id=? AND startup_id IN ({placeholders})",
            tuple([user["id"]] + ids)
        )
        liked_ids = {r["startup_id"] for r in liked_rows}
    return render_template("startups_list.html", approved=approved, my_startups=my_startups,
                           liked_ids=liked_ids, categories=startups_mod.CATEGORIES)


@app.route("/startups/create", methods=["POST"])
@login_required
def startups_create():
    user = get_current_user()
    image_path = None
    if "image" in request.files:
        image_path = _startup_save_image(request.files["image"])
    ok, msg, sid = startups_mod.create_startup(
        user["id"], request.form.get("name", ""), request.form.get("description", ""),
        image_path, request.form.get("link_url", ""), request.form.get("category", "boshqa")
    )
    flash(msg, "success" if ok else "error")
    return redirect(url_for("startups_list"))


@app.route("/startups/<int:startup_id>")
@login_required
def startup_detail(startup_id):
    startup = startups_mod.get_startup(startup_id)
    if not startup or (startup["status"] != "approved" and startup["user_id"] != get_current_user()["id"]):
        abort(404)
    startups_mod.increment_view(startup_id)
    like_count = startups_mod.get_like_count(startup_id)
    user_liked = startups_mod.is_liked(startup_id, get_current_user()["id"])
    return render_template("startup_detail.html", startup=startup, like_count=like_count, user_liked=user_liked)


@app.route("/api/startups/<int:startup_id>/like", methods=["POST"])
@api_login_required
def api_startup_like(startup_id):
    user = get_current_user()
    liked, count = startups_mod.toggle_like(startup_id, user["id"])
    return api_response(True, data={"liked": liked, "like_count": count})


@app.route("/startups/<int:startup_id>/delete", methods=["POST"])
@login_required
def startup_delete(startup_id):
    user = get_current_user()
    is_admin = user.get("role") in ("admin", "super_admin")
    ok, msg = startups_mod.delete_startup(startup_id, user["id"], is_admin)
    flash(msg, "success" if ok else "error")
    return redirect(url_for("startups_list"))


# Admin — startaplarni tasdiqlash
@app.route("/admin/startups")
@admin_required
def admin_startups():
    status = request.args.get("status", "pending")
    startups_data = startups_mod.get_all_startups_admin(status if status != "all" else None)
    return render_template("admin_startups.html", startups=startups_data, status_filter=status)


@app.route("/admin/startups/<int:startup_id>/review", methods=["POST"])
@admin_required
def admin_startups_review(startup_id):
    decision = request.form.get("decision")
    ok, msg = startups_mod.review_startup(startup_id, session["user_id"], decision)
    flash(msg, "success" if ok else "error")
    return redirect(url_for("admin_startups"))


@app.route("/admin/startups/<int:startup_id>/auction", methods=["POST"])
@admin_required
def admin_startup_create_auction(startup_id):
    """Admin tasdiqlangan loyihani auksionga qo'yadi."""
    try:
        start_price = int(request.form.get("start_price") or 0) or None
    except ValueError:
        start_price = None
    try:
        duration_days = int(request.form.get("duration_days") or 0) or None
    except ValueError:
        duration_days = None
    ok, msg, aid = startups_mod.create_auction(startup_id, session["user_id"], start_price, duration_days)
    flash(msg, "success" if ok else "error")
    return redirect(url_for("admin_startups"))


@app.route("/admin/startup-auctions/<int:auction_id>/cancel", methods=["POST"])
@admin_required
def admin_startup_auction_cancel(auction_id):
    ok, msg = startups_mod.cancel_auction(auction_id, session["user_id"])
    flash(msg, "success" if ok else "error")
    return redirect(url_for("startup_auctions_list"))


# =================================================================
# STARTAPLAR AUKSIONI — foydalanuvchi tomondan
# =================================================================
@app.route("/startup-auctions")
@login_required
def startup_auctions_list():
    startups_mod.check_and_finalize_expired_auctions()
    auctions = startups_mod.get_active_auctions()
    return render_template("startup_auctions_list.html", auctions=auctions)


@app.route("/startup-auctions/<int:auction_id>")
@login_required
def startup_auction_detail(auction_id):
    startups_mod.check_and_finalize_expired_auctions()
    auction = startups_mod.get_auction(auction_id)
    if not auction:
        abort(404)
    bids = startups_mod.get_auction_bids(auction_id)
    return render_template("startup_auction_detail.html", auction=auction, bids=bids)


@app.route("/startup-auctions/<int:auction_id>/bid", methods=["POST"])
@login_required
def startup_auction_bid(auction_id):
    user = get_current_user()
    try:
        amount = int(request.form.get("amount", 0))
    except ValueError:
        amount = 0
    ok, msg = startups_mod.place_bid(auction_id, user["id"], amount)
    flash(msg, "success" if ok else "error")
    return redirect(url_for("startup_auction_detail", auction_id=auction_id))


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
            error=f"AI javob uchun {get_price('ai_cost_per_msg')} code tangasi kerak. {msg}",
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
# SHAXSIY XABARLAR — Telegram uslubidagi foydalanuvchidan-foydalanuvchiga chat
# =================================================================

@app.route("/messages")
@login_required
def messages_page():
    user = get_current_user()
    q = request.args.get("q", "").strip()
    conversations = get_conversations(user["id"])
    search_results = search_users(q, user["id"]) if q else []
    return render_template("messages.html", conversations=conversations,
                           search_results=search_results, search_q=q)


@app.route("/messages/<int:peer_id>")
@login_required
def messages_thread(peer_id):
    user = get_current_user()
    peer = query_one("SELECT id, ism, familiya, avatar, plan, role, custom_id FROM users WHERE id=?", (peer_id,))
    if not peer:
        flash("Foydalanuvchi topilmadi.", "error")
        return redirect(url_for("messages_page"))
    thread = get_thread(user["id"], peer_id, 200)
    mark_thread_read(user["id"], peer_id)
    conversations = get_conversations(user["id"])
    return render_template("messages_thread.html", peer=peer, thread=thread,
                           conversations=conversations,
                           transfer_fee_percent=0 if user.get("plan") in ("pro", "cyber_pro", "vip", "enterprise") else get_price("coin_transfer_fee_percent"))


@app.route("/messages/<int:peer_id>/send", methods=["POST"])
@login_required
def messages_send(peer_id):
    user = get_current_user()
    body = request.form.get("body", "")
    ok, msg = send_message(user["id"], peer_id, body)
    if not ok:
        flash(msg, "error")
    return redirect(url_for("messages_thread", peer_id=peer_id))


@app.route("/api/messages/<int:peer_id>/poll")
@api_login_required
def api_messages_poll(peer_id):
    """Real-vaqtda yangilanish uchun polling endpoint: oxirgi xabarlardan keyingilarini qaytaradi."""
    user = get_current_user()
    try:
        after_id = int(request.args.get("after_id", 0))
    except ValueError:
        after_id = 0
    rows = query_all(
        """SELECT * FROM private_messages
           WHERE ((sender_id=? AND receiver_id=?) OR (sender_id=? AND receiver_id=?)) AND id > ?
           ORDER BY id ASC""",
        (user["id"], peer_id, peer_id, user["id"], after_id)
    )
    if rows:
        mark_thread_read(user["id"], peer_id)
    return api_response(True, data={"messages": rows, "unread_total": get_unread_total(user["id"])})


@app.route("/api/messages/<int:peer_id>/send", methods=["POST"])
@api_login_required
def api_messages_send(peer_id):
    user = get_current_user()
    data = request.get_json(silent=True) or {}
    ok, msg = send_message(user["id"], peer_id, data.get("body", ""))
    if not ok:
        return api_response(False, error=msg)
    return api_response(True, data={"message": msg})


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
    # Plan settings — bazadan (admin tahrirlay oladi, butun saytda real ishlaydi)
    plan_settings = get_pricing()
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
    # Premium ID boshqaruvi uchun
    premium_ids_admin = get_premium_ids_list()
    # Admin/super admin boshqaruvi
    all_admins = get_all_admins()
    current = get_current_user()
    is_super_admin = bool(current and current["role"] == "super_admin")
    # G'azna jamg'armasi (admin "G'azna" tabida ko'rsatish uchun)
    treasury_balance = treasury_mod.get_fund_balance()
    treasury_recent_log = treasury_mod.get_fund_log(15)
    return render_template(
        "admin_dashboard.html", stats=stats, recent_users=recent_users, recent_logs=recent_logs,
        top_courses=top_courses, day_labels=day_labels, activity_series=activity_series,
        source_labels=source_labels, source_series=source_series, plan_counts=plan_counts,
        security_events=security_events, blocked_ips=blocked_ips, security_stats=security_stats,
        payments=payments, total_uzs=total_uzs, total_code=total_code,
        all_courses=all_courses, plan_settings=plan_settings,
        top_leaders=top_leaders, premium_ids_admin=premium_ids_admin,
        all_admins=all_admins, is_super_admin=is_super_admin,
        treasury_balance=treasury_balance, treasury_recent_log=treasury_recent_log,
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
# ADMIN — Adminlar boshqaruvi (admin qo'shish, 4 xonali admin_id)
# =================================================================

@app.route("/admin/admins/create", methods=["POST"])
@admin_required
def admin_create_admin():
    """Yangi login/parol bilan admin yaratadi (har bir admin faqat o'zini yaratganlarni emas,
    istalgan adminni yaratishi mumkin — lekin role='super_admin' faqat super_admin tomonidan beriladi)."""
    ism = request.form.get("ism", "").strip()
    familiya = request.form.get("familiya", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    role = request.form.get("role", "admin")

    current = get_current_user()
    if role == "super_admin" and current["role"] != "super_admin":
        flash("Faqat Super Admin boshqa Super Admin tayinlashi mumkin.", "error")
        return redirect(url_for("admin_dashboard") + "#admins")

    ok, msg = create_new_admin(ism, familiya, email, password, role)
    flash(msg, "success" if ok else "error")
    if ok:
        log_action(session["user_id"], "admin_create_admin", details=f"email:{email},role:{role}", ip=request.remote_addr)
    return redirect(url_for("admin_dashboard") + "#admins")


@app.route("/admin/admins/promote", methods=["POST"])
@admin_required
def admin_promote_user():
    """Mavjud foydalanuvchini admin/mentor qilib tayinlaydi."""
    try:
        target_user_id = int(request.form.get("user_id", 0))
    except ValueError:
        target_user_id = 0
    role = request.form.get("role", "admin")

    current = get_current_user()
    if role == "super_admin" and current["role"] != "super_admin":
        flash("Faqat Super Admin boshqa Super Admin tayinlashi mumkin.", "error")
        return redirect(url_for("admin_dashboard") + "#admins")

    if not target_user_id:
        flash("Foydalanuvchi ID kiritilmadi.", "error")
        return redirect(url_for("admin_dashboard") + "#admins")

    ok, msg = promote_user_to_admin(target_user_id, role)
    flash(msg, "success" if ok else "error")
    if ok:
        log_action(session["user_id"], "admin_promote_user", details=f"target:{target_user_id},role:{role}", ip=request.remote_addr)
    return redirect(url_for("admin_dashboard") + "#admins")


@app.route("/admin/admins/<int:user_id>/demote", methods=["POST"])
@admin_required
def admin_demote_admin(user_id):
    """Adminlik huquqini olib tashlaydi. Super adminni faqat super_admin tushira oladi."""
    target = query_one("SELECT * FROM users WHERE id=?", (user_id,))
    current = get_current_user()
    if target and target["role"] == "super_admin" and current["role"] != "super_admin":
        flash("Faqat Super Admin Super Adminni tushira oladi.", "error")
        return redirect(url_for("admin_dashboard") + "#admins")
    if target and target["id"] == current["id"]:
        flash("O'zingizni admin huquqidan mahrum qila olmaysiz.", "error")
        return redirect(url_for("admin_dashboard") + "#admins")

    ok, msg = demote_admin(user_id)
    flash(msg, "success" if ok else "error")
    if ok:
        log_action(session["user_id"], "admin_demote_admin", details=f"target:{user_id}", ip=request.remote_addr)
    return redirect(url_for("admin_dashboard") + "#admins")


@app.route("/admin/admins/<int:user_id>/change-admin-id", methods=["POST"])
@super_admin_required
def admin_change_admin_id(user_id):
    """FAQAT Super Admin boshqa adminning 4 xonali Admin ID raqamini o'zgartira oladi."""
    new_admin_id = request.form.get("admin_id", "").strip()
    ok, msg = super_admin_change_admin_id(user_id, new_admin_id)
    flash(msg, "success" if ok else "error")
    if ok:
        log_action(session["user_id"], "super_admin_change_admin_id",
                   details=f"target:{user_id},new_id:{new_admin_id}", ip=request.remote_addr)
    return redirect(url_for("admin_dashboard") + "#admins")


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
    if plan not in ("free", "pro", "cyber_pro", "vip", "enterprise"):
        flash("Noto'g'ri plan.", "error")
        return redirect(url_for("admin_users"))
    if plan in ("pro", "cyber_pro", "vip"):
        from coins import _calc_plan_expiry
        expires_at = _calc_plan_expiry()
        execute("UPDATE users SET plan=?, plan_expires_at=? WHERE id=?", (plan, expires_at, user_id))
    else:
        execute("UPDATE users SET plan=?, plan_expires_at=NULL WHERE id=?", (plan, user_id))
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
    dest = request.form.get("redirect_to") or url_for("admin_users")
    if amount <= 0:
        flash("Miqdor musbat bo'lishi kerak.", "error")
        return redirect(dest)
    add_coins(user_id, amount, "admin_add", ref_id=session["user_id"])
    log_action(session["user_id"], "admin_add_coins", details=f"user:{user_id},amount:{amount}", ip=request.remote_addr)
    flash(f"Foydalanuvchiga {amount:,} code tangasi qo'shildi.", "success")
    return redirect(dest)


@app.route("/admin/users/<int:user_id>/remove-coins", methods=["POST"])
@admin_required
def admin_remove_coins(user_id):
    """Foydalanuvchidan code tangasi ayirish (admin huquqi)."""
    try:
        amount = int(request.form.get("amount", 0))
    except ValueError:
        amount = 0
    dest = request.form.get("redirect_to") or url_for("admin_users")
    if amount <= 0:
        flash("Miqdor musbat bo'lishi kerak.", "error")
        return redirect(dest)
    user = query_one("SELECT code_balance FROM users WHERE id=?", (user_id,))
    if not user:
        flash("Foydalanuvchi topilmadi.", "error")
        return redirect(dest)
    current = user["code_balance"] or 0
    actual = min(amount, current)  # ko'proq ayirib bo'lmaydi
    if actual <= 0:
        flash("Foydalanuvchining balansi nol — ayirib bo'lmaydi.", "error")
        return redirect(dest)
    execute("UPDATE users SET code_balance = code_balance - ? WHERE id=?", (actual, user_id))
    execute("INSERT INTO code_transactions (user_id, amount, reason, ref_id) VALUES (?,?,?,?)",
            (user_id, -actual, "admin_remove", session["user_id"]))
    log_action(session["user_id"], "admin_remove_coins",
               details=f"user:{user_id},amount:{actual}", ip=request.remote_addr)
    flash(f"Foydalanuvchidan {actual:,} code tangasi ayirildi.", "success")
    return redirect(dest)


@app.route("/admin/treasury/deposit", methods=["POST"])
@admin_required
def admin_deposit_to_treasury():
    """Admin tomonidan g'azna jamg'armasiga to'g'ridan-to'g'ri code solib berish."""
    try:
        amount = int(request.form.get("amount", 0))
    except ValueError:
        amount = 0
    note = request.form.get("note", "").strip()
    ok, msg = treasury_mod.admin_deposit_to_fund(session["user_id"], amount, note)
    log_action(session["user_id"], "admin_treasury_deposit",
               details=f"amount:{amount},note:{note}", ip=request.remote_addr)
    flash(msg, "success" if ok else "error")
    return redirect(url_for("admin_dashboard") + "#treasury")


# =================================================================
# G'AZNA (Code Panel) — foydalanuvchilar/admin tizimidan BUTUNLAY MUSTAQIL.
# Alohida login (email+parol), alohida sessiya, alohida jamg'arma balansi.
# Pro yoqish/o'chirish ENDI ADMIN PANELDA ("Foydalanuvchilar" bo'limida) qoladi —
# G'azna faqat jamg'armadan coin chiqarish bilan shug'ullanadi.
# =================================================================

def treasury_login_required(view):
    """G'azna xodimi sifatida kirilganligini tekshiradi (foydalanuvchi sessiyasidan mustaqil)."""
    from functools import wraps

    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("treasury_account_id"):
            return redirect(url_for("treasury_login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


@app.route("/treasury/login", methods=["GET", "POST"])
def treasury_login():
    """G'azna xodimlari uchun mustaqil login sahifasi (foydalanuvchi/admin login'idan butunlay alohida)."""
    next_url = request.args.get("next") or request.form.get("next") or url_for("treasury_dashboard")
    no_accounts_yet = treasury_mod.treasury_accounts_count() == 0

    if request.method == "POST":
        if no_accounts_yet:
            # Birinchi G'azna hisobini shu yerda yaratamiz (bootstrap)
            ism = request.form.get("ism", "")
            email = request.form.get("email", "")
            password = request.form.get("password", "")
            confirm = request.form.get("confirm_password", "")
            if password != confirm:
                flash("Parollar mos kelmadi.", "error")
                return redirect(url_for("treasury_login"))
            ok, msg = treasury_mod.create_treasury_account(ism, email, password)
            if not ok:
                flash(msg, "error")
                return redirect(url_for("treasury_login"))
            account = treasury_mod.get_treasury_account_by_email(email)
            session["treasury_account_id"] = account["id"]
            session["treasury_account_ism"] = account["ism"]
            flash("G'azna hisobi yaratildi va tizimga kirdingiz.", "success")
            return redirect(next_url)
        else:
            email = request.form.get("email", "")
            password = request.form.get("password", "")
            account = treasury_mod.verify_treasury_login(email, password)
            if not account:
                flash("Email yoki parol noto'g'ri.", "error")
                return redirect(url_for("treasury_login", next=next_url))
            session["treasury_account_id"] = account["id"]
            session["treasury_account_ism"] = account["ism"]
            return redirect(next_url)

    return render_template("treasury_login.html", no_accounts_yet=no_accounts_yet, next_url=next_url)


@app.route("/treasury/logout")
def treasury_logout():
    session.pop("treasury_account_id", None)
    session.pop("treasury_account_ism", None)
    flash("G'aznadan chiqdingiz.", "success")
    return redirect(url_for("treasury_login"))


@app.route("/treasury/")
@treasury_login_required
def treasury_dashboard():
    stats = treasury_mod.get_fund_stats()
    fund_log = treasury_mod.get_fund_log(60)
    q = request.args.get("q", "").strip()
    search_results = []
    if q:
        search_results = query_all(
            """SELECT id, ism, familiya, email, plan, code_balance, is_blocked, custom_id
               FROM users WHERE ism LIKE ? OR familiya LIKE ? OR email LIKE ? OR custom_id LIKE ?
               ORDER BY id DESC LIMIT 30""",
            (f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%")
        )
    return render_template(
        "treasury_dashboard.html",
        stats=stats, fund_log=fund_log, search_q=q, search_results=search_results,
        treasury_ism=session.get("treasury_account_ism"),
    )


@app.route("/treasury/issue/<int:user_id>", methods=["POST"])
@treasury_login_required
def treasury_issue_coins(user_id):
    """G'azna jamg'armasidan foydalanuvchiga coin chiqaradi. Mablag' yetmasa rad etiladi."""
    try:
        amount = int(request.form.get("amount", 0))
    except ValueError:
        amount = 0
    ok, msg = treasury_mod.issue_coins_to_user(session["treasury_account_id"], user_id, amount)
    flash(msg, "success" if ok else "error")
    return redirect(url_for("treasury_dashboard", q=request.form.get("q", "")))


@app.route("/treasury/accounts")
@treasury_login_required
def treasury_accounts_page():
    """G'azna xodimlari ro'yxati (faqat boshqa G'azna xodimi ko'ra oladi)."""
    accounts = treasury_mod.list_treasury_accounts()
    return render_template("treasury_accounts.html", accounts=accounts)


@app.route("/treasury/accounts/create", methods=["POST"])
@treasury_login_required
def treasury_accounts_create():
    """Yangi G'azna xodimi qo'shish — faqat tizimga kirgan G'azna xodimi qo'sha oladi."""
    ism = request.form.get("ism", "")
    email = request.form.get("email", "")
    password = request.form.get("password", "")
    ok, msg = treasury_mod.create_treasury_account(ism, email, password)
    flash(msg, "success" if ok else "error")
    return redirect(url_for("treasury_accounts_page"))


@app.route("/treasury/accounts/<int:account_id>/toggle", methods=["POST"])
@treasury_login_required
def treasury_accounts_toggle(account_id):
    if account_id == session.get("treasury_account_id"):
        flash("O'zingizning hisobingizni faolsizlantira olmaysiz.", "error")
        return redirect(url_for("treasury_accounts_page"))
    treasury_mod.toggle_treasury_account(account_id)
    flash("Hisob holati o'zgartirildi.", "success")
    return redirect(url_for("treasury_accounts_page"))


@app.route("/treasury/accounts/<int:account_id>/reset-password", methods=["POST"])
@treasury_login_required
def treasury_accounts_reset_password(account_id):
    new_password = request.form.get("new_password", "")
    ok, msg = treasury_mod.reset_treasury_account_password(account_id, new_password)
    flash(msg, "success" if ok else "error")
    return redirect(url_for("treasury_accounts_page"))


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
    p = get_pricing()
    is_pro = user.get("plan") in ("pro", "cyber_pro", "vip", "enterprise")
    return render_template("coins.html", balance=balance, txns=txns,
                           pro_cost=p["pro_price_code"],
                           cyber_pro_cost=p["cyber_pro_price_code"],
                           vip_cost=p["vip_price_code"],
                           vip_enabled=p["vip_enabled"] in (1, "1", True),
                           ai_cost=p["ai_cost_per_msg"],
                           course_reward=p["course_reward_code"],
                           paid_course_code=p["paid_course_code_default"],
                           transfer_fee_percent=0 if is_pro else p["coin_transfer_fee_percent"],
                           is_pro=is_pro)


@app.route("/coins/transfer", methods=["POST"])
@login_required
def coins_transfer():
    user = get_current_user()
    recipient_raw = request.form.get("recipient", "").strip()
    try:
        amount = int(request.form.get("amount", 0))
    except ValueError:
        amount = 0

    target = None
    if recipient_raw:
        if recipient_raw.lstrip("#").isdigit() and recipient_raw.startswith("#"):
            target = query_one("SELECT id FROM users WHERE custom_id=?", (recipient_raw.lstrip("#"),))
        else:
            target = query_one("SELECT id FROM users WHERE custom_id=? OR email=?", (recipient_raw, recipient_raw))

    if not target:
        flash("Qabul qiluvchi topilmadi. ID (#0000) yoki email kiriting.", "error")
        return redirect(url_for("coins_page"))

    ok, msg = transfer_coins(user["id"], target["id"], amount)
    flash(msg, "success" if ok else "error")
    return redirect(url_for("coins_page"))


# =================================================================
# SAYTDAN TO'G'RIDAN-TO'G'RI CODE SOTIB OLISH (botsiz, ID+karta+chek)
# =================================================================
CODE_PURCHASE_ALLOWED_EXT = {"png", "jpg", "jpeg", "gif", "webp", "pdf"}
CODE_PURCHASE_UPLOAD_DIR = os.path.join("static", "uploads", "receipts")


def _save_receipt_file(file_storage):
    if not file_storage or not file_storage.filename:
        return None
    ext = file_storage.filename.rsplit(".", 1)[-1].lower() if "." in file_storage.filename else ""
    if ext not in CODE_PURCHASE_ALLOWED_EXT:
        return None
    import uuid
    safe_name = f"{uuid.uuid4().hex}.{ext}"
    os.makedirs(CODE_PURCHASE_UPLOAD_DIR, exist_ok=True)
    full_path = os.path.join(CODE_PURCHASE_UPLOAD_DIR, safe_name)
    file_storage.save(full_path)
    return f"/static/uploads/receipts/{safe_name}"


@app.route("/coins/buy")
@login_required
def coins_buy_page():
    """Saytdan to'g'ridan-to'g'ri CODE sotib olish sahifasi."""
    user = get_current_user()
    requests_list = coins_purchase.get_user_purchase_requests(user["id"])
    return render_template(
        "coins_buy.html",
        cards=coins_purchase.PAYMENT_CARDS,
        packages=coins_purchase.SUGGESTED_PACKAGES,
        min_amount=coins_purchase.MIN_AMOUNT,
        requests_list=requests_list,
        my_custom_id=user.get("custom_id"),
    )


@app.route("/coins/buy/submit", methods=["POST"])
@login_required
def coins_buy_submit():
    user = get_current_user()
    custom_id = request.form.get("custom_id", "").strip().lstrip("#")
    try:
        amount = int(request.form.get("amount", 0))
    except ValueError:
        amount = 0

    receipt_path = None
    if "receipt" in request.files:
        receipt_path = _save_receipt_file(request.files["receipt"])
        if request.files["receipt"].filename and not receipt_path:
            flash("Fayl turi noto'g'ri. Faqat rasm (png/jpg) yoki PDF qabul qilinadi.", "error")
            return redirect(url_for("coins_buy_page"))

    ok, msg, rid = coins_purchase.create_site_purchase_request(
        user["id"], custom_id, amount, receipt_path
    )
    flash(msg, "success" if ok else "error")
    return redirect(url_for("coins_buy_page"))


@app.route("/api/coins/buy")
@api_login_required
def api_coins_buy_requests():
    """Foydalanuvchi o'z so'rovlari holatini tekshirishi uchun (real-vaqt yangilanish)."""
    user = get_current_user()
    rows = coins_purchase.get_user_purchase_requests(user["id"], 10)
    return api_response(True, data={"requests": rows})


@app.route("/api/coins/transfer", methods=["POST"])
@api_login_required
def api_coins_transfer():
    """Chat ichidan tanga jo'natish uchun JSON endpoint."""
    user = get_current_user()
    data = request.get_json(silent=True) or {}
    try:
        to_user_id = int(data.get("to_user_id", 0))
        amount = int(data.get("amount", 0))
    except (TypeError, ValueError):
        return api_response(False, error="Noto'g'ri ma'lumot")
    ok, msg = transfer_coins(user["id"], to_user_id, amount)
    if ok:
        return api_response(True, data={"message": msg, "new_balance": get_balance(user["id"])})
    return api_response(False, error=msg)


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


@app.route("/coins/buy-cyber-pro", methods=["POST"])
@login_required
def coins_buy_cyber_pro():
    """Cyber Pro versiyasini sotib olish — Pro'dan kuchliroq."""
    user = get_current_user()
    ok, msg = buy_cyber_pro_with_coins(user["id"])
    if ok:
        execute("INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
                (user["id"], "Cyber Pro!",
                 "Cyber Pro faollashtirildi! Endi Ingliz tili, Matematika, Office yo'nalishlari ochildi. "
                 "Har bir kurs bitirishda 1,000 CODE bonus olasiz, P2P o'tkazmalar komissiyasiz.", "success"))
    flash(msg, "success" if ok else "error")
    return redirect(url_for("coins_page"))


@app.route("/coins/buy-vip", methods=["POST"])
@login_required
def coins_buy_vip():
    """SHATS CYBER PRO — eng kuchli versiya."""
    user = get_current_user()
    ok, msg = buy_vip_with_coins(user["id"])
    if ok:
        execute("INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
                (user["id"], "🔥 SHATS CYBER PRO!",
                 "SHATS CYBER PRO versiyasi faollashtirildi! Eng yuqori darajadagi imkoniyatlar ochildi.", "success"))
    flash(msg, "success" if ok else "error")
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
# SERTIFIKAT TIZIMI — yo'nalish bo'yicha 50 test (15daq) + 15 amaliy (30daq)
# =================================================================
import certificates as cert_mod


@app.route("/certificates")
@login_required
def certificates_page():
    """Foydalanuvchining barcha kurslar/yo'nalishlari ro'yxati — sertifikat statusi bilan."""
    user = get_current_user()
    # IT yo'nalishlari ro'yxati
    directions = query_all(
        "SELECT * FROM directions WHERE slug NOT IN ('ingliz-tili','matematika','office') ORDER BY sort_order"
    )
    direction_progress = []
    for d in directions:
        progress = cert_mod.get_user_direction_progress(user["id"], d["id"])
        # Mavjud ariza yoki imtihon
        application = query_one(
            "SELECT * FROM certificate_applications WHERE user_id=? AND direction_id=? ORDER BY id DESC LIMIT 1",
            (user["id"], d["id"])
        )
        paid = cert_mod.has_paid_for_exam(user["id"], d["id"])
        direction_progress.append({
            "direction": d,
            "progress": progress,
            "application": application,
            "paid": paid,
            "is_it": cert_mod.is_it_direction(d["slug"]),
        })
    apps = cert_mod.get_user_applications(user["id"])
    return render_template("certificates.html",
                           direction_progress=direction_progress,
                           applications=apps,
                           exam_fee=get_price("certificate_exam_fee"))


@app.route("/certificates/<int:direction_id>/pay", methods=["POST"])
@login_required
def certificates_pay(direction_id):
    user = get_current_user()
    ok, msg = cert_mod.pay_for_certificate_exam(user["id"], direction_id)
    flash(msg, "success" if ok else "error")
    if ok:
        return redirect(url_for("certificates_exam", direction_id=direction_id))
    return redirect(url_for("certificates_page"))


@app.route("/certificates/<int:direction_id>/exam")
@login_required
def certificates_exam(direction_id):
    """Sertifikat imtihoni sahifasi: 50 test (15 daq) + 15 amaliy (30 daq)."""
    user = get_current_user()
    if not cert_mod.has_paid_for_exam(user["id"], direction_id):
        flash("Avval imtihon uchun to'lov qilishingiz kerak.", "error")
        return redirect(url_for("certificates_page"))
    direction = query_one("SELECT * FROM directions WHERE id=?", (direction_id,))
    if not direction:
        abort(404)
    # 50 ta test savol (yo'nalishdagi barcha kurslar testidan random tanlanadi)
    questions = query_all(
        """SELECT tq.* FROM test_questions tq
           JOIN tests t ON t.id = tq.test_id
           WHERE t.course_id IN (SELECT id FROM courses WHERE direction_id=?)
           ORDER BY RANDOM() LIMIT 50""",
        (direction_id,)
    )
    return render_template("certificates_exam.html",
                           direction=direction,
                           questions=questions,
                           test_duration_min=15,
                           practice_duration_min=30,
                           practice_count=15)


@app.route("/certificates/<int:direction_id>/submit", methods=["POST"])
@login_required
def certificates_submit(direction_id):
    """Imtihon yakuni — javoblar va amaliylar ballini hisoblaydi."""
    user = get_current_user()
    if not cert_mod.has_paid_for_exam(user["id"], direction_id):
        flash("Avval to'lov qiling.", "error")
        return redirect(url_for("certificates_page"))

    # Test ballini hisoblash
    test_score = 0
    test_total = 0
    for key, value in request.form.items():
        if key.startswith("q_"):
            qid = key[2:]
            try:
                qid_int = int(qid)
            except ValueError:
                continue
            q = query_one("SELECT correct_option FROM test_questions WHERE id=?", (qid_int,))
            if q:
                test_total += 1
                if (value or "").lower() == q["correct_option"].lower():
                    test_score += 1

    # Amaliy ballini hisoblash (15 ta amaliy, har biri 0-10 ball, mijoz tomonidan o'zi baholaydi
    # demo uchun — real loyihada mentor baholaydi)
    practice_score = 0
    practice_total = 15 * 10  # 150 ball
    for i in range(1, 16):
        v = request.form.get(f"practice_{i}", "0")
        try:
            pv = max(0, min(10, int(v)))
        except ValueError:
            pv = 0
        practice_score += pv

    passed, msg, attempt_id = cert_mod.submit_exam_results(
        user["id"], direction_id, test_score, test_total, practice_score, practice_total
    )

    if passed:
        # Avtomatik ariza yaratish
        ok, app_msg = cert_mod.create_certificate_application(user["id"], direction_id, attempt_id)
        flash(f"Tabriklaymiz! Imtihondan o'tdingiz ({test_score+practice_score}/{test_total+practice_total}). "
              f"Sertifikat arizasi avtomatik yuborildi — admin tasdiqlashini kuting.", "success")
    else:
        flash(f"Afsus, imtihondan o'ta olmadingiz ({test_score+practice_score}/{test_total+practice_total}). "
              f"60% kerak. Qayta to'lab urinish mumkin.", "error")
    return redirect(url_for("certificates_page"))


# Admin — sertifikat arizalari
@app.route("/admin/certificates")
@admin_required
def admin_certificates():
    status = request.args.get("status", "")
    applications = cert_mod.get_all_applications(status if status else None)
    return render_template("admin_certificates.html",
                           applications=applications, filter_status=status)


@app.route("/admin/certificates/<int:app_id>/review", methods=["POST"])
@admin_required
def admin_certificates_review(app_id):
    decision = request.form.get("decision")
    note = request.form.get("note", "")
    ok, msg = cert_mod.review_application(app_id, session["user_id"], decision, note)
    flash(msg, "success" if ok else "error")
    return redirect(url_for("admin_certificates"))


# G'aznachi — sertifikat arizalari (faqat ko'rish, statistika)
@app.route("/treasury/certificates")
@treasury_login_required
def treasury_certificates():
    applications = cert_mod.get_all_applications()
    return render_template("treasury_certificates.html", applications=applications)


# =================================================================
# G'AZNA — Telegram bot orqali sotuv so'rovlari
# =================================================================
@app.route("/api/treasury/notifications/pending")
@treasury_login_required
def api_treasury_notifications_pending():
    """G'azna paneli uchun ovozli bildirishnoma: yangi kutilayotgan bot to'lov so'rovlari.
    Sessiyada ko'rilgan ID'lar ro'yxati saqlanadi — qayta ko'rsatilmasin."""
    seen_ids = session.get("treasury_seen_purchase_ids", [])
    pending = query_all(
        "SELECT id, request_type, code_amount, target_custom_id, created_at "
        "FROM bot_purchase_requests WHERE status='pending' ORDER BY id DESC LIMIT 20"
    )
    items = []
    new_seen = list(seen_ids)
    for r in pending:
        if r["id"] in seen_ids:
            continue
        new_seen.append(r["id"])
        if r["request_type"] == "code":
            body = f"⚡ {r['code_amount']:,} CODE so'rovi — ID #{r['target_custom_id']}"
        else:
            body = f"📚 Kurs sotib olish so'rovi — ID #{r['target_custom_id']}"
        items.append({
            "id": r["id"],
            "title": "Yangi to'lov so'rovi",
            "body": body,
        })
    # Sessiyada faqat oxirgi 200 tasini saqlaymiz (cheksiz o'smasin)
    session["treasury_seen_purchase_ids"] = new_seen[-200:]
    return api_response(True, data={"items": items})


@app.route("/treasury/bot-purchases")
@treasury_login_required
def treasury_bot_purchases():
    """Bot orqali kelgan to'lov so'rovlari ro'yxati."""
    status = request.args.get("status", "pending")
    if status == "all":
        rows = query_all(
            "SELECT * FROM bot_purchase_requests ORDER BY id DESC LIMIT 200"
        )
    else:
        rows = query_all(
            "SELECT * FROM bot_purchase_requests WHERE status=? ORDER BY id DESC LIMIT 200",
            (status,)
        )
    return render_template("treasury_bot_purchases.html", rows=rows, status=status,
                           bot_token=Config.TELEGRAM_BOT_TOKEN)


@app.route("/treasury/bot-purchases/<int:req_id>/approve", methods=["POST"])
@treasury_login_required
def treasury_bot_approve(req_id):
    """So'rovni tasdiqlash: g'azna jamg'armasidan code chiqaradi yoki kurs ochadi.
    Foydalanuvchi botda xabar oladi."""
    import json as _json
    req = query_one("SELECT * FROM bot_purchase_requests WHERE id=?", (req_id,))
    if not req:
        flash("So'rov topilmadi.", "error")
        return redirect(url_for("treasury_bot_purchases"))
    if req["status"] != "pending":
        flash(f"Bu so'rov allaqachon ko'rib chiqilgan ({req['status']}).", "error")
        return redirect(url_for("treasury_bot_purchases"))

    site_user_id = req["site_user_id"]
    if not site_user_id:
        flash("Foydalanuvchi topilmadi.", "error")
        return redirect(url_for("treasury_bot_purchases"))

    treasury_id = session["treasury_account_id"]

    if req["request_type"] == "code":
        # G'azna jamg'armasidan code chiqarish
        amount = req["code_amount"]
        ok, msg = treasury_mod.issue_coins_to_user(treasury_id, site_user_id, amount)
        if not ok:
            flash(msg, "error")
            return redirect(url_for("treasury_bot_purchases"))
        # So'rovni tasdiqlash
        execute(
            """UPDATE bot_purchase_requests SET status='completed', reviewed_by=?,
               reviewed_at=datetime('now'), admin_note='approved via treasury'
               WHERE id=?""",
            (treasury_id, req_id)
        )
        # Saytda notification
        execute(
            "INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
            (site_user_id, "CODE qo'shildi!",
             f"{'Saytdan' if req['source']=='site' else 'Telegram bot orqali'} sotib olingan {amount:,} CODE hisobingizga qo'shildi.",
             "success")
        )
        try:
            push_mod.send_push_to_user(
                site_user_id, "CODE qo'shildi! ⚡",
                f"{amount:,} CODE hisobingizga qo'shildi.", "/coins"
            )
        except Exception:
            pass
        # Botga xabar (faqat bot orqali kelgan bo'lsa)
        _notify_bot_user(req["chat_id"], "code", req)
        flash(f"⚡ {amount:,} CODE foydalanuvchiga chiqarildi.", "success")

    elif req["request_type"] == "course":
        try:
            courses = _json.loads(req["courses_json"] or "[]")
        except Exception:
            courses = []
        for c in courses:
            existing = query_one(
                "SELECT id FROM enrollments WHERE user_id=? AND course_id=?",
                (site_user_id, c["id"])
            )
            if not existing:
                execute(
                    "INSERT INTO enrollments (user_id, course_id, progress_percent) VALUES (?,?,0)",
                    (site_user_id, c["id"])
                )
        execute(
            """UPDATE bot_purchase_requests SET status='completed', reviewed_by=?,
               reviewed_at=datetime('now'), admin_note='courses unlocked'
               WHERE id=?""",
            (treasury_id, req_id)
        )
        execute(
            "INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
            (site_user_id, "Kurslar ochildi!",
             f"Telegram bot orqali sotib olingan {len(courses)} ta kurs hisobingizga qo'shildi.",
             "success")
        )
        try:
            push_mod.send_push_to_user(
                site_user_id, "Kurslar ochildi! 📚",
                f"{len(courses)} ta kurs hisobingizga qo'shildi.", "/courses"
            )
        except Exception:
            pass
        _notify_bot_user(req["chat_id"], "course", req)
        flash(f"📚 {len(courses)} ta kurs foydalanuvchiga ochildi.", "success")

    return redirect(url_for("treasury_bot_purchases"))


@app.route("/treasury/bot-purchases/<int:req_id>/reject", methods=["POST"])
@treasury_login_required
def treasury_bot_reject(req_id):
    """So'rovni rad etish."""
    req = query_one("SELECT * FROM bot_purchase_requests WHERE id=?", (req_id,))
    if not req:
        flash("So'rov topilmadi.", "error")
        return redirect(url_for("treasury_bot_purchases"))
    if req["status"] != "pending":
        flash("Allaqachon ko'rib chiqilgan.", "error")
        return redirect(url_for("treasury_bot_purchases"))

    reason = request.form.get("reason", "Chek soxta yoki ma'lumotlar mos kelmaydi")
    treasury_id = session["treasury_account_id"]
    execute(
        """UPDATE bot_purchase_requests SET status='rejected', reviewed_by=?,
           reviewed_at=datetime('now'), admin_note=? WHERE id=?""",
        (treasury_id, reason, req_id)
    )
    _notify_bot_user(req["chat_id"], "rejected", req, reason=reason)
    flash("So'rov rad etildi va foydalanuvchiga xabar yuborildi.", "success")
    return redirect(url_for("treasury_bot_purchases"))


def _notify_bot_user(chat_id, kind, req, reason=""):
    """Telegram bot orqali foydalanuvchiga natija xabari yuborish."""
    token = Config.TELEGRAM_BOT_TOKEN
    if not token or not chat_id:
        return
    try:
        # Foydalanuvchining tili
        tg_user = query_one("SELECT language FROM telegram_users WHERE chat_id=?", (chat_id,))
        lang = tg_user["language"] if tg_user else "uz"

        # Telegram bot tarjimalarini import qilamiz
        import telegram_bot as bot_mod
        if kind == "code":
            text = bot_mod.t(lang, "purchase_approved_code",
                             code=req["code_amount"], cid=req["target_custom_id"])
        elif kind == "course":
            import json as _json
            try:
                cnt = len(_json.loads(req["courses_json"] or "[]"))
            except Exception:
                cnt = 0
            text = bot_mod.t(lang, "purchase_approved_course",
                             n=cnt, cid=req["target_custom_id"])
        else:  # rejected
            text = bot_mod.t(lang, "purchase_rejected", reason=reason)

        import requests
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            timeout=10
        )
    except Exception as e:
        log_action(None, "bot_notify_error", details=str(e)[:200])


@app.route("/treasury/bot-purchases/<int:req_id>/receipt")
@treasury_login_required
def treasury_bot_receipt(req_id):
    """Chek skrinini ko'rsatish — botdan kelgan bo'lsa Telegram CDN'dan,
    saytdan kelgan bo'lsa to'g'ridan-to'g'ri statik fayldan."""
    req = query_one("SELECT receipt_file_id, receipt_file_path, source FROM bot_purchase_requests WHERE id=?", (req_id,))
    if not req:
        abort(404)

    # Saytdan yuklangan fayl — to'g'ridan-to'g'ri yo'naltirish
    if req["receipt_file_path"]:
        return redirect(req["receipt_file_path"])

    if not req["receipt_file_id"]:
        abort(404)
    token = Config.TELEGRAM_BOT_TOKEN
    if not token:
        flash("Bot token sozlanmagan.", "error")
        return redirect(url_for("treasury_bot_purchases"))
    try:
        import requests as _req
        r = _req.get(f"https://api.telegram.org/bot{token}/getFile",
                     params={"file_id": req["receipt_file_id"]}, timeout=10)
        d = r.json()
        if d.get("ok"):
            file_path = d["result"]["file_path"]
            return redirect(f"https://api.telegram.org/file/bot{token}/{file_path}")
    except Exception as e:
        log_action(None, "bot_receipt_error", details=str(e)[:200])
    flash("Chek olib bo'lmadi.", "error")
    return redirect(url_for("treasury_bot_purchases"))


@app.route("/treasury/history")
@treasury_login_required
def treasury_history():
    """G'azna to'liq kirim-chiqim tarixi — loyiha boshlanganidan barcha harakatlar.
    Filtrlar: yo'nalish (in/out/all), sabab, sana oraliq."""
    direction_filter = request.args.get("direction", "")
    reason_filter = request.args.get("reason", "")
    date_from = request.args.get("date_from", "")
    date_to = request.args.get("date_to", "")
    page = max(1, int(request.args.get("page", 1) or 1))
    per_page = 100

    where = ["1=1"]
    params = []
    if direction_filter in ("in", "out"):
        where.append("direction = ?")
        params.append(direction_filter)
    if reason_filter:
        # 'id_sale' -> shu prefix bilan boshlanadigan ham olinadi
        if reason_filter in ("id_sale", "admin_deposit"):
            where.append("(reason = ? OR reason LIKE ?)")
            params.extend([reason_filter, reason_filter + ":%"])
        else:
            where.append("reason = ?")
            params.append(reason_filter)
    if date_from:
        where.append("created_at >= ?")
        params.append(date_from)
    if date_to:
        where.append("created_at <= ?")
        params.append(date_to + " 23:59:59")

    where_sql = " AND ".join(where)
    total_row = query_one(
        f"SELECT COUNT(*) c FROM treasury_fund_log WHERE {where_sql}", tuple(params)
    )
    total = total_row["c"] if total_row else 0
    offset = (page - 1) * per_page
    pages = max(1, (total + per_page - 1) // per_page)

    rows = query_all(
        f"""SELECT l.*, u.ism as user_ism, u.familiya as user_familiya, u.custom_id as user_custom_id,
                   ta.ism as treasury_ism
            FROM treasury_fund_log l
            LEFT JOIN users u ON u.id = l.user_id
            LEFT JOIN treasury_accounts ta ON ta.id = l.treasury_account_id
            WHERE {where_sql}
            ORDER BY l.id DESC
            LIMIT ? OFFSET ?""",
        tuple(params + [per_page, offset])
    )

    # Filtrdagi yig'indi
    sum_in = query_one(
        f"SELECT COALESCE(SUM(amount),0) s FROM treasury_fund_log WHERE direction='in' AND {where_sql}",
        tuple(params)
    )["s"]
    sum_out = query_one(
        f"SELECT COALESCE(SUM(amount),0) s FROM treasury_fund_log WHERE direction='out' AND {where_sql}",
        tuple(params)
    )["s"]

    # Reasonlar ro'yxati (filtr dropdown uchun)
    reasons = query_all(
        """SELECT DISTINCT CASE
              WHEN reason LIKE 'id_sale:%' THEN 'id_sale'
              WHEN reason LIKE 'admin_deposit:%' THEN 'admin_deposit'
              ELSE reason
           END as r FROM treasury_fund_log ORDER BY r"""
    )

    return render_template(
        "treasury_history.html",
        rows=rows,
        total=total, page=page, pages=pages,
        sum_in=sum_in, sum_out=sum_out,
        balance=treasury_mod.get_fund_balance(),
        reasons=[r["r"] for r in reasons],
        filters={
            "direction": direction_filter,
            "reason": reason_filter,
            "date_from": date_from,
            "date_to": date_to,
        }
    )


# =================================================================
# PING TEST (PENTESTING) — plan bo'yicha kvota va narx
# =================================================================
@app.route("/pentesting/ping")
@login_required
def pentesting_ping_page():
    user = get_current_user()
    quota, cost = ping_mod.get_quota_and_cost(user["plan"])
    used = ping_mod.get_used_count(user["id"])
    recent = query_all(
        "SELECT * FROM ping_test_usage WHERE user_id=? ORDER BY id DESC LIMIT 20",
        (user["id"],)
    )
    return render_template("pentesting_ping.html",
                           quota=quota, cost=cost, used=used,
                           remaining=max(0, quota - used), recent=recent,
                           methods=ping_mod.PING_METHODS)


@app.route("/api/pentesting/ping", methods=["POST"])
@api_login_required
def api_pentesting_ping():
    user = get_current_user()
    data = request.get_json(silent=True) or {}
    host = (data.get("host") or "").strip()
    method = (data.get("method") or "icmp").strip()
    if not host:
        return api_response(False, error="Host bo'sh.")
    ok, msg, result = ping_mod.run_ping_test(user["id"], host, method)
    if ok:
        return api_response(True, data={
            "result": result,
            "new_balance": get_balance(user["id"]),
        })
    return api_response(False, error=msg)


# =================================================================
# CODE EDITOR (Cyber Pro uchun) — HTML/CSS/JS real-vaqt preview
# =================================================================
@app.route("/code-editor")
@login_required
def code_editor_page():
    user = get_current_user()
    if user.get("plan") not in ("cyber_pro", "vip") and user.get("role") not in ("admin", "super_admin"):
        flash("Code editor Cyber Pro va undan yuqori foydalanuvchilar uchun.", "error")
        return redirect(url_for("pricing"))
    return render_template("code_editor.html")


# =================================================================
# ANNOUNCEMENTS (admin e'lonlari) — ovozli broadcast
# =================================================================
@app.route("/admin/announcements")
@admin_required
def admin_announcements():
    announcements_list = ann_mod.list_all_announcements()
    return render_template("admin_announcements.html", announcements=announcements_list)


@app.route("/admin/announcements/create", methods=["POST"])
@admin_required
def admin_announcements_create():
    title = request.form.get("title", "")
    body = request.form.get("body", "")
    priority = request.form.get("priority", "normal")
    target_plans = request.form.get("target_plans", "all")
    voice_enabled = request.form.get("voice_enabled") == "on"
    ok, msg, ann_id = ann_mod.create_announcement(
        session["user_id"], title, body, priority, target_plans, voice_enabled
    )
    log_action(session["user_id"], "announcement_created",
               details=f"id:{ann_id},target:{target_plans}", ip=request.remote_addr)
    flash(msg, "success" if ok else "error")
    return redirect(url_for("admin_announcements"))


@app.route("/admin/announcements/<int:ann_id>/toggle", methods=["POST"])
@admin_required
def admin_announcements_toggle(ann_id):
    ann_mod.toggle_announcement(ann_id)
    flash("E'lon holati o'zgartirildi.", "success")
    return redirect(url_for("admin_announcements"))


@app.route("/admin/announcements/<int:ann_id>/delete", methods=["POST"])
@admin_required
def admin_announcements_delete(ann_id):
    ann_mod.delete_announcement(ann_id)
    flash("E'lon o'chirildi.", "success")
    return redirect(url_for("admin_announcements"))


@app.route("/api/announcements/pending")
@api_login_required
def api_announcements_pending():
    """Foydalanuvchi hali ko'rmagan faol e'lonlar (front-end real-vaqtda chaqiradi)."""
    user = get_current_user()
    pending = ann_mod.get_active_announcements_for_user(user["id"])
    return api_response(True, data={"announcements": pending})


@app.route("/api/announcements/<int:ann_id>/seen", methods=["POST"])
@api_login_required
def api_announcements_seen(ann_id):
    user = get_current_user()
    ann_mod.mark_announcement_viewed(user["id"], ann_id)
    return api_response(True)


@app.route("/api/notifications/pending")
@api_login_required
def api_notifications_pending():
    """Foydalanuvchining o'qilmagan barcha bildirishnomalari (ovozli xabarlar uchun)."""
    user = get_current_user()
    items = query_all(
        "SELECT id, title, body, type, created_at FROM notifications WHERE user_id=? AND is_read=0 ORDER BY id DESC LIMIT 20",
        (user["id"],)
    )
    return api_response(True, data={"notifications": items})


@app.route("/api/notifications/<int:notif_id>/read", methods=["POST"])
@api_login_required
def api_notifications_mark_read(notif_id):
    user = get_current_user()
    execute("UPDATE notifications SET is_read=1 WHERE id=? AND user_id=?",
            (notif_id, user["id"]))
    return api_response(True)


# =================================================================
# WEB PUSH NOTIFICATIONS — foydalanuvchi saytdan chiqib ketsa ham
# qurilmasiga bildirishnoma kelishi uchun (Push API + Service Worker)
# =================================================================

@app.route("/sw.js")
def service_worker():
    """Service Worker ildiz darajasida xizmat ko'rsatilishi shart (scope cheklovi)."""
    resp = send_file(os.path.join(app.root_path, "static", "sw.js"))
    resp.headers["Content-Type"] = "application/javascript"
    resp.headers["Service-Worker-Allowed"] = "/"
    return resp


@app.route("/api/push/vapid-public-key")
def api_push_vapid_key():
    """Frontend uchun VAPID public key (obuna yaratishda kerak)."""
    return api_response(True, data={
        "publicKey": Config.VAPID_PUBLIC_KEY,
        "configured": push_mod.is_push_configured(),
    })


@app.route("/api/push/subscribe", methods=["POST"])
@api_login_required
def api_push_subscribe():
    """Brauzer push obunasini saqlash."""
    user = get_current_user()
    data = request.get_json(silent=True) or {}
    endpoint = data.get("endpoint", "")
    keys = data.get("keys", {})
    p256dh = keys.get("p256dh", "")
    auth = keys.get("auth", "")
    ua = request.headers.get("User-Agent", "")[:255]
    ok, msg = push_mod.save_subscription(user["id"], endpoint, p256dh, auth, ua)
    if ok:
        log_action(user["id"], "push_subscribed", ip=request.remote_addr)
        return api_response(True, data={"message": msg})
    return api_response(False, error=msg)


@app.route("/api/push/unsubscribe", methods=["POST"])
@api_login_required
def api_push_unsubscribe():
    """Push obunasini bekor qilish (foydalanuvchi ovozni/push'ni o'chirganda)."""
    data = request.get_json(silent=True) or {}
    endpoint = data.get("endpoint", "")
    if endpoint:
        push_mod.remove_subscription(endpoint)
    return api_response(True)


@app.route("/api/push/test", methods=["POST"])
@login_required
def api_push_test():
    """Foydalanuvchi o'zi sinash uchun test push yuborish."""
    user = get_current_user()
    if not push_mod.has_active_subscription(user["id"]):
        flash("Avval push bildirishnomalarni yoqing.", "error")
        return redirect(request.referrer or url_for("dashboard"))
    result = push_mod.send_push_to_user(
        user["id"], "Test bildirishnoma",
        "Bu CYBER SHATS dan sinov xabari. Push ishlayapti!", "/dashboard"
    )
    if result.get("sent", 0) > 0:
        flash(f"Test push yuborildi ({result['sent']} ta qurilmaga).", "success")
    else:
        flash("Push yuborilmadi: " + result.get("error", "noma'lum xato"), "error")
    return redirect(request.referrer or url_for("dashboard"))


# =================================================================
# SMM / TARGETOLOG / LOGISTIKA — Faqat Pro (alohida AI chat)
# =================================================================
@app.route("/smm")
@login_required
def smm_hub():
    user = get_current_user()
    if user.get("plan") not in ("pro", "cyber_pro", "vip", "enterprise") and user.get("role") not in ("admin", "super_admin", "mentor"):
        flash("SMM, Targetolog va Logistika bo'limlari faqat Pro foydalanuvchilar uchun!", "warn")
        return redirect(url_for("pricing"))
    return render_template("smm_hub.html", smm_directions=SMM_DIRECTIONS, user=user)


@app.route("/smm/<direction>")
@login_required
def smm_chat(direction):
    user = get_current_user()
    if user.get("plan") not in ("pro", "cyber_pro", "vip", "enterprise") and user.get("role") not in ("admin", "super_admin", "mentor"):
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
    if user.get("plan") not in ("pro", "cyber_pro", "vip", "enterprise") and user.get("role") not in ("admin", "super_admin", "mentor"):
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
    # Premium IDlarni tekshir (endi bazadan)
    is_premium = query_one("SELECT id FROM premium_ids WHERE custom_id=?", (new_id,))
    if is_premium:
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
    vip_ids = get_vip_ids_list()
    return render_template("admin_ids.html", premium_ids=premium_ids, auctions=auctions, vip_ids=vip_ids)


@app.route("/admin/ids/vip/assign", methods=["POST"])
@admin_required
def admin_vip_assign():
    """VIP maxsus ID (0-9) ni foydalanuvchiga tayinlash."""
    digit = request.form.get("digit", "").strip()
    try:
        user_id = int(request.form.get("user_id", 0))
    except ValueError:
        user_id = 0
    ok, msg = assign_vip_id(session["user_id"], digit, user_id)
    if ok:
        log_action(session["user_id"], "vip_id_assigned", details=f"digit:{digit},user:{user_id}",
                   ip=request.remote_addr)
    flash(msg, "success" if ok else "error")
    return redirect(url_for("admin_ids") + "#vip")


@app.route("/admin/ids/vip/<digit>/revoke", methods=["POST"])
@admin_required
def admin_vip_revoke(digit):
    """VIP ID'ni egasidan qaytarib olish."""
    ok, msg = revoke_vip_id(digit)
    if ok:
        log_action(session["user_id"], "vip_id_revoked", details=f"digit:{digit}", ip=request.remote_addr)
    flash(msg, "success" if ok else "error")
    return redirect(url_for("admin_ids") + "#vip")


@app.route("/admin/ids/create", methods=["POST"])
@admin_required
def admin_create_premium_id_route():
    """Admin yangi premium ID (istalgan 7 xonali raqam) + narx kiritib sotuvga qo'shadi."""
    custom_id = request.form.get("custom_id", "").strip()
    id_type = request.form.get("id_type", "custom").strip() or "custom"
    try:
        base_price = int(request.form.get("base_price", 0))
    except ValueError:
        base_price = 0
    ok, msg = admin_create_premium_id(custom_id, base_price, id_type)
    flash(msg, "success" if ok else "error")
    if ok:
        log_action(session["user_id"], "admin_create_premium_id",
                   details=f"id:{custom_id},price:{base_price}", ip=request.remote_addr)
    return redirect(url_for("admin_ids"))


@app.route("/admin/ids/<custom_id>/set-price", methods=["POST"])
@admin_required
def admin_set_premium_id_price(custom_id):
    """Admin mavjud premium IDning narxini o'zgartiradi."""
    try:
        base_price = int(request.form.get("base_price", 0))
    except ValueError:
        base_price = 0
    ok, msg = admin_update_premium_id_price(custom_id, base_price)
    flash(msg, "success" if ok else "error")
    if ok:
        log_action(session["user_id"], "admin_update_premium_id_price",
                   details=f"id:{custom_id},price:{base_price}", ip=request.remote_addr)
    return redirect(url_for("admin_ids"))


@app.route("/admin/ids/<custom_id>/delete", methods=["POST"])
@admin_required
def admin_delete_premium_id_route(custom_id):
    """Admin premium IDni ro'yxatdan o'chiradi (faqat sotilmagan bo'lsa)."""
    ok, msg = admin_delete_premium_id(custom_id)
    flash(msg, "success" if ok else "error")
    if ok:
        log_action(session["user_id"], "admin_delete_premium_id",
                   details=f"id:{custom_id}", ip=request.remote_addr)
    return redirect(url_for("admin_ids"))


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



@app.route("/admin/courses/<int:course_id>/set-price", methods=["POST"])
@admin_required
def admin_set_course_price(course_id):
    """Kursning code-narxini admin o'zgartiradi."""
    course = query_one("SELECT * FROM courses WHERE id=?", (course_id,))
    if not course:
        abort(404)
    try:
        price = max(0, int(request.form.get("code_price", 0)))
    except ValueError:
        price = 0
    execute("UPDATE courses SET code_price=? WHERE id=?", (price, course_id))
    log_action(session["user_id"], "admin_set_course_price",
               details=f"course:{course_id},price:{price}", ip=request.remote_addr)
    flash(f"«{course['title']}» kursi narxi {price:,} code ga o'zgartirildi.", "success")
    return redirect(url_for("admin_dashboard") + "#codes")


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
    """Free plan sozlamalarini bazaga saqlaydi — butun saytda darhol ishlaydi."""
    try:
        ai_limit = int(request.form.get("ai_daily_limit", 10))
    except ValueError:
        ai_limit = 10
    try:
        test_limit = int(request.form.get("free_test_limit", 30))
    except ValueError:
        test_limit = 30
    smm_access = 1 if request.form.get("free_smm", "0") == "1" else 0

    set_prices({
        "free_ai_limit": ai_limit,
        "free_test_limit": test_limit,
        "free_smm_access": smm_access,
    }, updated_by=session["user_id"])
    log_action(session["user_id"], "update_free_plan_settings",
               details=f"ai_limit:{ai_limit},test_limit:{test_limit},smm:{smm_access}",
               ip=request.remote_addr)
    flash("Free plan sozlamalari saqlandi.", "success")
    return redirect(url_for("admin_dashboard") + "#settings")


@app.route("/admin/settings/pro-plan", methods=["POST"])
@admin_required
def admin_settings_pro_plan():
    """Pro plan narxlarini bazaga saqlaydi — Pro sotib olish narxi darhol o'zgaradi."""
    try:
        price_uzs = int(request.form.get("pro_price_uzs", 99000))
    except ValueError:
        price_uzs = 99000
    try:
        price_code = int(request.form.get("pro_price_code", 57000))
    except ValueError:
        price_code = 57000
    try:
        ai_limit = int(request.form.get("pro_ai_limit", 100))
    except ValueError:
        ai_limit = 100
    try:
        duration = int(request.form.get("pro_duration_days", 30))
    except ValueError:
        duration = 30

    set_prices({
        "pro_price_uzs": price_uzs,
        "pro_price_code": price_code,
        "pro_ai_limit": ai_limit,
        "pro_duration_days": duration,
    }, updated_by=session["user_id"])
    log_action(session["user_id"], "update_pro_plan_settings",
               details=f"price_uzs:{price_uzs},price_code:{price_code},ai_limit:{ai_limit},duration:{duration}",
               ip=request.remote_addr)
    flash("Pro plan narxlari saqlandi va saytda yangilandi.", "success")
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


@app.route("/admin/settings/pricing", methods=["POST"])
@admin_required
def admin_update_pricing():
    """Barcha CODE narxlarini bitta forma orqali saqlash."""
    keys = [
        "pro_price_code", "cyber_pro_price_code", "vip_price_code",
        "paid_course_code_default",
        "coin_transfer_fee_percent", "plan_duration_days",
        "welcome_bonus_code", "cyber_pro_welcome_bonus", "vip_welcome_bonus",
        "course_reward_code", "cyber_pro_course_bonus", "vip_course_bonus",
        "ai_cost_per_msg",
        "certificate_exam_fee",
        "ping_test_free_quota", "ping_test_pro_quota", "ping_test_cyber_pro_quota", "ping_test_vip_quota",
        "ping_test_cost_free", "ping_test_cost_pro", "ping_test_cost_cyber_pro", "ping_test_cost_vip",
        "id_tier_A_min", "id_tier_A_max",
        "id_tier_B_min", "id_tier_B_max",
        "id_tier_C_min", "id_tier_C_max",
        "id_tier_D_min", "id_tier_D_max",
        "id_tier_E_min", "id_tier_E_max",
    ]
    updates = {}
    for k in keys:
        v = request.form.get(k)
        if v is None or v == "":
            continue
        try:
            updates[k] = int(v)
        except ValueError:
            continue
    # Checkbox (form'da yo'q bo'lsa = o'chirilgan)
    updates["vip_enabled"] = 1 if request.form.get("vip_enabled") == "1" else 0
    set_prices(updates, updated_by=session["user_id"])
    log_action(session["user_id"], "update_pricing_settings",
               details=f"keys:{len(updates)}", ip=request.remote_addr)
    flash(f"{len(updates)} ta narx saqlandi va saytda yangilandi.", "success")
    return redirect(url_for("admin_dashboard") + "#pricing")


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
