# CHORVA PRO 2.0-alpha — Web App integratsiyasi

## Qo‘shildi
- Mavjud SQLAlchemy modellari bilan ishlaydigan FastAPI API.
- Telegram Mini App `initData` HMAC tekshiruvi.
- Lokal ishlab chiqish uchun faqat `APP_ENV=development` rejimida ishlaydigan test identifikatori.
- Mobil-first React + TypeScript + Vite interfeysi.
- Dashboard, chorva ro‘yxati/qidiruvi, chorva qo‘shish, vazn kiritish, yem qoldig‘i va moliya ko‘rinishi.
- Bot asosiy menyusida `WEBAPP_URL` berilganda Mini App ochish tugmasi.
- `run_all.py` orqali bot va API'ni bitta servisda ishga tushirish.

## Hozircha keyingi bosqichda
- Web App ichidan oziqlantirish jadvalini to‘liq boshqarish.
- Yem sarfini Web App'dan tasdiqlash va FIFO tranzaksiyalari.
- Moliyaviy yozuvlarni UI orqali qo‘shish/tahrirlash.
- Kalendar komponenti, hisobot grafiklari, Excel va backup UI.
- Ko‘p rasm/hujjat yuklash va profil tarixining barcha bo‘limlari.
- Production PostgreSQL migratsiyalari va to‘liq deploy sinovi.
