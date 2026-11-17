import asyncio, logging, json
from datetime import datetime
from zoneinfo import ZoneInfo
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy import select
from aiogram.types import FSInputFile
from app.config import BOT_TOKEN, TIMEZONE
from app.db import init_db, Session, User, Animal, FeedingSchedule, FeedingReminder, BackupLog
from app.handlers import router
from app.keyboards import reminder_kb

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
log=logging.getLogger("chorva_pro")

async def reminder_worker(bot: Bot):
    tz=ZoneInfo(TIMEZONE)
    while True:
        try:
            now=datetime.now(tz)
            clock=now.strftime("%H:%M")
            day=now.strftime("%Y-%m-%d")
            async with Session() as s:
                schedules=(await s.execute(select(FeedingSchedule).where(FeedingSchedule.active==True))).scalars().all()
                for sch in schedules:
                    try: times=json.loads(sch.times_json)
                    except Exception: continue
                    if clock not in times: continue
                    stamp=f"{day} {clock} schedule:{sch.id}"
                    existing=(await s.execute(select(FeedingReminder).where(FeedingReminder.scheduled_for==stamp))).scalar_one_or_none()
                    if existing: continue
                    animal=(await s.execute(select(Animal).where(Animal.id==sch.animal_id,Animal.user_id==sch.user_id,Animal.status=="active"))).scalar_one_or_none()
                    user=await s.get(User,sch.user_id)
                    if not animal or not user: continue
                    reminder=FeedingReminder(user_id=sch.user_id,schedule_id=sch.id,animal_id=animal.id,scheduled_for=stamp,items_json=sch.items_json,status="pending")
                    s.add(reminder)
                    try:
                        await s.commit(); await s.refresh(reminder)
                    except Exception:
                        await s.rollback(); continue
                    items=json.loads(sch.items_json)
                    lines=[]
                    for item in items:
                        if item.get("water") or item["name"].lower()=="suv": lines.append("💧 Suv")
                        else: lines.append(f"• {item['qty']:g} kg {item['name']}")
                    text=(f"⏰ <b>Ozuqa berish vaqti!</b>\n\n🐂 ID: <b>{animal.code}</b> · {animal.kind}\n\n"+"\n".join(lines)+"\n\nBerilgan miqdorni tasdiqlang:")
                    try: await bot.send_message(user.telegram_id,text,reply_markup=reminder_kb(reminder.id),parse_mode="HTML")
                    except Exception as e: log.warning("Reminder send failed for user %s: %s",user.telegram_id,e)
        except Exception:
            log.exception("Reminder worker error")
        await asyncio.sleep(20)


async def automatic_backup_worker(bot: Bot):
    """Sends one JSON backup per user each day at 02:00 Asia/Tashkent."""
    from app.backup import make_user_backup
    tz=ZoneInfo(TIMEZONE)
    while True:
        try:
            now=datetime.now(tz)
            if now.strftime("%H:%M")=="02:00":
                day=now.strftime("%Y-%m-%d")
                async with Session() as s:
                    users=(await s.execute(select(User))).scalars().all()
                    user_ids=[u.telegram_id for u in users]
                    internal={u.telegram_id:u.id for u in users}
                for tg_id in user_ids:
                    async with Session() as s:
                        exists=(await s.execute(select(BackupLog).where(BackupLog.user_id==internal[tg_id],BackupLog.backup_date==day))).scalar_one_or_none()
                        if exists: continue
                    path=await make_user_backup(tg_id)
                    if not path: continue
                    try:
                        await bot.send_document(tg_id,FSInputFile(path),caption="🌙 CHORVA PRO avtomatik kunlik backup. Faylni xavfsiz joyda saqlang.")
                        async with Session() as s:
                            s.add(BackupLog(user_id=internal[tg_id],backup_date=day)); await s.commit()
                    except Exception:
                        log.exception("Automatic backup failed for %s",tg_id)
            await asyncio.sleep(30)
        except Exception:
            log.exception("Automatic backup worker error")
            await asyncio.sleep(30)

async def run_bot(initialize=True):
    if not BOT_TOKEN or BOT_TOKEN=="PASTE_YOUR_BOT_TOKEN_HERE":
        raise RuntimeError("BOT_TOKEN topilmadi. JustRunMyApp Environment Variables bo‘limida BOT_TOKEN kiriting.")
    if initialize:
        await init_db()
    bot=Bot(token=BOT_TOKEN)
    dp=Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    task=asyncio.create_task(reminder_worker(bot))
    backup_task=asyncio.create_task(automatic_backup_worker(bot))
    log.info("CHORVA PRO ishga tushdi. Timezone=%s",TIMEZONE)
    try:
        await dp.start_polling(bot,allowed_updates=dp.resolve_used_update_types())
    finally:
        task.cancel(); backup_task.cancel()
        await bot.session.close()

async def main():
    await run_bot()

if __name__=="__main__":
    asyncio.run(main())
