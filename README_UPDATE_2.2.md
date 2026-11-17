# CHORVA PRO 2.2 yangilash

Ushbu ZIP mavjud `chorva_pro` loyihasining ustiga yangilash uchun mo‘ljallangan.

1. ZIP ichidagi `chorva_pro` papkasi tarkibini GitHub repository ildiziga yuklang.
2. Mavjud fayllarni yangilang, yangi `CHANGELOG_v2.2.md` va `README_UPDATE_2.2.md` fayllarini qo‘shing.
3. `app/db.py` dagi BIGINT migratsiyasini saqlang. Neon bazasini o‘chirmang va `DATABASE_URL` ni almashtirmang.
4. GitHub commit qiling. Railway avtomatik deploy qiladi.
5. Deploy tugagach Telegram botni ochib, jadvalga o‘zingiz belgilagan vaqt qo‘shish, chorva tahrirlash va ombor qoldig‘ini qo‘shish/ayirishni tekshiring.

## Eslatma
- Oziqlantirishdagi `750 gr` qiymati ichki hisobda `0.75 kg` sifatida saqlanadi.
- Chorvani faol ro‘yxatdan o‘chirish tarixiy moliyaviy va oziqlantirish yozuvlarini saqlash uchun arxivlaydi.
- Yem turi sarf tarixiga ega bo‘lsa, tizim tarixni buzmaslik uchun uni o‘chirishga ruxsat bermaydi; nomini tahrirlash mumkin.
