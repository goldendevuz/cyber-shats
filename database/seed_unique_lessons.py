# -*- coding: utf-8 -*-
"""
CYBER SHATS V1.3 — Har bir dars uchun noyob, mavzuga mos content.
Ishga tushirish: python database/seed_unique_lessons.py
"""
import sqlite3, os

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cyber_shats.db")

# Har bir yo'nalish uchun dars mavzulari (kurs tartibida)
# Format: {course_id: [(sarlavha, qisqacha_content), ...]}

LESSONS = {
# ===== Python =====
5: [
("Python nima va nima uchun?", "## Python nima?\n\nPython — 1991 yilda Guido van Rossum tomonidan yaratilgan, oddiy sintaksisli va kuchli kutubxonalarga ega dasturlash tili.\n\n### Qo'llanilishi\n- Web (Django, Flask)\n- Ma'lumot tahlili (Pandas, NumPy)\n- Mashinaviy o'qitish (TensorFlow, PyTorch)\n- Avtomatlashtirish\n- Tizim skriptlash\n\n### O'rnatish\n```bash\npython --version   # versiyani tekshirish\npip install <paket>  # paket o'rnatish\n```\n"),
("O'zgaruvchilar va ma'lumot turlari", "## O'zgaruvchilar va ma'lumot turlari\n\n```python\nism = 'Aziz'         # str\nyosh = 25            # int\nnарx = 19.99         # float\nfaol = True          # bool\n\nprint(type(ism))     # <class 'str'>\n```\n\n### Type conversion\n```python\nx = int('42')\ny = float('3.14')\nz = str(100)\n```\n\n### F-strings\n```python\nprint(f'{ism} {yosh} yoshda')  # Aziz 25 yoshda\n```\n"),
("Ro'yxatlar, kortejlar, lug'atlar", "## Kolleksiyalar\n\n### List\n```python\nmevalr = ['olma', 'banan', 'uzum']\nmevalr.append('nok')\nmevalr.sort()\nprint(mevalr[0])    # olma\n```\n\n### Tuple (o'zgarmas)\n```python\nkoord = (40.7128, -74.0060)\nkenglik, uzunlik = koord\n```\n\n### Dict\n```python\ntalaba = {'ism': 'Sarvar', 'yosh': 20}\ntalaba['guruh'] = 'CS-22'\nprint(talaba.get('telefon', 'noma\\'lum'))\n```\n"),
("Shartli operatorlar", "## Shartli operatorlar\n\n```python\nyosh = 18\n\nif yosh >= 18:\n    print('Voyaga yetgan')\nelif yosh >= 13:\n    print('O\\'smir')\nelse:\n    print('Bola')\n\n# Bir qatorli (ternary)\nnatija = 'katta' if yosh > 18 else 'kichik'\n\n# match-case (Python 3.10+)\nmatch yosh:\n    case 0: print('Chaqaloq')\n    case 18: print('Aynan 18')\n    case _: print('Boshqa')\n```\n"),
("Tsikllar: for va while", "## Tsikllar\n\n### For tsikli\n```python\n# Range\nfor i in range(5):         # 0-4\n    print(i)\n\n# Ro'yxat bo'yicha\nfor meva in ['olma','banan']:\n    print(meva)\n\n# Enumerate\nfor i, el in enumerate(['a','b','c']):\n    print(f'{i}: {el}')\n\n# Zip\nfor nom, baho in zip(['Ali','Vali'],[85,90]):\n    print(f'{nom}: {baho}')\n```\n\n### While\n```python\nn = 0\nwhile n < 5:\n    print(n)\n    n += 1\n```\n"),
("Funksiyalar: asosiy", "## Funksiyalar\n\n```python\ndef tabrikla(ism, til='uz'):\n    if til == 'uz':\n        return f'Assalomu alaykum, {ism}!'\n    return f'Hello, {ism}!'\n\nprint(tabrikla('Bobur'))\nprint(tabrikla('Alex', til='en'))\n```\n\n### *args va **kwargs\n```python\ndef yig_indi(*sonlar):\n    return sum(sonlar)\n\ndef chop(**info):\n    for k, v in info.items():\n        print(f'{k} = {v}')\n\nprint(yig_indi(1, 2, 3, 4, 5))\nchop(ism='Nilufar', yosh=22, shahar='Toshkent')\n```\n"),
("Funksiyalar: ilg'or", "## Lambda, map, filter, sorted\n\n```python\n# Lambda\nkarre = lambda x: x**2\nprint(karre(7))    # 49\n\n# Map\nsonlar = [1, 2, 3, 4]\nkarreli = list(map(lambda x: x**2, sonlar))\n\n# Filter\ntoq = list(filter(lambda x: x % 2 != 0, sonlar))\n\n# Sorted bilan key\nso_zlar = ['banana', 'apple', 'cherry']\nprint(sorted(so_zlar, key=len))  # uzunlik bo'yicha\n\n# List comprehension (pythonic)\nkarreli2 = [x**2 for x in sonlar if x > 1]\n```\n"),
("OOP: Sinflar va obyektlar", "## Obyektga yo'naltirilgan dasturlash\n\n```python\nclass Avtomobil:\n    ishlab_chiqaruvchi = 'CYBER Motors'  # klass o'zgaruvchisi\n\n    def __init__(self, model, yil, rang):\n        self.model = model\n        self.yil = yil\n        self.rang = rang\n        self._tezlik = 0      # himoyalangan\n\n    def tezlashtir(self, qo_shimcha):\n        self._tezlik += qo_shimcha\n        return self\n\n    @property\n    def tezlik(self):\n        return self._tezlik\n\n    def __str__(self):\n        return f'{self.yil} {self.model} ({self.rang})'\n\nmashin = Avtomobil('Nexia', 2022, 'qora')\nmashin.tezlashtir(60).tezlashtir(20)\nprint(mashin, '—', mashin.tezlik, 'km/h')\n```\n"),
("OOP: Meros va polimorfizm", "## Meros (Inheritance) va Polimorfizm\n\n```python\nclass Shakl:\n    def yuza(self):\n        raise NotImplementedError\n\n    def hisob(self):\n        print(f'Yuza: {self.yuza():.2f}')\n\nclass Aylana(Shakl):\n    def __init__(self, radius):\n        self.r = radius\n\n    def yuza(self):\n        import math\n        return math.pi * self.r ** 2\n\nclass To_rtburchak(Shakl):\n    def __init__(self, a, b):\n        self.a, self.b = a, b\n\n    def yuza(self):\n        return self.a * self.b\n\nfor shakl in [Aylana(5), To_rtburchak(4, 6)]:\n    shakl.hisob()    # polimorfizm\n```\n"),
("Fayl va istisnolarni boshqarish", "## Fayllar va Try/Except\n\n```python\nimport json\n\n# Fayl o'qish\ntry:\n    with open('data.json', 'r', encoding='utf-8') as f:\n        data = json.load(f)\nexcept FileNotFoundError:\n    print('Fayl topilmadi')\nexcept json.JSONDecodeError as e:\n    print(f'JSON xato: {e}')\nelse:\n    print('Muvaffaqiyatli yuklandi')\nfinally:\n    print('Har doim bajariladi')\n\n# Fayl yozish\nwith open('natija.txt', 'w', encoding='utf-8') as f:\n    f.write('Salom, fayl!\\n')\n```\n"),
("Modullar va paketlar", "## Modullar va paket tizimi\n\n```python\n# Standart kutubxona\nimport os, sys, math, random\nfrom datetime import datetime, timedelta\nfrom collections import Counter, defaultdict\nimport itertools\n\n# Amaliy misollar\nprint(os.getcwd())             # joriy papka\nprint(sys.version)             # Python versiyasi\nprint(math.gcd(48, 18))       # 6\nprint(Counter('hello'))        # {'l':2, ...}\n\n# random\nprint(random.choice(['a','b','c']))\nprint(random.sample(range(100), 10))\n\n# datetime\nbugon = datetime.now()\nertaga = bugon + timedelta(days=1)\nprint(ertaga.strftime('%Y-%m-%d'))\n```\n"),
],

# ===== JavaScript =====
13: [
("JS tarixi va brauzerda ishlash", "## JavaScript tarixi\n\nJavaScript 1995 yilda Brendan Eich tomonidan 10 kunda yaratilgan. Hozir ECMA standartiga asoslanadi.\n\n### Qanday ishlaydi?\n```html\n<!-- HTML'ga ulanish -->\n<script src='app.js'></script>\n\n<!-- Inline -->\n<script>\n    console.log('Salom!');\n    document.title = 'Yangi sarlavha';\n</script>\n```\n\n### Asosiy ob'ektlar\n- `window` — global ob'ekt\n- `document` — DOM\n- `console` — debug\n- `navigator` — brauzer info\n"),
("Zamonaviy JS: let, const, template", "## ES6+ Zamonaviy JavaScript\n\n```javascript\n// let — block scope\nlet yosh = 25;\nyosh = 26;  // OK\n\n// const — o'zgarmas\nconst PI = 3.14;\n\n// Template literals\nconst ism = 'Jasur';\nconsole.log(`Salom, ${ism}! Pi = ${PI.toFixed(2)}`);\n\n// Destructuring\nconst [a, b, ...rest] = [1, 2, 3, 4, 5];\nconst {nomi, yosh: n, ...q} = {nomi:'Ali', yosh:20, ball:90};\n\n// Spread\nconst arr1 = [1,2,3];\nconst arr2 = [...arr1, 4, 5];\nconst yangi = {...q, verified: true};\n```\n"),
("Array metodlari chuqur", "## Array metodlari\n\n```javascript\nconst baholar = [85, 92, 78, 95, 60, 88];\n\n// Transform\nconsole.log(baholar.map(b => b * 1.1));  // 10% bonus\nconsole.log(baholar.filter(b => b >= 80));  // a'lochi\nconsole.log(baholar.reduce((sum, b) => sum + b, 0));  // jami\n\n// Topish\nconsole.log(baholar.find(b => b === 95));   // 95\nconsole.log(baholar.findIndex(b => b < 70)); // 4\nconsole.log(baholar.every(b => b > 50));    // true\nconsole.log(baholar.some(b => b >= 95));    // true\n\n// O'zgartirish\nconst saralangan = [...baholar].sort((a,b) => b-a);\nconst tekis = [[1,2],[3,4]].flat();\n```\n"),
("DOM boshqaruvi", "## DOM — Document Object Model\n\n```javascript\n// Elementlar topish\nconst sarlavha = document.getElementById('sarlavha');\nconst tugmalar = document.querySelectorAll('.tugma');\nconst birinchi = document.querySelector('nav > a:first-child');\n\n// O'zgartirish\nsarlavha.textContent = 'Yangi matn';\nsarlavha.innerHTML = '<em>Kursiv</em>';\nsarlavha.style.color = '#00ff41';\nsarlavha.classList.add('faol');\nsarlavha.classList.toggle('yashirin');\n\n// Yangi element\nconst p = document.createElement('p');\np.textContent = 'Yangi paragraf';\np.className = 'muted';\ndocument.body.appendChild(p);\n\n// O'chirish\np.remove();\n```\n"),
("Events va hodisalar", "## Event handling\n\n```javascript\nconst btn = document.querySelector('#submit');\n\n// Standart\nbtn.addEventListener('click', function(e) {\n    e.preventDefault();\n    console.log('Click!', e.target);\n});\n\n// Arrow function\ndocument.addEventListener('keydown', (e) => {\n    if (e.ctrlKey && e.key === 's') {\n        e.preventDefault();\n        saqlash();\n    }\n});\n\n// Delegation (samarali)\ndocument.getElementById('list').addEventListener('click', (e) => {\n    const li = e.target.closest('li');\n    if (li) li.classList.toggle('tanlangan');\n});\n\n// Custom event\nconst event = new CustomEvent('ma_lumot', { detail: { id: 5 } });\ndocument.dispatchEvent(event);\n```\n"),
("Async/Await va Promises", "## Asinxron dasturlash\n\n```javascript\n// Promise yaratish\nconst kechikish = (ms) => new Promise(resolve => setTimeout(resolve, ms));\n\n// Async/Await\nasync function ma_lumot_olish(url) {\n    try {\n        const res = await fetch(url);\n        if (!res.ok) throw new Error(`HTTP ${res.status}`);\n        const data = await res.json();\n        return data;\n    } catch (xato) {\n        console.error('Xato:', xato.message);\n        throw xato;\n    }\n}\n\n// Bir vaqtda ko'p so'rov\nasync function barchani_ol() {\n    const [users, posts] = await Promise.all([\n        fetch('/api/users').then(r => r.json()),\n        fetch('/api/posts').then(r => r.json())\n    ]);\n    return { users, posts };\n}\n```\n"),
],

# ===== Web Dev =====
1: [
("HTML — asoslar va tuzilish", "## HTML asoslar\n\n```html\n<!DOCTYPE html>\n<html lang='uz'>\n<head>\n    <meta charset='UTF-8'>\n    <meta name='viewport' content='width=device-width, initial-scale=1'>\n    <title>Sahifa</title>\n</head>\n<body>\n    <header>\n        <nav>\n            <a href='/'>Bosh sahifa</a>\n            <a href='/haqida'>Haqida</a>\n        </nav>\n    </header>\n    <main>\n        <h1>Asosiy sarlavha</h1>\n        <p>Paragraf matni</p>\n    </main>\n    <footer>© 2026</footer>\n</body>\n</html>\n```\n\n### Semantik teglar\n`<header>`, `<nav>`, `<main>`, `<article>`, `<section>`, `<aside>`, `<footer>` — qidiruv va foydalanish uchun muhim.\n"),
("CSS — selektorlar va box model", "## CSS\n\n```css\n/* Box model */\n.karta {\n    width: 300px;\n    padding: 16px;\n    border: 1px solid #ccc;\n    margin: 10px auto;\n    border-radius: 8px;\n    box-shadow: 0 2px 8px rgba(0,0,0,.1);\n    box-sizing: border-box;  /* padding ichida */\n}\n\n/* Selektorlar */\na:hover { color: blue; }\np:first-child { font-weight: bold; }\n.list > li { list-style: none; }\n.btn + .btn { margin-left: 8px; }\n\n/* CSS o'zgaruvchilari */\n:root {\n    --asosiy: #00ff41;\n    --fon: #0a0a0a;\n}\nh1 { color: var(--asosiy); }\n```\n"),
("Flexbox layout", "## Flexbox\n\n```css\n.container {\n    display: flex;\n    justify-content: space-between;  /* asosiy o'q */\n    align-items: center;              /* ko'ndalang o'q */\n    flex-wrap: wrap;\n    gap: 16px;\n}\n\n.element {\n    flex: 1 1 250px;  /* grow shrink basis */\n    order: 2;         /* tartib */\n}\n\n/* Navbar */\n.navbar {\n    display: flex;\n    justify-content: space-between;\n    align-items: center;\n    padding: 0 20px;\n    height: 60px;\n}\n\n/* Markazlashtirish */\n.centered {\n    display: flex;\n    justify-content: center;\n    align-items: center;\n    min-height: 100vh;\n}\n```\n"),
("Grid layout", "## CSS Grid\n\n```css\n/* Asosiy grid */\n.grid {\n    display: grid;\n    grid-template-columns: repeat(3, 1fr);\n    grid-template-rows: auto;\n    gap: 20px;\n}\n\n/* Responsive grid */\n.responsive-grid {\n    display: grid;\n    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));\n    gap: 16px;\n}\n\n/* Nozik joylashtirish */\n.boshqaruv {\n    grid-column: 1 / -1;     /* butun qator */\n    grid-row: 1 / 3;         /* 2 qator egallaydi */\n}\n\n/* Named areas */\n.sahifa {\n    grid-template-areas:\n        'header header'\n        'aside main'\n        'footer footer';\n}\n```\n"),
("Responsive dizayn va media queries", "## Responsive dizayn\n\n```css\n/* Mobile first yondashuv */\n.karta { font-size: 14px; padding: 12px; }\n\n/* Tablet */\n@media (min-width: 768px) {\n    .karta { font-size: 16px; padding: 20px; }\n}\n\n/* Desktop */\n@media (min-width: 1024px) {\n    .karta { padding: 32px; }\n}\n\n/* Printlash */\n@media print { nav, .reklama { display: none; } }\n\n/* Prefers-color-scheme */\n@media (prefers-color-scheme: dark) {\n    body { background: #111; color: #eee; }\n}\n\n/* Viewport units */\n.hero { min-height: 100svh; }  /* svh = small viewport */\n```\n"),
("JavaScript va DOM bilan veb animatsiya", "## Veb animatsiyalar\n\n```css\n/* CSS animatsiya */\n@keyframes paydo_bo_l {\n    from { opacity: 0; transform: translateY(20px); }\n    to   { opacity: 1; transform: translateY(0); }\n}\n\n.animatsiya {\n    animation: paydo_bo_l 0.4s ease-out;\n    transition: all 0.3s ease;\n}\n\n.tugma:hover { transform: scale(1.05); }\n```\n\n```javascript\n// Web Animations API\nconst el = document.querySelector('.karta');\nel.animate([\n    { transform: 'scale(1)', opacity: 1 },\n    { transform: 'scale(0.95)', opacity: 0.5 },\n    { transform: 'scale(1)', opacity: 1 }\n], { duration: 300, easing: 'ease-in-out' });\n\n// IntersectionObserver (scroll animation)\nconst observer = new IntersectionObserver((entries) => {\n    entries.forEach(e => {\n        if (e.isIntersecting) e.target.classList.add('ko_rindi');\n    });\n});\ndocument.querySelectorAll('.fade').forEach(el => observer.observe(el));\n```\n"),
],
}

# Qolgan kurslar uchun yo'nalish bo'yicha mavzu shablonlari
DIRECTION_TOPICS = {
    "ai-ml": [
        "Kirish va muhit sozlash", "Matematik asoslar (Chiziqli algebra)",
        "Statistika va ehtimollik", "NumPy — raqamli hisoblash",
        "Pandas — ma'lumot tahlili", "Vizualizatsiya (Matplotlib/Seaborn)",
        "Scikit-learn — ML kutubxonasi", "Linear/Logistic Regression",
        "Decision Tree va Random Forest", "SVM va KNN",
        "Klasterizatsiya (K-Means, DBSCAN)", "Dimensionality Reduction (PCA)",
        "Model baholash va validatsiya", "Hyperparameter tuning",
        "Loyiha: to'liq ML pipeline",
    ],
    "web-dev": [
        "HTML semantika chuqur", "CSS flexbox amaliyot",
        "CSS grid murakkab layoutlar", "JavaScript ES6+",
        "DOM manipulation ilg'or", "Fetch API va AJAX",
        "LocalStorage va SessionStorage", "CSS animatsiyalar",
        "Responsive dizayn amaliyot", "Veb formalar va validatsiya",
        "Git va versiya nazorat", "Webpack/Vite — build tools",
        "npm va paket menejment", "Debugging va DevTools",
        "Loyiha: Portfolio sayt",
    ],
    "javascript": [
        "ES6+ xususiyatlar batafsil", "Prototip zanjirlari",
        "Closure va scope", "Callback va Promise",
        "Async/Await amaliyot", "Event Loop tushuncha",
        "RegExp — qidiruv naqshlari", "WeakMap va WeakSet",
        "Proxy va Reflect", "Generator funksiyalar",
        "Module sistemasi (ESM)", "TypeScript asoslari",
        "Jest bilan testing", "Design patterns JS'da",
        "Loyiha: Real-time chat",
    ],
    "devops": [
        "Linux buyruqlar qatori", "Shell skriptlash",
        "Git workflow va branching", "Docker asoslari",
        "Dockerfile yozish", "Docker Compose",
        "CI/CD tushuncha", "GitHub Actions",
        "Nginx konfiguratsiya", "SSL/TLS sertifikat",
        "Monitoring (Prometheus/Grafana)", "Logging (ELK Stack)",
        "Kubernetes asoslari", "Helm charts",
        "Loyiha: To'liq CI/CD pipeline",
    ],
    "data-science": [
        "Data Science yo'li", "Python for Data Science",
        "NumPy chuqur", "Pandas amaliyot",
        "Vizualizatsiya ilg'or", "Ma'lumot tozalash",
        "Statistik tahlil", "Gipotest tekshiruvi",
        "SQL for DS", "Web scraping",
        "Feature Engineering", "ML modellar",
        "Time series tahlil", "NLP asoslari",
        "Loyiha: Ma'lumot tahlili hisoboti",
    ],
    "mobile-dev": [
        "Mobil dasturlashga kirish", "Flutter muhiti sozlash",
        "Widget tizimi", "Layout va flexbox Flutter'da",
        "Navigatsiya va routing", "State management",
        "HTTP so'rovlar va API", "Local ma'lumotlar saqlash",
        "Push notification", "Kamera va fayl",
        "Animatsiyalar Flutter'da", "Testing Flutter",
        "Play Store/App Store deploy", "Performance optimizatsiya",
        "Loyiha: To'liq mobil ilova",
    ],
    "cloud": [
        "Cloud computing asoslari", "IaaS, PaaS, SaaS farqlari",
        "AWS/GCP/Azure taqqoslash", "Virtual machine yaratish",
        "Object storage", "Database as a Service",
        "Serverless funksiyalar", "Container orchestration",
        "CDN va edge computing", "IAM va xavfsizlik",
        "Cost optimization", "Multi-cloud strategiya",
        "Disaster recovery", "Cloud monitoring",
        "Loyiha: Cloud-native ilova",
    ],
    "cpp": [
        "C++ asoslari va kompilyatsiya", "Pointer va reference",
        "Xotira boshqaruvi", "STL konteynerlar",
        "Template metaprogramming", "RAII pattern",
        "Smart pointerlar", "Concurrency (thread)",
        "Modern C++17/20", "Performance optimizatsiya",
        "Design patterns C++da", "Unit testing",
    ],
    "database": [
        "Ma'lumotlar bazasi asoslari", "SQL SELECT chuqur",
        "JOIN operatsiyalar", "Subquery va CTE",
        "Indekslash va optimizatsiya", "Tranzaksiyalar va ACID",
        "Normalizatsiya (1NF-3NF)", "Trigger va Stored Procedure",
        "NoSQL tushuncha", "MongoDB asoslari",
        "Redis — kesh va session", "Ma'lumotlar bazasi arxitekturasi",
        "Sharding va replikatsiya", "Backup va recovery",
        "Loyiha: Ma'lumotlar bazasi dizayn",
    ],
    "networking": [
        "OSI modeli 7 qatlam", "TCP/IP to'plami",
        "IP manzillash va CIDR", "Routing protokollar",
        "Switch va VLAN", "Firewall va ACL",
        "VPN texnologiyalar", "DNS chuqur",
        "HTTP/2 va HTTP/3", "Load Balancing",
        "Network monitoring", "Packet analyzer (Wireshark)",
        "SDN (Software Defined Networking)", "IPv6 migratsiya",
        "Loyiha: Tarmoq infratuzilma dizayn",
    ],
    "smm": [
        "Raqamli marketing asoslari", "Maqsadli auditoriya aniqlash",
        "Kontent strategiyasi", "Instagram marketing",
        "Telegram kanal o'stirish", "YouTube strategiyasi",
        "TikTok content", "Copywriting asoslari",
        "Visual dizayn asoslari", "Analitika va metrikalar",
        "Targeted reklama", "Influencer marketing",
        "Email marketing", "SEO asoslari",
        "Loyiha: Brand promotional plan",
    ],
    "matematika": [
        "Sonlar nazariyasi", "Chiziqli algebra — vektorlar",
        "Matritsa amallar", "Determinant va inversiya",
        "Ehtimollik nazariyasi", "Statistika asoslari",
        "Differensial hisob", "Integral hisob",
        "Diskret matematika", "Grafiklar nazariyasi",
        "Kriptografiya matematikasi", "Raqamli metodlar",
    ],
    "ingliz-tili": [
        "IT ingliz tili — kirish", "Texnik hujjatlarni o'qish",
        "Kod sharhlarini yozish", "Stack Overflow samarali ishlatish",
        "GitHub README yozish", "Texnik intervyu so'zlari",
        "API dokumentatsiyasini tushunish", "Email va muloqot",
        "Texnik prezentatsiya", "Open source hissa qo'shish",
        "LinkedIn va portfolio", "Onlayn hamjamiyatda muloqot",
    ],
    "logistika": [
        "Logistika asoslar", "Supply Chain Management",
        "Ombor boshqaruvi", "Transport logistikasi",
        "1C bilan ishlash", "Excel for logistics",
        "KPI va metrikalar", "Import/export qoidalar",
        "Customs va bojxona", "E-commerce logistikasi",
        "Last-mile delivery", "Logistika avtomatizatsiyasi",
    ],
    "office": [
        "Excel — asosiy funksiyalar", "Excel — ilg'or formulalar",
        "Pivot Table va grafik", "Word — professional hujjat",
        "PowerPoint — prezentatsiya", "Outlook — email boshqaruvi",
        "OneNote — eslatmalar", "Teams — jamoa ishlash",
        "Google Sheets", "Google Docs", "Canva dizayn",
        "PDF bilan ishlash",
    ],
    "targetolog": [
        "Targetologiyaga kirish", "Facebook/Meta Ads Manager",
        "Maqsadli auditoriya segmentatsiya", "Pixel o'rnatish",
        "Reklama formatlari", "Kontent yaratish reklamaga",
        "A/B testing", "Retargeting strategiyasi",
        "Google Ads asoslari", "Analitika (GA4)",
        "ROI hisoblash", "Budjet boshqaruvi",
        "Case study tahlil", "Loyiha: Kampaniya ishga tushirish",
    ],
}


def make_content(title: str, course_title: str) -> str:
    return f"""## {title}

**{course_title}** — bu darsda «{title}» mavzusi batafsil ko'rib chiqiladi.

### Asosiy tushunchalar

Ushbu mavzu professional IT mutaxassisi uchun zarur bilimlardan biri. Nazariy qismni o'qib, amaliyotda sinab ko'ring.

### Qo'shimcha resurslar

- Kod yozish panelida amaliyot qiling
- Hacker Lab terminalida buyruqlarni sinab ko'ring
- Jamoa bo'limida savol bering va tajriba ulashing

### Keyingi qadam

Mavzuni o'zlashtirgach, keyingi darsda yangi, chuqurroq bilimlar bilan davom etamiz.
"""


def main():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    updated = 0

    # 1. Aniq belgilangan kurslar
    for cid, lesson_list in LESSONS.items():
        rows = c.execute("SELECT id FROM lessons WHERE course_id=? ORDER BY order_num", (cid,)).fetchall()
        for i, row in enumerate(rows):
            if i < len(lesson_list):
                title, content = lesson_list[i]
                c.execute("UPDATE lessons SET title=?, content_html=? WHERE id=?", (title, content, row["id"]))
            updated += 1

    # 2. DIRECTION_TOPICS bilan qolgan kurslar
    rows_all = c.execute(
        """SELECT l.id, l.order_num, l.title as ltitle, c.id as cid, c.title as ctitle,
                  d.slug, d.name_uz
           FROM lessons l
           JOIN courses c ON c.id=l.course_id
           JOIN directions d ON d.id=c.direction_id
           WHERE c.id NOT IN (9,10,11,12) AND c.id NOT IN (?,?,?,?,?,?,?)""",
        tuple(LESSONS.keys())
    ).fetchall()

    course_offsets = {}
    for row in rows_all:
        cid = row["cid"]
        slug = row["slug"]
        topics = DIRECTION_TOPICS.get(slug, [])
        course_offsets[cid] = course_offsets.get(cid, 0)
        idx = course_offsets[cid]
        course_offsets[cid] += 1

        if idx < len(topics):
            title = topics[idx % len(topics)]
            content = make_content(title, row["ctitle"])
            c.execute("UPDATE lessons SET title=?, content_html=? WHERE id=?",
                      (title, content, row["id"]))
        else:
            content = make_content(row["ltitle"], row["ctitle"])
            c.execute("UPDATE lessons SET content_html=? WHERE id=?", (content, row["id"]))
        updated += 1

    conn.commit()
    conn.close()
    print(f"Jami yangilangan: {updated} ta dars")


if __name__ == "__main__":
    main()
