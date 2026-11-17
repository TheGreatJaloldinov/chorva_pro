# CHORVA PRO 2.0 — Web App + Telegram Mini App

## Imkoniyatlar
- Ko'p foydalanuvchi uchun Telegram `initData` HMAC tekshiruvi.
- Lokal sinov rejimi (`APP_ENV=development`, `X-Dev-Telegram-Id`).
- Chorva CRUD: Sigir, Buqa, Qo'chqor, Sovliq; jins avtomatik; ID avtomatik; arxiv/tiklash.
- Vazn yozuvlari va chorva qaydlari.
- Yem xaridlari, FIFO ombor sarfi, qoldiq ogohlantirish chegarasi.
- Oziqlantirish jadvali va vaqtlar.
- Daromad/xarajatlar, oylik hisobot, Excel eksport.
- Telegram bot reminder worker va kunlik backup worker (bot jarayoni ishlayotgan bo'lishi kerak).

## Lokal ishga tushirish (Windows 11)
1. Python 3.11+ va Node.js 20+ o'rnating.
2. Loyiha ildizida `.env.example` nusxasini `.env` deb saqlang.
3. `APP_ENV=development` qoldiring. `BOT_TOKEN`ni bot bildirishnomalari kerak bo'lganda kiriting.
4. Terminal:

```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

5. Frontend:

```powershell
cd webapp
npm install
npm run build
cd ..
```

6. Backend API:

```powershell
python api_main.py
```

Brauzer: http://localhost:8000
API hujjatlari: http://localhost:8000/docs

## Telegram bot + Web App birga
`WEBAPP_URL`ni HTTPS domeningizga qo'ying, botni BotFather orqali Mini App sifatida sozlang. API va bot polling bir processda ishlashi uchun:

```powershell
python run_all.py
```

Bot token bo'lmasa, `run_all.py` ishlamaydi. Web API lokal demo rejimida alohida `python api_main.py` bilan ishlaydi.

## Railway / VPS deploy
- `APP_ENV=production` bo'lishi shart.
- `BOT_TOKEN` maxfiy environment variable sifatida kiritiladi.
- `DATABASE_URL` persistent PostgreSQL ulanishi bo'lishi tavsiya etiladi.
- `WEBAPP_URL` HTTPS manzil bo'lishi kerak.
- `VITE_DEV_TELEGRAM_ID` faqat lokal frontend sinovi uchun. Production build'da bu development header ishlatilmasin.
- API va bot pollingni bitta containerda ishlatish uchun `python run_all.py` start command. Yoki API va botni alohida worker sifatida deploy qiling.

## Muhim cheklovlar
- Web App ichidagi jadvalni saqlash API'da ishlaydi. Telegram eslatmalari bot worker, haqiqiy BOT_TOKEN va Telegram foydalanuvchisi botga `/start` qilgan bo'lishini talab qiladi.
- Telegram bot reminders'ni qabul qilishi uchun foydalanuvchi botni bloklamagan bo'lishi kerak.
- SQLite lokal sinov uchun. Bir nechta foydalanuvchi va production uchun PostgreSQL ishlating.
- Excel eksport API: `GET /api/reports/export`.
- API auth: Telegram Mini App `initData` tekshiriladi; development header faqat APP_ENV=development holatida ruxsat.

## Render + Neon deploy (production)

- Connect the GitHub repository to Render as a **Web Service**.
- Build command: `pip install -r requirements.txt && cd webapp && npm install && npm run build`
- Start command: `python api_main.py`
- Add environment variables: `BOT_TOKEN`, `DATABASE_URL` (Neon connection string), `TIMEZONE=Asia/Tashkent`, `APP_ENV=production`, `PORT=8000`, `CORS_ORIGINS=*`, `DATA_DIR=./data`, `PYTHONUNBUFFERED=1`.
- The app automatically converts ordinary `postgresql://` / `postgres://` Neon URLs to SQLAlchemy's asyncpg URL and normalizes SSL query parameters.
- Deploy and verify `/api/health`.

Do not publish BOT_TOKEN or DATABASE_URL. If either was exposed, rotate it before deploying.
