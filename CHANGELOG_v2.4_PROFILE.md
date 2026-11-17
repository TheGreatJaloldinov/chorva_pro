# CHORVA PRO v2.4 - Professional profile

## Added
- Telegram-linked profile header with Telegram avatar, username and Telegram ID.
- Editable user name and phone number.
- Single-farm profile: farm name, address and activity type.
- Saved preferences: language, Asia/Tashkent timezone, feeding reminder lead time, daily report preference and default low-stock threshold.
- Profile summary with active animal count and feed type count.
- Authenticated `/api/profile` GET/PATCH endpoints, scoped to the currently authenticated user.

## Database safety
- Adds new `users` columns using PostgreSQL `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`.
- Existing users, animals, feed, schedules and financial records are not dropped or recreated.
- New fields have safe defaults for existing users.

## Notes
- Telegram photo is displayed from Telegram Web App user data; it is not copied to the database.
- Profile notification preferences are persisted. Wiring every preference into the notification worker is a separate follow-up integration and should be tested on Railway before being described as live.
