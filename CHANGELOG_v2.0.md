# CHORVA PRO 2.0 — Web App

## Ushbu build
- Mobil-first React Web App navigatsiyasi: bosh sahifa, chorva, ombor, oziqlantirish, moliya, hisobot.
- FastAPI backend: Telegram Mini App HMAC auth va faqat development rejimida demo header.
- Chorva qo'shish, jinsni turga qarab aniqlash, qidirish, arxiv/tiklash, vazn va qaydlar.
- Yem xaridi, FIFO bo'yicha ombordan sarflash, qoldiq chegarasi.
- Oziqlantirish jadvalini yaratish va faollashtirish/to'xtatish.
- Daromad/xarajat, oylik hisobot, Excel eksport, JSON backup.
- Telegram reminder worker bilan jadval itemlari `qty` formatiga moslashtirildi.

## Tekshiruv holati
- Python fayllari `compileall` bilan sintaksis tekshiruvidan o'tkazildi.
- Ushbu muhitda internet/DNS cheklovi sabab npm paketlarini o'rnatib Vite build va brauzer end-to-end sinovi bajarilmadi.
- Telegram token, real Telegram Mini App HTTPS domeni va production PostgreSQL ulanishi foydalanuvchi tomonidan sozlanishi kerak.
