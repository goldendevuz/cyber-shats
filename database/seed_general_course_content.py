# -*- coding: utf-8 -*-
"""
CYBER SHATS V1.3 — Boshqa yo'nalishlar (Cyber Security'dan tashqari) uchun
video havolasini olib tashlab, professional matn material bilan almashtirish.

Cyber Security kurslari (course_id 9-12) allaqachon seed_cybersecurity_content.py
orqali chuqur, qo'lda yozilgan material oldi. Bu skript qolgan 817 ta dars uchun
kursning mavzusiga mos, video YO'Q, foydali matn material yaratadi.

Eslatma: bu material qo'lda yozilgan Cyber Security darslari darajasida CHUQUR
EMAS (817 ta darsga individual yozish amaliy emas), lekin har biri kurs mavzusiga
mos, video havolasisiz, foydali tuzilgan matn beradi.

Ishga tushirish: python database/seed_general_course_content.py
"""
import sqlite3
import os

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cyber_shats.db")


def generate_lesson_content(course_title: str, module_topic: str, lesson_num: int,
                             total_in_module: int, is_practice: bool) -> str:
    """
    Kurs va modul mavzusiga mos, video havolasisiz, professional formatdagi
    matn material yaratadi.
    """
    if is_practice:
        return f"""## {module_topic} — Amaliy mashq

Bu modulda o'rgangan **{module_topic}** mavzusi bo'yicha amaliyot vaqti keldi.

### Vazifa

1. Modul davomida o'rgangan asosiy tushunchalarni qisqacha o'z so'zlaringiz bilan
   yozib chiqing
2. Agar yo'nalishingiz Hacker Lab orqali amaliyot qilish imkoniyatiga ega bo'lsa,
   o'sha paneldan foydalaning
3. O'rgangan bilimlaringizni "Jamoa" bo'limida boshqa o'quvchilar bilan ulashing

### Nazorat savollari

- **{module_topic}** mavzusidagi eng muhim 3 ta tushunchani sanab bering
- Bu bilimlarni real loyihada qanday qo'llash mumkin?

Keyingi modulga o'tishdan oldin, ushbu mavzuni to'liq tushunganingizga ishonch
hosil qiling — keyingi mavzular ko'pincha avvalgisiga asoslanadi.
"""

    return f"""## {module_topic} — {lesson_num}-qism

«**{course_title}**» kursining ushbu qismida **{module_topic}** mavzusi bo'yicha
asosiy tushunchalar va amaliy yondashuvlar ko'rib chiqiladi.

### Bu darsda nimalarni o'rganasiz

Ushbu mavzu — «{course_title}» kursining muhim qismlaridan biri bo'lib,
keyingi darslarda chuqurroq qo'llaniladigan asosiy tushunchalarni shakllantiradi.
Materialni diqqat bilan o'qib, asosiy g'oyalarni o'zlashtirib oling.

### Asosiy tushunchalar

«{module_topic}» mavzusida e'tibor qaratish kerak bo'lgan jihatlar:

- Nazariy asoslarni tushunish — bu amaliyotda xato qilmaslik uchun zarur
- Har bir yangi tushunchani avvalgi bilimlar bilan bog'lash
- Mumkin bo'lsa, kichik amaliy misollar orqali sinab ko'rish

### Amaliyotga tayyorlanish

Modul oxiridagi amaliy mashqda ushbu qismda o'rgangan bilimlaringiz sinaladi.
Agar biror joyni tushunmay qolsangiz, materialni qayta o'qing yoki Hacker Lab
panelidagi AI yordamchilardan (yoki tashqi Gemini/ChatGPT havolalaridan) yordam
so'rang.

### Keyingi qadam

{"Ushbu modulning so'nggi nazariy qismi — keyingi dars amaliyot bo'ladi." if lesson_num == total_in_module - 1 else "Keyingi darsda mavzu davom etadi, materiallarni ketma-ket o'qib boring."}
"""


def main():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Cyber Security darslaridan tashqari hamma narsani yangilaymiz
    lessons = c.execute(
        """SELECT l.id, l.title, l.order_num, l.course_id, l.module_id,
                  m.title as module_title, c.title as course_title
           FROM lessons l
           JOIN modules m ON m.id = l.module_id
           JOIN courses c ON c.id = l.course_id
           WHERE l.course_id NOT IN (9,10,11,12)
           ORDER BY l.course_id, l.order_num"""
    ).fetchall()

    print(f"Yangilanadigan darslar soni: {len(lessons)}")

    # Har bir modul uchun "mavzu nomi"ni aniqlash (1-modul nomidan, masalan
    # "1-Modul: HTML Asoslari" -> "HTML Asoslari"). Agar modul nomi sodda
    # bo'lsa ("2-Modul"), kurs nomidan foydalanamiz.
    module_topics = {}
    for row in lessons:
        mid = row["module_id"]
        if mid not in module_topics:
            mtitle = row["module_title"]
            if ":" in mtitle:
                topic = mtitle.split(":", 1)[1].strip()
            else:
                topic = row["course_title"]
            module_topics[mid] = topic

    # Har bir modul ichidagi darslar sonini hisoblash (amaliyot pozitsiyasini
    # aniqlash uchun)
    module_lesson_counts = {}
    for row in lessons:
        mid = row["module_id"]
        module_lesson_counts[mid] = module_lesson_counts.get(mid, 0) + 1

    module_lesson_index = {}  # joriy hisoblagich har bir modul uchun

    updated = 0
    for row in lessons:
        mid = row["module_id"]
        module_lesson_index[mid] = module_lesson_index.get(mid, 0) + 1
        idx = module_lesson_index[mid]
        total = module_lesson_counts[mid]
        topic = module_topics[mid]
        is_practice = "amaliyot" in (row["title"] or "").lower()

        content = generate_lesson_content(
            row["course_title"], topic, idx, total, is_practice
        )
        c.execute("UPDATE lessons SET content_html=? WHERE id=?", (content, row["id"]))
        updated += 1

    conn.commit()
    conn.close()
    print(f"Jami yangilangan darslar: {updated}")


if __name__ == "__main__":
    main()
