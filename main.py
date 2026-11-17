import asyncio
import html
import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import FSInputFile
from sqlalchemy import select

from app.config import BOT_TOKEN, TIMEZONE
from app.db import (
    init_db, Session, User, Animal, FeedingSchedule, FeedingReminder, BackupLog,
    FeedType, FeedLot, FeedUsage, Expense, Income,
    NotificationLog, StockAlertState, DailyReportLog,
)
from app.handlers import router
from app.keyboards import reminder_kb

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
log = logging.getLogger("chorva_pro")


def format_feed_quantity(quantity_kg: float) -> str:
    """Render kg values in a human-friendly kg/gram format."""
    grams = max(0, int(round(float(quantity_kg or 0) * 1000)))
    kg, remainder = divmod(grams, 1000)
    if kg and remainder:
        return f"{kg} kg {remainder} gr"
    if kg:
        return f"{kg} kg"
    return f"{remainder} gr"


async def reminder_worker(bot: Bot):
    """Per-user feeding reminders, low-stock alerts and optional daily summaries."""
    while True:
        try:
            async with Session() as s:
                schedules = (await s.execute(
                    select(FeedingSchedule).where(FeedingSchedule.active.is_(True))
                )).scalars().all()

                for sch in schedules:
                    try:
                        times = json.loads(sch.times_json)
                        items = json.loads(sch.items_json)
                    except (TypeError, ValueError, json.JSONDecodeError):
                        log.warning("Invalid feeding schedule JSON: %s", sch.id)
                        continue

                    user = await s.get(User, sch.user_id)
                    animal = await s.get(Animal, sch.animal_id)
                    if not user or not animal or animal.status != "active":
                        continue

                    try:
                        user_tz = ZoneInfo(user.timezone or TIMEZONE)
                    except Exception:
                        user_tz = ZoneInfo(TIMEZONE)
                    now = datetime.now(user_tz).replace(second=0, microsecond=0)
                    day = now.strftime("%Y-%m-%d")
                    lead_minutes = max(0, int(user.reminder_minutes or 0))

                    for clock in times:
                        try:
                            hour, minute = map(int, str(clock).split(":"))
                            target = now.replace(hour=hour, minute=minute)
                        except (TypeError, ValueError):
                            continue

                        delta = int((target - now).total_seconds() // 60)
                        if delta != 0 and (lead_minutes == 0 or delta != lead_minutes):
                            continue

                        kind = "due" if delta == 0 else f"pre{lead_minutes}"
                        lines = []
                        for item in items:
                            item_name = str(item.get("name", "Yem"))
                            if item.get("water") or item_name.strip().lower() == "suv":
                                lines.append("💧 Suv")
                            else:
                                qty = item.get("qty", item.get("quantity", 0))
                                lines.append(f"• {format_feed_quantity(float(qty or 0))} {html.escape(item_name)}")

                        if kind == "due":
                            stamp = f"{day} {clock} schedule:{sch.id}"
                            reminder = (await s.execute(
                                select(FeedingReminder).where(FeedingReminder.scheduled_for == stamp)
                            )).scalar_one_or_none()
                            if reminder:
                                continue
                            reminder = FeedingReminder(
                                user_id=sch.user_id,
                                schedule_id=sch.id,
                                animal_id=animal.id,
                                scheduled_for=stamp,
                                items_json=sch.items_json,
                                status="pending",
                            )
                            s.add(reminder)
                            try:
                                await s.commit()
                                await s.refresh(reminder)
                            except Exception:
                                await s.rollback()
                                continue
                            msg = (
                                f"⏰ <b>Ozuqa berish vaqti keldi!</b>\n\n"
                                f"🐂 ID: <b>{html.escape(animal.code)}</b> · {html.escape(animal.kind)}\n"
                                f"⏰ Vaqt: <b>{html.escape(str(clock))}</b>\n\n"
                                + "\n".join(lines)
                                + "\n\nBerilganini CHORVA PRO’da tasdiqlang."
                            )
                            try:
                                await bot.send_message(
                                    user.telegram_id, msg, parse_mode="HTML",
                                    reply_markup=reminder_kb(reminder.id),
                                )
                            except Exception as exc:
                                log.warning("Due reminder send failed for %s: %s", user.telegram_id, exc)
                                # Remove the unsent pending reminder so the worker can retry.
                                try:
                                    await s.delete(reminder)
                                    await s.commit()
                                except Exception:
                                    await s.rollback()
                        else:
                            event_key = f"feeding:{user.id}:{sch.id}:{day}:{clock}:{kind}"
                            exists = (await s.execute(
                                select(NotificationLog.id).where(NotificationLog.event_key == event_key)
                            )).scalar_one_or_none()
                            if exists:
                                continue
                            msg = (
                                f"🔔 <b>Ozuqa vaqti yaqin!</b>\n\n"
                                f"🐂 ID: <b>{html.escape(animal.code)}</b> · {html.escape(animal.kind)}\n"
                                f"⏰ Belgilangan vaqt: <b>{html.escape(str(clock))}</b> ({lead_minutes} daqiqadan keyin)\n\n"
                                + "\n".join(lines)
                            )
                            try:
                                await bot.send_message(user.telegram_id, msg, parse_mode="HTML")
                                s.add(NotificationLog(user_id=user.id, event_key=event_key))
                                await s.commit()
                            except Exception as exc:
                                await s.rollback()
                                log.warning("Pre-feeding alert failed for %s: %s", user.telegram_id, exc)

                # Low-stock alerts: one message per low-stock episode. A new alert is
                # enabled only after stock rises above the threshold and falls again.
                feeds = (await s.execute(select(FeedType))).scalars().all()
                for feed in feeds:
                    lots = (await s.execute(
                        select(FeedLot).where(
                            FeedLot.user_id == feed.user_id,
                            FeedLot.feed_type_id == feed.id,
                        )
                    )).scalars().all()
                    remaining = sum(float(lot.quantity_remaining or 0) for lot in lots)
                    threshold = float(feed.low_stock_alert if feed.low_stock_alert is not None else 5)
                    state = (await s.execute(
                        select(StockAlertState).where(
                            StockAlertState.user_id == feed.user_id,
                            StockAlertState.feed_type_id == feed.id,
                        )
                    )).scalar_one_or_none()

                    if remaining > threshold:
                        if state and state.is_low:
                            state.is_low = False
                            await s.commit()
                        continue
                    if state and state.is_low:
                        continue

                    user = await s.get(User, feed.user_id)
                    if not user:
                        continue
                    msg = (
                        "⚠️ <b>OMBOR OGOHLANTIRISHI</b>\n\n"
                        f"🌾 {html.escape(feed.name)}: <b>{format_feed_quantity(remaining)}</b> qoldi.\n"
                        f"📉 Ogohlantirish chegarasi: {format_feed_quantity(threshold)}.\n\n"
                        "Ozuqa zaxirasini to‘ldirish tavsiya etiladi."
                    )
                    try:
                        await bot.send_message(user.telegram_id, msg, parse_mode="HTML")
                        if state is None:
                            s.add(StockAlertState(user_id=feed.user_id, feed_type_id=feed.id, is_low=True))
                        else:
                            state.is_low = True
                        await s.commit()
                    except Exception as exc:
                        await s.rollback()
                        log.warning("Low-stock alert failed for %s: %s", user.telegram_id, exc)

                # Optional daily report at 20:00 in each user's configured timezone.
                users = (await s.execute(select(User).where(User.daily_report_enabled.is_(True)))).scalars().all()
                for user in users:
                    try:
                        user_tz = ZoneInfo(user.timezone or TIMEZONE)
                    except Exception:
                        user_tz = ZoneInfo(TIMEZONE)
                    now = datetime.now(user_tz)
                    if now.strftime("%H:%M") != "20:00":
                        continue
                    day = now.strftime("%Y-%m-%d")
                    already_sent = (await s.execute(
                        select(DailyReportLog.id).where(
                            DailyReportLog.user_id == user.id,
                            DailyReportLog.report_date == day,
                        )
                    )).scalar_one_or_none()
                    if already_sent:
                        continue

                    feed_usage = (await s.execute(select(FeedUsage).where(
                        FeedUsage.user_id == user.id, FeedUsage.used_at == day
                    ))).scalars().all()
                    expenses = (await s.execute(select(Expense).where(
                        Expense.user_id == user.id, Expense.expense_date == day
                    ))).scalars().all()
                    incomes = (await s.execute(select(Income).where(
                        Income.user_id == user.id, Income.income_date == day
                    ))).scalars().all()
                    animal_count = (await s.execute(select(Animal).where(
                        Animal.user_id == user.id, Animal.status == "active"
                    ))).scalars().all()
                    feed_names = {}
                    for usage in feed_usage:
                        feed = await s.get(FeedType, usage.feed_type_id)
                        feed_name = feed.name if feed else "Yem"
                        feed_names[feed_name] = feed_names.get(feed_name, 0.0) + float(usage.quantity or 0)
                    feed_lines = [f"• {html.escape(name)}: {format_feed_quantity(qty)}" for name, qty in sorted(feed_names.items())]
                    income_total = sum(float(x.amount or 0) for x in incomes)
                    expense_total = sum(float(x.amount or 0) for x in expenses)
                    report = (
                        f"📊 <b>CHORVA PRO · Kunlik hisobot</b>\n\n"
                        f"📅 Sana: <b>{day}</b>\n"
                        f"🐄 Faol chorva: <b>{len(animal_count)} bosh</b>\n"
                        f"🌾 Yem sarfi: <b>{format_feed_quantity(sum(feed_names.values()))}</b>\n"
                        f"📈 Daromad: <b>{income_total:,.0f} so‘m</b>\n"
                        f"📉 Xarajat: <b>{expense_total:,.0f} so‘m</b>\n"
                        f"💰 Sof natija: <b>{income_total-expense_total:,.0f} so‘m</b>"
                    )
                    if feed_lines:
                        report += "\n\n<b>Yemlar bo‘yicha:</b>\n" + "\n".join(feed_lines)
                    try:
                        await bot.send_message(user.telegram_id, report, parse_mode="HTML")
                        s.add(DailyReportLog(user_id=user.id, report_date=day))
                        await s.commit()
                    except Exception as exc:
                        await s.rollback()
                        log.warning("Daily report send failed for %s: %s", user.telegram_id, exc)
        except Exception:
            log.exception("Reminder/stock notification worker error")
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
