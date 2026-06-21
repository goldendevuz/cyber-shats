# -*- coding: utf-8 -*-
"""
CYBER SHATS V1.3 — E-kutubxona uchun HAQIQIY, bepul, ochiq litsenziyali
IT kitoblari. Hammasi qonuniy: muallif tomonidan bepul e'lon qilingan
(Creative Commons) yoki public domain.

Eski 12 ta soxta yozuv (file_url='#') o'chiriladi, o'rniga haqiqiy,
ishlaydigan havolalar bilan kitoblar qo'shiladi.

DIQQAT: Bu fayllar bizning serverimizda SAQLANMAYDI — to'g'ridan-to'g'ri
muallif/noshirning rasmiy saytiga havola qilinadi (qonuniy va xavfsiz yondashuv).

Ishga tushirish: python database/seed_real_books.py
"""
import sqlite3
import os

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cyber_shats.db")

# (sarlavha, turi, hajmi-belgisi, kategoriya, havola)
REAL_BOOKS = [
    # ---------- PYTHON ----------
    ("Think Python 2e — Allen B. Downey", "PDF", "~3 MB", "python",
     "https://greenteapress.com/thinkpython2/thinkpython2.pdf"),
    ("Automate the Boring Stuff with Python (onlayn)", "Web", "Onlayn", "python",
     "https://automatetheboringstuff.com/"),
    ("A Byte of Python", "Web", "Onlayn", "python",
     "https://python.swaroopch.com/"),

    # ---------- WEB DASTURLASH ----------
    ("Eloquent JavaScript (3rd Edition)", "Web", "Onlayn", "javascript",
     "https://eloquentjavascript.net/"),
    ("You Don't Know JS (kitoblar seriyasi)", "GitHub", "Onlayn", "javascript",
     "https://github.com/getify/You-Dont-Know-JS"),
    ("MDN Web Docs — HTML/CSS/JS to'liq qo'llanma", "Web", "Onlayn", "web-dev",
     "https://developer.mozilla.org/uz/"),

    # ---------- CYBER SECURITY ----------
    ("OWASP Testing Guide", "PDF", "Onlayn", "cyber-security",
     "https://owasp.org/www-project-web-security-testing-guide/"),
    ("The Web Application Hacker's Handbook (resurslar)", "Web", "Onlayn", "cyber-security",
     "https://owasp.org/www-project-top-ten/"),
    ("NIST Cybersecurity Framework", "PDF", "Onlayn", "cyber-security",
     "https://www.nist.gov/cyberframework"),

    # ---------- TARMOQ / LINUX ----------
    ("The Linux Command Line — William Shotts", "PDF", "~3.5 MB", "networking",
     "https://linuxcommand.org/tlcl.php"),
    ("TCP/IP asoslari (Wikibooks)", "Web", "Onlayn", "networking",
     "https://en.wikibooks.org/wiki/Communication_Networks/TCP_and_UDP_Protocols"),

    # ---------- ALGORITMLAR / CS ----------
    ("Open Data Structures", "PDF", "~2 MB", "database",
     "https://opendatastructures.org/"),
    ("Think Complexity 2e — Allen B. Downey", "PDF", "~2 MB", "ai-ml",
     "https://greenteapress.com/wp/think-complexity-2e/"),

    # ---------- C++ ----------
    ("Learn C++ (learncpp.com)", "Web", "Onlayn", "cpp",
     "https://www.learncpp.com/"),

    # ---------- MA'LUMOTLAR BAZASI ----------
    ("Use The Index, Luke! (SQL optimallashtirish)", "Web", "Onlayn", "database",
     "https://use-the-index-luke.com/"),

    # ---------- DEVOPS / CLOUD ----------
    ("The Site Reliability Workbook (Google SRE)", "Web", "Onlayn", "devops",
     "https://sre.google/workbook/table-of-contents/"),
    ("Kubernetes hujjatlari (rasmiy)", "Web", "Onlayn", "cloud",
     "https://kubernetes.io/docs/home/"),

    # ---------- DATA SCIENCE / AI ----------
    ("Dive into Deep Learning", "Web", "Onlayn", "ai-ml",
     "https://d2l.ai/"),
    ("An Introduction to Statistical Learning", "PDF", "~15 MB", "data-science",
     "https://www.statlearning.com/"),

    # ---------- UMUMIY (FREE PROGRAMMING BOOKS) ----------
    ("Free Programming Books — to'liq ro'yxat (4000+)", "Web", "Onlayn", "boshqa",
     "https://ebookfoundation.github.io/free-programming-books-search/"),
]


def main():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # Eski soxta yozuvlarni tozalash (file_url='#' bo'lganlar)
    deleted = c.execute("DELETE FROM books WHERE file_url='#'").rowcount
    print(f"O'chirilgan soxta yozuvlar: {deleted}")

    inserted = 0
    for title, ftype, size, category, url in REAL_BOOKS:
        existing = c.execute("SELECT id FROM books WHERE title=?", (title,)).fetchone()
        if existing:
            c.execute(
                "UPDATE books SET type=?, size_label=?, category=?, file_url=? WHERE title=?",
                (ftype, size, category, url, title)
            )
        else:
            c.execute(
                "INSERT INTO books (title, type, size_label, category, file_url) VALUES (?,?,?,?,?)",
                (title, ftype, size, category, url)
            )
            inserted += 1

    conn.commit()
    total = c.execute("SELECT COUNT(*) FROM books").fetchone()[0]
    conn.close()
    print(f"Yangi qo'shilgan kitoblar: {inserted}")
    print(f"Jami kitoblar bazada: {total}")


if __name__ == "__main__":
    main()
