# CHORVA PRO v2.4.2 — oziqlantirish jadvali 500 xatolik tuzatishi

## Aniqlangan sabab

Railway loglarida `POST /api/schedules` uchun ikkita noto'g'ri qiymat qayd etilgan:
- `animal_id` qiymati `null` bo'lganda `int(None)` chaqirilgan.
- Yem qatoridagi `quantity` qiymati `null` bo'lganda `float(None)` chaqirilgan.

## Tuzatishlar

- Chorva tanlanmagan bo'lsa, frontend saqlashni to'xtatib, tushunarli xabar ko'rsatadi.
- Kamida bitta vaqt, chorva va to'liq yem nomi/miqdori talab qilinadi.
- Backend `animal_id`, vaqtlar va yem miqdorlarini alohida tekshiradi; yaroqsiz payload uchun HTTP 422 qaytaradi, 500 emas.
- Jadvalni yaratish va tahrirlash bir xil validatsiyadan foydalanadi.
- Miqdor parseri `750 gr`, `0.75 kg`, `1.3 kg`, `1 kg 300 gr` yozuvlarini qabul qiladi.
- Bo'sh yoki chala yem qatorlari saqlanmaydi.

## Ma'lumotlar bazasi

Ushbu tuzatish yangi jadval yoki migratsiya talab qilmaydi. Mavjud Neon PostgreSQL ma'lumotlari o'zgartirilmaydi.
