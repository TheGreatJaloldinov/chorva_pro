# CHORVA PRO v2.4 update

This update adds the professional single-farm user profile.

## Deploy
1. Back up the current Neon database before deployment.
2. Replace/add repository files from this project, keeping Railway environment variables unchanged.
3. Railway will restart the service. On startup, the app adds the new profile columns to the existing PostgreSQL `users` table using non-destructive `ADD COLUMN IF NOT EXISTS` statements.
4. Open the Telegram Web App and tap the round avatar on the home screen.
5. Edit profile and farm information, save, then reopen the profile to confirm values persist.

## Profile fields
- Name, phone
- Farm name, address, activity type (single farm per user)
- Language, Asia/Tashkent timezone
- Feeding reminder lead time, daily report preference, default low-stock threshold
- Telegram avatar, username and ID (read from Telegram Web App session)

No database reset is required. Do not delete the Neon project or change `DATABASE_URL` / `BOT_TOKEN`.
