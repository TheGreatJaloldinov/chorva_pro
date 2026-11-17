# CHORVA PRO 2.0 — Web App / Telegram Mini App (boshlang‘ich integratsiya)

Ushbu versiya mavjud Aiogram + SQLAlchemy loyihasini saqlab qoladi va uning ma'lumotlar bazasiga FastAPI API hamda mobil-first React interfeysini qo‘shadi.

## Arxitektura

- `main.py` — mavjud Telegram bot va eslatma/backup worker'lari.
- `api/` — FastAPI, Telegram Mini App `initData` imzosini tekshirish va API endpointlari.
- `webapp/` — React + TypeScript + Vite mobil interfeysi.
- `run_all.py` — bot va API'ni bitta hosting servisida parallel ishga tushirish uchun.
- `app/db.py` — mavjud SQLAlchemy modellari; Web App shu modellardan foydalanadi.

## Lokal ishga tushirish

### 1. Python muhit

Loyiha ildizida:

```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

`.env.example` faylidan `.env` nusxa yarating va `BOT_TOKEN` kiriting. Lokal sinov uchun:

```env
BOT_TOKEN=... 
DATABASE_URL=sqlite+aiosqlite:///./chorva_pro.db
TIMEZONE=Asia/Tashkent
DATA_DIR=./data
APP_ENV=development
PORT=8000
WEBAPP_URL=
```

### 2. Backend API

Terminal 1:

```powershell
python api_main.py
```

API: `http://127.0.0.1:8000`  
API hujjatlari: `http://127.0.0.1:8000/docs`

Lokal testda `APP_ENV=development` bo‘lgani uchun frontend `X-Dev-Telegram-Id` header yuboradi. Bu faqat lokal test uchun. Ommaviy serverda `APP_ENV=production` bo‘lishi shart.

### 3. Web App

Terminal 2:

```powershell
cd webapp
npm install
npm run dev
```

Vite odatda `http://localhost:5173` manzilida ochiladi. API so‘rovlari `http://127.0.0.1:8000` ga proxy qilinadi.

### 4. Telegram bot

Terminal 3:

```powershell
python main.py
```

Telegram ichida Mini App tugmasini yoqish uchun `.env` ichidagi `WEBAPP_URL` qiymatiga HTTPS domen kiriting. Telegram Mini App oddiy `localhost` manzilini telefoningizdan ocholmaydi.

### 5. Bitta servis sifatida ishga tushirish

Hostingda (API va bot bir servisda):

```bash
python run_all.py
```

`PORT` hosting tomonidan beriladi. `DATABASE_URL` doimiy PostgreSQL manziliga sozlanishi kerak. SQLite faylini vaqtinchalik container diskida qoldirmang.

## Hozirgi Web App funksiyalari

- Telegram `initData` server tomonida HMAC orqali tekshiriladi.
- Dashboard: chorva soni, umumiy vazn, moliya natijasi va yem qoldig‘i.
- Chorvalar ro‘yxati, qidiruv va yangi chorva qo‘shish.
- Chorva vaznini Web App orqali yangilash.
- Yem ombori qoldig‘ini ko‘rish.
- Mavjud moliyaviy yozuvlarni ko‘rish.
- Telegram bot menyusida Web App ochish tugmasi (WEBAPP_URL berilganda).

## Keyingi ishlab chiqish bosqichlari

1. Oziqlantirish jadvalini Web App'dan yaratish/tahrirlash va eslatmalarni boshqarish.
2. Yem xaridi, FIFO sarfi va past qoldiq sozlamalarini to‘liq UI qilish.
3. Xarajat/daromad kiritish, sana kalendari va grafik hisobotlar.
4. Chorva profilining to‘liq tarixi, ko‘p rasm va hujjatlar.
5. Arxiv, sotish, backup/restore va ko‘p foydalanuvchili xo‘jaliklar.
6. PostgreSQL migratsiyalari va ishlab chiqarish xavfsizligi.

## Xavfsizlik eslatmalari

- `BOT_TOKEN` hech qachon frontend yoki GitHub repository'ga qo‘yilmaydi.
- `APP_ENV=development` rejimi faqat localhost uchun; production'da o‘chirilsin.
- Har bir API so‘rovi foydalanuvchi Telegram `initData` imzosini tekshiradi.
- Har bir DB so‘rovi `user_id` bilan cheklanadi.
- Web App HTTPS orqali ishlashi kerak.
