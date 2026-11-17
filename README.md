# CHORVA PRO v1.2

Telegram chorvachilik boshqaruv boti. Python 3.11+, Aiogram 3, SQLAlchemy async.

## Windows'da ishga tushirish

1. Loyihani oching va terminalda virtual muhit yarating:

```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

2. `.env.example` faylidan `.env` nusxa yarating va `BOT_TOKEN` qiymatini kiriting. Lokal test uchun SQLite URL ishlatilishi mumkin:

```env
BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
DATABASE_URL=sqlite+aiosqlite:///./chorva_pro.db
TIMEZONE=Asia/Tashkent
DATA_DIR=./data
```

3. Botni ishga tushiring:

```powershell
python main.py
```

## Sana tanlash
Xarid, yem xaridi, sotuv, xarajat va daromad sanalari kalendar tugmalari orqali tanlanadi. Qo‘lda sana yozish shart emas.

## Oziqlantirish vaqtlari
Jadval yaratishda vaqt tugmalarini tanlang. Bir nechta vaqtni belgilash mumkin. Noodatiy vaqt uchun `Boshqa vaqtni kiritish` tugmasidan foydalaning.

## Eslatma
Bot foydalanuvchi tomonidan yuborilgan matnlarni faqat Telegram API ruxsat bergan holatlarda o‘chira oladi. Boshqa foydalanuvchilarning yoki oldingi barcha chat xabarlarini tozalash imkoni yo‘q.
