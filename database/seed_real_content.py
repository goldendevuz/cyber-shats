# -*- coding: utf-8 -*-
"""
Har bir dars mavzusiga mos HAQIQIY mazmun yozish skripti.
Mavzu nomiga qarab tegishli content yaratadi.
"""
import sqlite3, os, re

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cyber_shats.db")

# Mavzuga mos haqiqiy mazmunlar lug'ati
CONTENT_MAP = {
    # AI / ML
    "kirish va muhit sozlash": """## Kirish va Muhit Sozlash

Bu kursda kerakli dasturiy ta'minotni o'rnatamiz.

### O'rnatish
```bash
pip install numpy pandas scikit-learn matplotlib jupyter
```

### Jupyter Notebook ishga tushirish
```bash
jupyter notebook
```

### Python versiyasini tekshirish
```python
import sys
print(sys.version)  # 3.9+ tavsiya etiladi

import numpy as np
import pandas as pd
print("NumPy:", np.__version__)
print("Pandas:", pd.__version__)
```

### Birinchi dastur
```python
import numpy as np
a = np.array([1, 2, 3, 4, 5])
print("Massiv:", a)
print("O'rtacha:", a.mean())
print("Standart og'ish:", a.std())
```
""",
    "numpy asoslari": """## NumPy — Raqamli Hisoblash Kutubxonasi

NumPy — Python'da eng asosiy ilmiy hisoblash kutubxonasi.

### Massiv yaratish
```python
import numpy as np

# 1D massiv
a = np.array([1, 2, 3, 4, 5])

# 2D massiv (matritsa)
m = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]])

# Avtomatik massivlar
zeros = np.zeros((3, 4))      # nollar
ones  = np.ones((2, 3))       # birlar
rng   = np.arange(0, 10, 2)  # 0, 2, 4, 6, 8
lin   = np.linspace(0, 1, 5)  # teng oraliqli 5 ta son
```

### Matematik amallar
```python
a = np.array([1, 2, 3, 4])
print(a + 10)        # [11 12 13 14]
print(a ** 2)        # [1  4  9 16]
print(np.sqrt(a))    # [1, 1.41, 1.73, 2.0]
print(a.sum())       # 10
print(a.mean())      # 2.5
print(a.max())       # 4
print(a.argmax())    # 3 (indeks)
```

### Matritsa ko'paytmasi
```python
A = np.array([[1, 2], [3, 4]])
B = np.array([[5, 6], [7, 8]])
print(A @ B)        # matritsalar ko'paytmasi
print(A.T)          # transpozitsiya
print(np.linalg.det(A))  # determinant
```
""",
    "pandas asoslari": """## Pandas — Ma'lumotlar Tahlili

Pandas — tuzilgan ma'lumotlar bilan ishlash uchun eng kuchli Python kutubxonasi.

### DataFrame yaratish
```python
import pandas as pd

# Lug'atdan
df = pd.DataFrame({
    'ism':   ['Ali', 'Vali', 'Guli'],
    'yosh':  [25, 30, 22],
    'shahar':['Toshkent', 'Samarqand', 'Buxoro']
})
print(df)
print(df.dtypes)
print(df.describe())
```

### Asosiy amallar
```python
# Ustun tanlash
print(df['ism'])
print(df[['ism', 'yosh']])

# Filtrlash
katta = df[df['yosh'] > 24]
toshkent = df[df['shahar'] == 'Toshkent']

# Yangi ustun
df['yosh2'] = df['yosh'] ** 2

# Saralash
df_sorted = df.sort_values('yosh', ascending=False)

# Guruhlash
df.groupby('shahar')['yosh'].mean()
```

### CSV o'qish/yozish
```python
df = pd.read_csv('data.csv', encoding='utf-8')
df.to_csv('natija.csv', index=False)
df.isnull().sum()   # yo'qolgan qiymatlar
df.dropna()         # tozalash
df.fillna(0)        # to'ldirish
```
""",
    "vizualizatsiya": """## Ma'lumotlarni Vizualizatsiya qilish

### Matplotlib bilan asosiy grafiklar
```python
import matplotlib.pyplot as plt
import numpy as np

x = np.linspace(0, 2*np.pi, 100)

# Chiziqli grafik
plt.figure(figsize=(10, 4))
plt.plot(x, np.sin(x), label='sin(x)', color='blue')
plt.plot(x, np.cos(x), label='cos(x)', color='red')
plt.xlabel('x')
plt.ylabel('y')
plt.title('Trigonometrik funksiyalar')
plt.legend()
plt.grid(True)
plt.show()
```

### Seaborn bilan professional grafiklar
```python
import seaborn as sns
import pandas as pd

# O'rnatilgan dataset
df = sns.load_dataset('iris')

# Juftlik grafigi
sns.pairplot(df, hue='species')
plt.show()

# Issiqlik xaritasi
corr = df.corr(numeric_only=True)
sns.heatmap(corr, annot=True, cmap='coolwarm')
plt.title('Korrelyatsiya matritsasi')
plt.show()
```

### Bar va Pie grafiklar
```python
kategoriyalar = ['A', 'B', 'C', 'D']
qiymatlar = [40, 30, 20, 10]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
ax1.bar(kategoriyalar, qiymatlar, color=['blue','green','red','gold'])
ax1.set_title('Bar grafik')
ax2.pie(qiymatlar, labels=kategoriyalar, autopct='%1.1f%%')
ax2.set_title('Pie grafik')
plt.show()
```
""",
    "linear regression": """## Chiziqli Regressiya (Linear Regression)

Regressiya — sonli natijani bashorat qilish uchun ishlatiladigan ML algoritmi.

### Nazariy asos
`y = w₀ + w₁x₁ + w₂x₂ + ... + wₙxₙ`

Maqsad: **xato funksiyasi (MSE)** ni minimallashtrish:
`MSE = (1/n) Σ(yᵢ - ŷᵢ)²`

### Sklearn bilan
```python
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
import numpy as np

# Ma'lumot yaratish
X = np.random.randn(100, 2)
y = 3*X[:,0] + 2*X[:,1] + np.random.randn(100)*0.5

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

model = LinearRegression()
model.fit(X_train, y_train)

y_pred = model.predict(X_test)
print(f"R² score: {r2_score(y_test, y_pred):.4f}")
print(f"MSE: {mean_squared_error(y_test, y_pred):.4f}")
print(f"Koeffitsientlar: {model.coef_}")
print(f"Bo'sh hadda: {model.intercept_:.4f}")
```
""",
    "logistic regression": """## Logistik Regressiya (Klassifikatsiya)

Ikki yoki ko'p sinfli klassifikatsiya uchun ishlatiladi.

### Sigmoid funksiyasi
`σ(z) = 1 / (1 + e⁻ᶻ)` — natijani 0 va 1 oralig'iga keltiradi.

### Python bilan
```python
from sklearn.linear_model import LogisticRegression
from sklearn.datasets import load_breast_cancer
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
import seaborn as sns, matplotlib.pyplot as plt

data = load_breast_cancer()
X_train, X_test, y_train, y_test = train_test_split(
    data.data, data.target, test_size=0.2, random_state=42)

model = LogisticRegression(max_iter=1000)
model.fit(X_train, y_train)

y_pred = model.predict(X_test)
print(classification_report(y_test, y_pred))

# Confusion matrix
cm = confusion_matrix(y_test, y_pred)
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues')
plt.title('Confusion Matrix')
plt.show()
```

### Muhim metrikalar
- **Precision**: aniqlik (TP / (TP+FP))
- **Recall**: to'liqlik (TP / (TP+FN))
- **F1-score**: ikkalasining harmonik o'rtachasi
- **AUC-ROC**: model sifatini umumiy baholash
""",
    "decision tree": """## Decision Tree — Qarorlar Daraxti

Qarorlar daraxti — ma'lumotlarni savollar orqali bo'ladigan, o'qilishi oson ML modeli.

### Ishlash printsipi
1. Eng yaxshi bo'luvchi xususiyatni topadi (Gini/Entropy asosida)
2. Rekursiv ravishda bo'ladi
3. Barg tugunlarda natijani qaytaradi

```python
from sklearn.tree import DecisionTreeClassifier, export_text, plot_tree
from sklearn.datasets import load_iris
import matplotlib.pyplot as plt

iris = load_iris()
X, y = iris.data, iris.target

dt = DecisionTreeClassifier(max_depth=3, random_state=42)
dt.fit(X, y)

print(f"Aniqlik: {dt.score(X, y):.4f}")

# Daraxti chizish
plt.figure(figsize=(15, 8))
plot_tree(dt, feature_names=iris.feature_names,
          class_names=iris.target_names, filled=True)
plt.title("Qarorlar Daraxti")
plt.show()

# Xususiyatlar ahamiyati
for name, imp in zip(iris.feature_names, dt.feature_importances_):
    print(f"  {name}: {imp:.4f}")
```

### Overfitting muammosi
```python
# max_depth, min_samples_split parametrlari bilan nazorat
dt_pruned = DecisionTreeClassifier(
    max_depth=4, min_samples_split=10, min_samples_leaf=5)
```
""",
    "random forest": """## Random Forest — Tasodifiy O'rmon

Ko'p qarorlar daraxtlarini birlashtirgan kuchli ensemble metod.

### Nima uchun kuchli?
- Har bir daraxt tasodifiy ma'lumotlarda o'qitiladi (Bootstrap)
- Har bir bo'linishda tasodifiy xususiyatlar tanlanadi
- Natija — ko'pchilik ovozi (klassifikatsiya) yoki o'rtacha (regressiya)

```python
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score
from sklearn.datasets import load_digits
import numpy as np

digits = load_digits()
X, y = digits.data, digits.target

rf = RandomForestClassifier(
    n_estimators=100,    # daraxtlar soni
    max_depth=10,        # maksimal chuqurlik
    random_state=42,
    n_jobs=-1            # barcha protsessorlardan foydalanish
)

# Cross-validation
scores = cross_val_score(rf, X, y, cv=5)
print(f"CV aniqlik: {scores.mean():.4f} ± {scores.std():.4f}")

rf.fit(X, y)

# Xususiyatlar ahamiyati
importances = rf.feature_importances_
top_idx = np.argsort(importances)[-10:]
print("Eng muhim 10 ta xususiyat:", top_idx)
```

### OOB (Out-of-Bag) baholash
```python
rf_oob = RandomForestClassifier(n_estimators=100, oob_score=True)
rf_oob.fit(X, y)
print(f"OOB aniqlik: {rf_oob.oob_score_:.4f}")
```
""",
    "svm va knn": """## SVM va KNN — Ikkita Kuchli Algoritm

### SVM (Support Vector Machine)
Sinflar orasidagi maksimal chegara (hyperplane) ni topadi.

```python
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler
from sklearn.datasets import load_wine
from sklearn.model_selection import train_test_split

wine = load_wine()
X_train, X_test, y_train, y_test = train_test_split(
    wine.data, wine.target, test_size=0.2, random_state=42)

# SVM uchun normalizatsiya ZARURIY
scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)
X_test  = scaler.transform(X_test)

svm = SVC(kernel='rbf', C=1.0, gamma='scale')
svm.fit(X_train, y_train)
print(f"SVM aniqlik: {svm.score(X_test, y_test):.4f}")
```

### KNN (K-Nearest Neighbors)
Yangi nuqtaning eng yaqin k ta qo'shnisi asosida sinf aniqlanadi.

```python
from sklearn.neighbors import KNeighborsClassifier

# Optimal K topish
best_k, best_score = 1, 0
for k in range(1, 21):
    knn = KNeighborsClassifier(n_neighbors=k)
    score = cross_val_score(knn, X_train, y_train, cv=5).mean()
    if score > best_score:
        best_k, best_score = k, score

print(f"Optimal K: {best_k}, CV aniqlik: {best_score:.4f}")

knn_final = KNeighborsClassifier(n_neighbors=best_k)
knn_final.fit(X_train, y_train)
```
""",
    "klasterizatsiya": """## Klasterizatsiya — Belgilanmagan O'qitish

### K-Means algoritmi
Ma'lumotlarni K ta guruhga bo'ladi.

```python
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
import numpy as np

# Ma'lumot yaratish
from sklearn.datasets import make_blobs
X, y_true = make_blobs(n_samples=300, centers=4, random_state=42)

# Elbow usuli — optimal K topish
inertias = []
K_range = range(1, 11)
for k in K_range:
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    km.fit(X)
    inertias.append(km.inertia_)

plt.plot(K_range, inertias, 'bo-')
plt.xlabel('K')
plt.ylabel('Inertia')
plt.title('Elbow usuli')
plt.show()

# K=4 bilan klasterizatsiya
km = KMeans(n_clusters=4, random_state=42, n_init=10)
labels = km.fit_predict(X)

plt.scatter(X[:,0], X[:,1], c=labels, cmap='viridis')
plt.scatter(km.cluster_centers_[:,0], km.cluster_centers_[:,1],
            c='red', marker='*', s=300, label='Markazlar')
plt.legend()
plt.show()
```
""",
    "html semantika": """## HTML Semantika — To'g'ri Belgilash

### Nima uchun semantika muhim?
- Qidiruv tizimlari (SEO) uchun
- Ekran o'quvchilar (accessibility) uchun
- Kod o'qilishi uchun

### Asosiy semantik teglar
```html
<!DOCTYPE html>
<html lang="uz">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mening saytim</title>
</head>
<body>
    <header>
        <nav>
            <ul>
                <li><a href="/">Bosh sahifa</a></li>
                <li><a href="/haqida">Haqida</a></li>
                <li><a href="/aloqa">Aloqa</a></li>
            </ul>
        </nav>
    </header>
    <main>
        <article>
            <h1>Maqola sarlavhasi</h1>
            <section>
                <h2>Birinchi bo'lim</h2>
                <p>Mazmun matni...</p>
                <figure>
                    <img src="rasm.jpg" alt="Rasmning ta'rifi">
                    <figcaption>Rasm tavsifi</figcaption>
                </figure>
            </section>
        </article>
        <aside>
            <h3>Qo'shimcha ma'lumot</h3>
        </aside>
    </main>
    <footer>
        <p>&copy; 2026 Mening Saytim</p>
    </footer>
</body>
</html>
```

### Div vs Semantik teglar
```html
<!-- NOTO'G'RI -->
<div class="header">...</div>
<div class="nav">...</div>

<!-- TO'G'RI -->
<header>...</header>
<nav>...</nav>
```
""",
    "css flexbox": """## CSS Flexbox — Zamonaviy Layout Tizimi

Flexbox — bir o'lchovli tartib uchun eng kuchli CSS vositasi.

### Asosiy xususiyatlar
```css
.container {
    display: flex;

    /* Gorizontal yo'nalish */
    justify-content: flex-start;  /* boshidan */
    justify-content: flex-end;    /* oxiridan */
    justify-content: center;      /* markazda */
    justify-content: space-between; /* oralig'ida */
    justify-content: space-around;  /* atrofida */

    /* Vertikal yo'nalish */
    align-items: stretch;  /* cho'zilgan (default) */
    align-items: center;   /* markazda */
    align-items: flex-start;
    align-items: flex-end;

    /* Qo'shimcha parametrlar */
    flex-direction: row;    /* qator (default) */
    flex-direction: column; /* ustun */
    flex-wrap: wrap;        /* qatorlarga bo'linadi */
    gap: 16px;              /* elementlar orasidagi masofa */
}

.item {
    flex: 1;         /* teng bo'linish */
    flex: 0 0 200px; /* qat'iy 200px */
    order: 2;        /* tartib */
    align-self: center; /* alohida moslash */
}
```

### Amaliy misollar
```css
/* Navigation bar */
.navbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0 20px;
}

/* Sahifa markazlash */
.hero {
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 100vh;
}

/* Karta grid */
.cards {
    display: flex;
    flex-wrap: wrap;
    gap: 20px;
}
.card { flex: 1 1 280px; }
```
""",
    "css grid": """## CSS Grid — Ikki O'lchovli Layout

Grid — ham qator, ham ustun bo'yicha to'liq nazorat beradi.

### Asosiy tushunchalar
```css
.container {
    display: grid;

    /* Ustunlar */
    grid-template-columns: 200px 1fr 1fr;
    grid-template-columns: repeat(3, 1fr);     /* 3 ta teng ustun */
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));

    /* Qatorlar */
    grid-template-rows: auto 1fr auto;

    /* Oraliq */
    gap: 20px;
    column-gap: 20px;
    row-gap: 10px;
}

/* Element joylashuvi */
.header { grid-column: 1 / -1; } /* butun qator */
.sidebar { grid-row: 2 / 4; }    /* 2-3-qatorlar */
.main { grid-area: 2 / 2 / 4 / 4; } /* row-start/col-start/row-end/col-end */
```

### Named Grid Areas
```css
.layout {
    display: grid;
    grid-template-areas:
        "header header header"
        "sidebar main main"
        "footer footer footer";
    grid-template-columns: 250px 1fr 1fr;
    grid-template-rows: 60px 1fr 60px;
    min-height: 100vh;
}

.header  { grid-area: header; }
.sidebar { grid-area: sidebar; }
.main    { grid-area: main; }
.footer  { grid-area: footer; }
```

### Responsive Grid
```css
.gallery {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 16px;
}
```
""",
    "javascript es6+": """## JavaScript ES6+ — Zamonaviy Xususiyatlar

### let, const, var farqlari
```javascript
var x = 1;    // function scope, hoisting
let y = 2;    // block scope, qayta o'zgartiriladi
const z = 3;  // block scope, o'zgarmas

// Const bilan object/array o'zgartiriladi
const user = { ism: 'Ali' };
user.yosh = 25;  // OK — ref o'zgarmadi
```

### Destructuring
```javascript
// Array
const [a, b, ...rest] = [1, 2, 3, 4, 5];

// Object
const { ism, yosh, shahar = 'Toshkent' } = user;

// Function parametrlarida
function greet({ ism, yosh = 18 }) {
    return `Salom, ${ism}! (${yosh} yosh)`;
}
```

### Spread va Rest
```javascript
const arr1 = [1, 2, 3];
const arr2 = [...arr1, 4, 5];    // [1,2,3,4,5]
const obj2 = { ...user, rol: 'admin' };

function sum(...numbers) {
    return numbers.reduce((a, b) => a + b, 0);
}
```

### Optional Chaining va Nullish Coalescing
```javascript
const city = user?.address?.city;    // xato bermaydi
const name = user.ism ?? 'Noma\'lum'; // null/undefined bo'lsa
```

### Template Literals
```javascript
const html = `
    <div class="user">
        <h2>${user.ism}</h2>
        <p>${user.yosh} yoshda</p>
    </div>
`;
```
""",
    "dom boshqaruvi": """## DOM Boshqaruvi — Sahifa Elementlarini Nazorat Qilish

### Elementlarni topish
```javascript
// ID bo'yicha
const header = document.getElementById('sarlavha');

// CSS selektor (birinchi)
const btn = document.querySelector('.tugma');

// CSS selektor (barchasi)
const items = document.querySelectorAll('li.faol');
```

### Mazmun va stil o'zgartirish
```javascript
// Matn
header.textContent = 'Yangi sarlavha';  // xavfsiz
header.innerHTML = '<em>Kursiv</em>';   // HTML qo'shiladi

// Atributlar
img.src = 'yangi.jpg';
link.href = '#yangi';
btn.disabled = true;

// Stil
el.style.color = '#00ff41';
el.style.display = 'none';

// CSS klasslari
el.classList.add('faol');
el.classList.remove('yashirin');
el.classList.toggle('tanlangan');
el.classList.contains('faol');  // true/false
```

### Yangi element yaratish va qo'shish
```javascript
const div = document.createElement('div');
div.className = 'karta';
div.innerHTML = `<h3>Sarlavha</h3><p>Mazmun</p>`;

// Qo'shish usullari
parent.appendChild(div);           // oxiriga
parent.prepend(div);                // boshiga
parent.insertBefore(div, sibling); // oldiga
el.remove();                        // o'chirish
```

### Dataset — HTML5 custom data attributes
```javascript
// HTML: <div data-user-id="42" data-role="admin">
const div = document.querySelector('[data-user-id]');
console.log(div.dataset.userId);  // "42"
console.log(div.dataset.role);    // "admin"
div.dataset.status = 'online';    // yangi qo'shish
```
""",
    "async/await va fetch": """## Async/Await va Fetch API

### Promise asoslari
```javascript
function kechikish(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

kechikish(1000).then(() => console.log('1 soniya o\'tdi'));
```

### Async/Await
```javascript
async function ma_lumot_olish(url) {
    try {
        const response = await fetch(url);

        if (!response.ok) {
            throw new Error(`HTTP xato: ${response.status}`);
        }

        const data = await response.json();
        return data;
    } catch (xato) {
        console.error('Xato yuz berdi:', xato.message);
        throw xato;
    }
}

// GET so'rov
async function foydalanuvchilarni_ol() {
    const users = await ma_lumot_olish('/api/users');
    console.log('Foydalanuvchilar:', users);
}
```

### POST so'rov
```javascript
async function yangi_foydalanuvchi(data) {
    const response = await fetch('/api/users', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(data)
    });
    return response.json();
}
```

### Parallel so'rovlar
```javascript
async function barchani_ol() {
    const [users, posts, comments] = await Promise.all([
        fetch('/api/users').then(r => r.json()),
        fetch('/api/posts').then(r => r.json()),
        fetch('/api/comments').then(r => r.json()),
    ]);
    return { users, posts, comments };
}
```
""",
    "osisni sozlash": """## Network Xavfsizligi — OSI va TCP/IP

### OSI Modeli — 7 qatlam
| Qatlam | Nomi | Protokollar | Funksiya |
|--------|------|-------------|---------|
| 7 | Application | HTTP, FTP, DNS | Foydalanuvchi ilovalar |
| 6 | Presentation | SSL/TLS, JPEG | Kodlash, shifrlash |
| 5 | Session | RPC, NetBIOS | Seans boshqaruvi |
| 4 | Transport | TCP, UDP | Port, ishonchlilik |
| 3 | Network | IP, ICMP | Marshrutizatsiya |
| 2 | Data Link | Ethernet, MAC | Kadr, switch |
| 1 | Physical | Kabel, Wi-Fi | Bit uzatish |

### TCP vs UDP
```
TCP (ishonchli):
  - 3-tomonlama qo'l siqish (SYN, SYN-ACK, ACK)
  - Paketlar qayta yuboriladi
  - HTTP/S, FTP, SSH, email

UDP (tez):
  - Ulanishsiz
  - Paketlar yo'qolishi mumkin
  - Video/audio stream, DNS, o'yinlar
```

### Port raqamlari (muhim)
```
20/21 — FTP
22   — SSH
23   — Telnet (xavfli!)
25   — SMTP (email)
53   — DNS
80   — HTTP
443  — HTTPS
3306 — MySQL
5432 — PostgreSQL
27017— MongoDB
```
""",
    "ip manzillash": """## IP Manzillash va Subneting

### IPv4 tuzilishi
```
192.168.1.100
  |   |  |  |
  Oktet1.2.3.4  (har biri 0-255)
```

### Maxsus IP manzillar
```
127.0.0.1        — loopback (o'z kompyuter)
10.0.0.0/8       — xususiy Class A
172.16.0.0/12    — xususiy Class B
192.168.0.0/16   — xususiy Class C
0.0.0.0          — barcha interfeys
255.255.255.255  — broadcast
```

### CIDR va Subnet Mask
```
/24 = 255.255.255.0   = 254 host
/25 = 255.255.255.128 = 126 host
/26 = 255.255.255.192 = 62 host
/30 = 255.255.255.252 = 2 host (P2P)
```

### Subneting misol: 192.168.10.0/26
```python
# 192.168.10.0/26 = 64 ta manzil
# Tarmoq:    192.168.10.0
# Birinchi:  192.168.10.1
# Oxirgi:    192.168.10.62
# Broadcast: 192.168.10.63
# Hostlar:   62 ta

import ipaddress
net = ipaddress.IPv4Network('192.168.10.0/26')
print(f"Tarmoq: {net.network_address}")
print(f"Broadcast: {net.broadcast_address}")
print(f"Hostlar: {net.num_addresses - 2}")
```

### nmap bilan tarmoq skanerlash (etik)
```bash
nmap -sn 192.168.1.0/24     # Ping scan
nmap -sV 192.168.1.1        # Versiya aniqlash
nmap -p 1-1000 192.168.1.1  # Port skanerlash
```
""",
}


def find_matching_content(title: str) -> str | None:
    """Dars nomiga mos content topadi."""
    t = title.lower().strip()
    for key, content in CONTENT_MAP.items():
        if key in t or t in key:
            return content
    # Qisman moslik
    for key, content in CONTENT_MAP.items():
        key_words = key.split()
        if any(w in t for w in key_words if len(w) > 3):
            return content
    return None


def generate_content(title: str, course_title: str, direction_slug: str) -> str:
    """Mavzuga mos haqiqiy mazmun yaratadi."""
    # Aniq mavzularni topib qaytaradi
    match = find_matching_content(title)
    if match:
        return match
    
    # Yo'nalishga mos generik lekin mazmunli content
    slug = direction_slug.lower()
    t = title.lower()
    
    if 'python' in slug or 'python' in t:
        return f"""## {title}

Bu darsda Python dasturlashning muhim bo'limi o'rganiladi.

### Asosiy tushunchalar

```python
# {title} mavzusi bo'yicha amaliy kod

def amaliyot():
    \"\"\"Bu funksiya {title} mavzusini o'rganish uchun\"\"\"
    pass

# O'zgaruvchilar
data = []
result = None

# Tsikl namunasi
for i in range(10):
    data.append(i ** 2)

print(f"Ma'lumotlar: {{data}}")
print(f"Jami: {{sum(data)}}")
```

### Asosiy qoidalar
- Kodni izohlar bilan yozing
- Funksiyalarni kichik va bir maqsadli qiling
- Xatolarni `try/except` bilan ushlang

### Mashq
Yuqoridagi kodni o'zingiz bajaring va natijani kuzating.
"""
    
    if 'web' in slug or 'javascript' in slug:
        return f"""## {title}

Veb dasturlashning muhim mavzusi — {title}.

### HTML/CSS Namuna
```html
<!-- {title} uchun namuna -->
<div class="container">
    <h2>{title}</h2>
    <p>Bu element {title} mavzusini namoyish etadi.</p>
    <button id="btn">Bosing</button>
</div>
```

```css
.container {{
    max-width: 800px;
    margin: 0 auto;
    padding: 20px;
    font-family: 'Segoe UI', sans-serif;
}}

.container h2 {{
    color: #1e90ff;
    border-bottom: 2px solid #1e90ff;
    padding-bottom: 8px;
}}
```

```javascript
// JavaScript qismi
const btn = document.getElementById('btn');
btn.addEventListener('click', function() {{
    console.log('{title} namunasi ishladi!');
    alert('Muvaffaqiyatli!');
}});
```

### Amaliyot
Kodni kod yozish panelida sinab ko'ring.
"""
    
    if 'cyber' in slug or 'security' in slug or 'hack' in slug:
        return f"""## {title}

Cyber Xavfsizlik sohasida muhim mavzu: **{title}**

### Nazariy asos

Xavfsizlik sohasida {title} quyidagi holatlarda muhim rol o'ynaydi:
- Tarmoq himoyasida
- Ma'lumotlar xavfsizligida
- Tizimlarni baholashda

### Amaliy buyruqlar (Linux/Kali)
```bash
# {title} uchun amaliy mashq
whoami
uname -a
ip a                    # tarmoq interfeyslari

# Fayl tizimi tekshiruvi
ls -la /var/log/
cat /etc/hosts
netstat -tulpn          # ochiq portlar
ss -tulpn               # zamonaviy usul
```

### Amaliyot vazifasi
Hacker Lab terminalida yuqoridagi buyruqlarni bajaring va natijani tahlil qiling.

### Muhim eslatma
Barcha amaliyotlar faqat ruxsat berilgan tizimlarda bajarilishi kerak!
"""
    
    # Umumiy professional content
    return f"""## {title}

**{course_title}** kursining ushbu darsida **{title}** mavzusi atroflica ko'rib chiqiladi.

### Kirish

{title} — bu sohadagi fundamental tushunchalardan biri bo'lib, professional darajada ishlash uchun zarur bilimdir.

### Asosiy tushunchalar

**Nazariy qism:**
Mavzuni to'liq tushunish uchun quyidagi asosiy nuqtalarga e'tibor bering:

1. **Asoslar** — {title} nima va nima uchun muhim
2. **Amaliyot** — Real vaziyatlarda qanday ishlatiladi
3. **Eng yaxshi amaliyotlar** — Professional standartlar

### Amaliy mashq

```
# {title} bo'yicha amaliyot
# Kod yozish panelida sinab ko'ring
# Hacker Lab terminalida buyruqlarni bajaring
```

### Tavsiya etilgan resurslar

- Rasmiy dokumentatsiya va qo'llanmalar
- Amaliy loyihalar va mashqlar
- Hamjamiyat forumi — savol va javoblar

### Keyingi qadam

Bu mavzuni o'zlashtirib, keyingi darsda yanada chuqur bilimlar o'rganamiz.
"""


def main():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    rows = c.execute("""
        SELECT l.id, l.title, l.order_num, c.title as ctitle, d.slug
        FROM lessons l
        JOIN courses c ON c.id = l.course_id
        JOIN directions d ON d.id = c.direction_id
        WHERE l.content_html LIKE '%ushbu darsda%'
        ORDER BY d.slug, c.id, l.order_num
    """).fetchall()
    
    updated = 0
    for row in rows:
        content = generate_content(row["title"], row["ctitle"], row["slug"])
        c.execute("UPDATE lessons SET content_html=? WHERE id=?", (content, row["id"]))
        updated += 1
        if updated % 50 == 0:
            conn.commit()
            print(f"  {updated}/{len(rows)} yangilandi...")
    
    conn.commit()
    conn.close()
    print(f"\nJami {updated} ta dars yangilandi!")


if __name__ == "__main__":
    main()
