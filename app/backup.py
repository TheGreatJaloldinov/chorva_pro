import json, os
from datetime import datetime
from sqlalchemy import select, delete
from sqlalchemy.types import DateTime as DateTimeType
from app.db import Session, User, Animal, WeightRecord, FeedType, FeedLot, FeedingSchedule, FeedingReminder, Expense, Income, Note, BackupLog
from app.config import DATA_DIR

MODELS=[Animal,WeightRecord,FeedType,FeedLot,FeedingSchedule,FeedingReminder,Expense,Income,Note]

async def make_user_backup(telegram_id:int):
    os.makedirs(DATA_DIR,exist_ok=True)
    async with Session() as s:
        user=(await s.execute(select(User).where(User.telegram_id==telegram_id))).scalar_one_or_none()
        if not user: return None
        payload={"format":"chorva-pro-backup-v1","created_at":datetime.utcnow().isoformat(),"telegram_id":telegram_id,"tables":{}}
        for model in MODELS:
            rows=(await s.execute(select(model).where(model.user_id==user.id))).scalars().all()
            records=[]
            for row in rows:
                rec={}
                for col in model.__table__.columns:
                    value=getattr(row,col.name)
                    rec[col.name]=value.isoformat() if isinstance(value,datetime) else value
                records.append(rec)
            payload[model.__tablename__]=records
        path=os.path.join(DATA_DIR,f"chorva_backup_{telegram_id}_{datetime.now():%Y%m%d_%H%M%S}.json")
        with open(path,"w",encoding="utf-8") as f: json.dump(payload,f,ensure_ascii=False,indent=2)
        return path

async def restore_user_backup(telegram_id:int,payload:dict):
    if payload.get("format")!="chorva-pro-backup-v1" or int(payload.get("telegram_id",-1))!=telegram_id:
        raise ValueError("Backup formati yoki Telegram foydalanuvchi ID mos kelmadi.")
    async with Session() as s:
        user=(await s.execute(select(User).where(User.telegram_id==telegram_id))).scalar_one_or_none()
        if not user: raise ValueError("Foydalanuvchi profili topilmadi. Avval botni /start orqali oching.")
        # Delete in reverse foreign-key order.
        for model in reversed(MODELS):
            await s.execute(delete(model).where(model.user_id==user.id))
        await s.flush()
        for model in MODELS:
            records=payload.get(model.__tablename__,[])
            for rec in records:
                values=dict(rec)
                values["user_id"]=user.id
                for col in model.__table__.columns:
                    if isinstance(col.type,DateTimeType) and isinstance(values.get(col.name),str):
                        values[col.name]=datetime.fromisoformat(values[col.name])
                s.add(model(**values))
        await s.commit()
