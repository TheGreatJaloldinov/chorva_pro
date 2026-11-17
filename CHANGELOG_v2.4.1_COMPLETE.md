# CHORVA PRO v2.4.1 COMPLETE

## Birlashma
- v2.2 oziqlantirish, chorva va ombor UI/API yaxshilanishlari saqlandi.
- v2.3 Telegram reminder va low-stock worker'i v2.4 profil DB modeli bilan birlashtirildi.
- v2.4 professional profil va single-farm profil endpointlari saqlandi.

## Ogohlantirish worker yaxshilanishi
- Oldindan eslatma foydalanuvchi profilidagi `reminder_minutes` qiymatiga amal qiladi.
- 0 daqiqa oldindan eslatmani o'chiradi; due-time xabarini o'chirmaydi.
- Low-stock xabari faqat bitta low-stock davrida bir marta yuboriladi; qoldiq chegaradan oshgach qayta faollashadi.
- Kunlik hisobot sukut bo'yicha o'chirilgan; yoqilganda 20:00 da yuboriladi.
- Miqdorlar Telegram xabarlarida kg/gr ko'rinishida ifodalanadi.

## Profil va ombor
- Profil chegarasi mavjud yem turlariga qo'llanadi.
- Yangi yem profilning joriy past-qoldiq chegarasi bilan yaratiladi.
- Profil ismi Telegram ismidan ustun ko'rsatiladi.
- API CORS konfiguratsiyasiga DELETE qo'shildi.

## Ma'lumotlar bazasi
- `telegram_id` BIGINT.
- Mavjud profil ustunlari saqlanadi.
- `notification_logs`, `stock_alert_states`, `daily_report_logs` jadvallari qo'shiladi.
- Eski 10 kg standart ombor chegarasi 5 kg ga yangilanadi; boshqa limitlar o'zgarmaydi.
- Hech qanday mavjud biznes jadvali o'chirilmaydi.
