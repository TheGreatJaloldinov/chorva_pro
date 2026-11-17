# CHORVA PRO v2.4.1 COMPLETE

Ushbu paket CHORVA PRO'ning avvalgi yaxshilanishlarini bitta loyihaga birlashtiradi:

- v2.2: oziqlantirish vaqtlari va miqdorlarini boshqarish, chorvani tahrirlash/arxivlash, yem va ombor amallari, profil avatarining bosh sahifadagi ko'rinishi;
- v2.3: Telegram orqali ozuqa vaqtidan oldingi eslatma, belgilangan vaqtdagi eslatma, kam qoldiq ogohlantirishi;
- v2.4: professional profil, shaxsiy ma'lumotlar, xo'jalik ma'lumotlari, til va bildirishnoma sozlamalari.

## Birlashtirilgan standart sozlamalar

- Ozuqa vaqtidan oldin: **15 daqiqa**.
- Belgilangan ozuqa vaqtida: **darhol**.
- Kam qoldiq chegarasi: **5 kg**.
- Kunlik hisobot: **o'chirilgan**. Foydalanuvchi profilidan yoqsa, har kuni 20:00 da (profil vaqt zonasida) yuboriladi.
- Vaqt zonasi: **Asia/Tashkent**.
- Xo'jalik rejimi: **bitta xo'jalik / foydalanuvchi**.

Eslatma oralig'i profil sozlamasidan 0, 5, 10, 15, 30 yoki 60 daqiqaga o'zgartiriladi. 0 tanlansa, oldindan eslatma o'chadi, lekin belgilangan vaqtdagi xabar qoladi.

## Loyihani GitHub'ga joylash

1. ZIP faylni kompyuterda oching.
2. Ichidagi `chorva_pro` papkasiga kiring.
3. Shu papka ichidagi barcha fayl va papkalarni (jumladan `api`, `app`, `webapp`, `Dockerfile`, `railway.json`, `requirements.txt`, `run_all.py`) mavjud GitHub repository'ning ildiziga joylang.
4. `.env` nomli haqiqiy maxfiy faylni GitHub'ga yuklamang. Faqat `.env.example` namunasi bo'lishi mumkin.
5. O'zgarishlarni Commit qiling. Railway GitHub deploy orqali qayta ishga tushadi.

## Railway Variables

Mavjud qiymatlarni saqlang:

- `BOT_TOKEN` — mavjud Telegram bot tokeni.
- `DATABASE_URL` — mavjud Neon PostgreSQL connection string.
- `WEBAPP_URL` — Telegram Mini App ochiladigan mavjud HTTPS URL.

Quyidagilarni tekshiring:

- `APP_ENV=production`
- `TIMEZONE=Asia/Tashkent`
- `PORT` — Railway tomonidan beriladi; qo'lda o'zgartirish shart emas.

`BOT_TOKEN` yoki `DATABASE_URL` qiymatlarini ZIP ichiga yozmang. Ularni chatga yubormang.

## Neon ma'lumotlarini saqlash

Ilova ishga tushganda `init_db()` mavjud bazada `CREATE TABLE IF NOT EXISTS` mazmunidagi SQLAlchemy `create_all` va `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` migratsiyalarini bajaradi. Yangi profil ustunlari va ogohlantirish jadvallari qo'shiladi. Mavjud foydalanuvchilar, chorva, yem partiyalari, sarf, jadval va moliyaviy yozuvlar o'chirilmaydi.

Telegram ID ustuni `BIGINT` bo'lib qoladi. `feed_types.low_stock_alert` uchun eski standart 10 kg qiymati 5 kg standartiga ko'chiriladi; boshqa maxsus qiymatlar o'zgarishsiz qoladi.

**Neon loyihasini o'chirmang va yangi bo'sh baza yaratmang.** Deploy'dan oldin Neon'dan backup olish tavsiya etiladi.

## Ogohlantirishlar qanday ishlaydi

- Telegram bot worker Railway servisida bot bilan birga ishlaydi.
- Oziqlantirish jadvali faol bo'lishi va chorva faol holatda turishi kerak.
- Oldindan eslatma foydalanuvchi profilidagi `reminder_minutes` qiymatiga muvofiq yuboriladi.
- Belgilangan vaqtda tasdiqlash tugmasi bo'lgan xabar yuboriladi.
- Yem qoldig'i uning ogohlantirish chegarasiga teng yoki undan pastga tushganda bir marta xabar yuboriladi. Qoldiq chegaradan oshgach, keyingi kamayish uchun ogohlantirish qayta faollashadi.
- Profil ichidagi umumiy chegara o'zgartirilsa, foydalanuvchining mavjud yem turlariga ham qo'llanadi. Yangi yem shu qiymat bilan yaratiladi.
- Kunlik hisobot sukut bo'yicha o'chirilgan. Yoqilgan taqdirda 20:00 da yuboriladi.

## Lokal ishga tushirish

Backend (loyiha ildizida):

```bash
python -m venv .venv
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

`.env.example` faylidan `.env` yarating, lokal uchun `APP_ENV=development`, `BOT_TOKEN`, `DATABASE_URL=sqlite+aiosqlite:///./chorva_pro.db` qiymatlarini sozlang.

Frontend:

```bash
cd webapp
npm install
npm run build
```

Bir servisda bot va API:

```bash
python run_all.py
```

Production'da SQLite emas, mavjud Neon PostgreSQL URL ishlatilishi kerak.

## Muhim tekshiruv eslatmasi

Ushbu muhitda Python fayllarining sintaksis tekshiruvi bajarildi. Paketlarni yuklab olish tarmoq vaqt chegarasiga yetgani sababli to'liq `npm run build`, Telegram orqali real xabar yuborish va Railway'dagi production sinovi bajarilmadi. Shuning uchun ZIP birlashtirilgan va deploy uchun tayyorlangan, lekin Railway deploy tugagach, real Telegram eslatmalari va profil saqlanishini tekshirish kerak.
