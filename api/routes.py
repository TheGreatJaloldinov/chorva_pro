from __future__ import annotations
import json
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import Session, get_user, User, Animal, WeightRecord, FeedType, FeedLot, FeedUsage, Expense, Income, FeedingSchedule, Note
from api.auth import telegram_identity
from api.schemas import AnimalCreate, AnimalUpdate, WeightCreate, FeedPurchaseCreate, MoneyCreate

router = APIRouter(prefix="/api")
async def db_session():
    async with Session() as session: yield session
async def current_user(identity: dict = Depends(telegram_identity), session: AsyncSession = Depends(db_session)) -> User:
    return await get_user(session, identity["telegram_id"], identity.get("full_name", ""))
def animal_dict(a):
    return {"id":a.id,"code":a.code,"kind":a.kind,"breed":a.breed,"sex":a.sex,"age_months":a.age_months,"current_weight":a.current_weight,"purchase_date":a.purchase_date,"purchase_price":a.purchase_price,"note":a.note,"status":a.status,"photo_file_id":a.photo_file_id}

@router.get('/health')
async def health(): return {"ok":True,"app":"CHORVA PRO","version":"2.4.1"}
@router.get('/me')
async def me(user:User=Depends(current_user)):
    return {"telegram_id":user.telegram_id,"full_name":user.full_name}

@router.get('/profile')
async def get_profile(user:User=Depends(current_user),session:AsyncSession=Depends(db_session)):
    animal_count=(await session.execute(select(func.count(Animal.id)).where(Animal.user_id==user.id,Animal.status=='active'))).scalar_one()
    feed_count=(await session.execute(select(func.count(FeedType.id)).where(FeedType.user_id==user.id))).scalar_one()
    return {"full_name":user.full_name,"phone":user.phone,"farm_name":user.farm_name,"farm_address":user.farm_address,"farm_type":user.farm_type,"language":user.language,"timezone":user.timezone,"reminder_minutes":user.reminder_minutes,"daily_report_enabled":user.daily_report_enabled,"low_stock_default":user.low_stock_default,"telegram_id":user.telegram_id,"created_at":user.created_at.isoformat() if user.created_at else None,"animal_count":animal_count,"feed_count":feed_count}

@router.patch('/profile')
async def update_profile(payload:dict,user:User=Depends(current_user),session:AsyncSession=Depends(db_session)):
    allowed={'full_name':200,'phone':40,'farm_name':200,'farm_address':300,'farm_type':80,'language':10,'timezone':50}
    for key,max_len in allowed.items():
        if key in payload:
            value=str(payload[key] or '').strip()
            if len(value)>max_len: raise HTTPException(422,f'{key} juda uzun')
            setattr(user,key,value)
    if 'reminder_minutes' in payload:
        value=int(payload['reminder_minutes'])
        if value not in (0,5,10,15,30,60): raise HTTPException(422,'Eslatma vaqti noto‘g‘ri')
        user.reminder_minutes=value
    if 'daily_report_enabled' in payload: user.daily_report_enabled=bool(payload['daily_report_enabled'])
    if 'low_stock_default' in payload:
        value=float(payload['low_stock_default'])
        if value<0 or value>1000000: raise HTTPException(422,'Ombor chegarasi noto‘g‘ri')
        user.low_stock_default=value
        # The profile setting is the farm-wide default: apply it to existing feed types too.
        feed_types=(await session.execute(select(FeedType).where(FeedType.user_id==user.id))).scalars().all()
        for feed in feed_types:
            feed.low_stock_alert=value
    await session.commit()
    return {'ok':True}

@router.get('/dashboard')
async def dashboard(user:User=Depends(current_user),session:AsyncSession=Depends(db_session)):
    animals=(await session.execute(select(Animal).where(Animal.user_id==user.id,Animal.status=='active'))).scalars().all()
    income=(await session.execute(select(func.coalesce(func.sum(Income.amount),0)).where(Income.user_id==user.id))).scalar_one()
    expenses=(await session.execute(select(func.coalesce(func.sum(Expense.amount),0)).where(Expense.user_id==user.id))).scalar_one()
    feeds=(await session.execute(select(FeedType).where(FeedType.user_id==user.id))).scalars().all(); stock=[]
    for f in feeds:
        lots=(await session.execute(select(FeedLot).where(FeedLot.user_id==user.id,FeedLot.feed_type_id==f.id))).scalars().all()
        remaining=sum(x.quantity_remaining for x in lots); stock.append({"id":f.id,"name":f.name,"remaining":round(remaining,2),"alert":f.low_stock_alert,"low":remaining<=f.low_stock_alert})
    return {"animal_count":len(animals),"total_weight":round(sum(a.current_weight for a in animals),2),"income":float(income),"expenses":float(expenses),"net":float(income)-float(expenses),"feed_stock":stock,"animal_types":{k:sum(a.kind==k for a in animals) for k in ['Sigir','Buqa','Qo‘chqor','Sovliq']}}

@router.get('/animals')
async def list_animals(status:str=Query('active',pattern='^(active|archived|all)$'),q:str='',kind:str='',user:User=Depends(current_user),session:AsyncSession=Depends(db_session)):
    stmt=select(Animal).where(Animal.user_id==user.id)
    if status!='all': stmt=stmt.where(Animal.status==status)
    if q.strip(): stmt=stmt.where(Animal.code.ilike(f'%{q.strip()}%')|Animal.kind.ilike(f'%{q.strip()}%')|Animal.breed.ilike(f'%{q.strip()}%'))
    if kind: stmt=stmt.where(Animal.kind==kind)
    rows=(await session.execute(stmt.order_by(Animal.code))).scalars().all(); return [animal_dict(a) for a in rows]

@router.post('/animals')
async def create_animal(payload:AnimalCreate,user:User=Depends(current_user),session:AsyncSession=Depends(db_session)):
    sexmap={'Sigir':'Urg‘ochi','Buqa':'Erkak','Qo‘chqor':'Erkak','Sovliq':'Urg‘ochi'}
    if payload.kind not in sexmap: raise HTTPException(422,'Chorva turini tanlang')
    existing=(await session.execute(select(Animal.code).where(Animal.user_id==user.id))).scalars().all(); code=(payload.code or '').strip()
    if not code: code=f"{max([int(x) for x in existing if x.isdigit()] or [0])+1:03d}"
    if code in existing: raise HTTPException(409,'Bu ID raqami band')
    a=Animal(user_id=user.id,code=code,kind=payload.kind,sex=sexmap[payload.kind],breed=payload.breed,age_months=payload.age_months,current_weight=payload.current_weight,purchase_date=payload.purchase_date or date.today().isoformat(),purchase_price=payload.purchase_price,note=payload.note)
    session.add(a); await session.flush()
    if a.current_weight>0: session.add(WeightRecord(user_id=user.id,animal_id=a.id,weight=a.current_weight,recorded_at=datetime.utcnow()))
    if a.purchase_price>0: session.add(Expense(user_id=user.id,animal_id=a.id,category='Chorva xaridi',amount=a.purchase_price,expense_date=a.purchase_date,description=f'Chorva #{code} xaridi'))
    await session.commit(); return {"ok":True,"animal":animal_dict(a)}

@router.get('/animals/{aid}')
async def animal_detail(aid:int,user:User=Depends(current_user),session:AsyncSession=Depends(db_session)):
    a=(await session.execute(select(Animal).where(Animal.id==aid,Animal.user_id==user.id))).scalar_one_or_none()
    if not a: raise HTTPException(404,'Chorva topilmadi')
    weights=(await session.execute(select(WeightRecord).where(WeightRecord.user_id==user.id,WeightRecord.animal_id==aid).order_by(WeightRecord.recorded_at.desc()))).scalars().all()
    notes=(await session.execute(select(Note).where(Note.user_id==user.id,Note.animal_id==aid).order_by(Note.created_at.desc()))).scalars().all()
    schedules=(await session.execute(select(FeedingSchedule).where(FeedingSchedule.user_id==user.id,FeedingSchedule.animal_id==aid))).scalars().all()
    return {**animal_dict(a),'weights':[{'weight':w.weight,'recorded_at':w.recorded_at.isoformat(),'note':w.note} for w in weights],'notes':[{'id':n.id,'body':n.body,'created_at':n.created_at.isoformat()} for n in notes],'feeding_schedules':[{'id':x.id,'times':json.loads(x.times_json),'items':json.loads(x.items_json),'active':x.active} for x in schedules]}

@router.patch('/animals/{aid}')
async def update_animal(aid:int,payload:AnimalUpdate,user:User=Depends(current_user),session:AsyncSession=Depends(db_session)):
    a=(await session.execute(select(Animal).where(Animal.id==aid,Animal.user_id==user.id))).scalar_one_or_none()
    if not a: raise HTTPException(404,'Chorva topilmadi')
    updates=payload.model_dump(exclude_unset=True)
    if 'status' in updates and updates['status'] not in ['active','archived']: raise HTTPException(422,'Holat noto‘g‘ri')
    if 'kind' in updates and updates['kind'] not in ['Sigir','Buqa','Qo‘chqor','Sovliq']: raise HTTPException(422,'Chorva turi noto‘g‘ri')
    if 'code' in updates and updates['code']:
        duplicate=(await session.execute(select(Animal.id).where(Animal.user_id==user.id,Animal.code==updates['code'],Animal.id!=aid))).scalar_one_or_none()
        if duplicate: raise HTTPException(409,'Bu ID raqami band')
    sexmap={'Sigir':'Urg‘ochi','Buqa':'Erkak','Qo‘chqor':'Erkak','Sovliq':'Urg‘ochi'}
    for k,v in updates.items(): setattr(a,k,v)
    if 'kind' in updates: a.sex=sexmap[updates['kind']]
    await session.commit(); return {'ok':True}

@router.delete('/animals/{aid}')
async def delete_animal(aid:int,user:User=Depends(current_user),session:AsyncSession=Depends(db_session)):
    a=(await session.execute(select(Animal).where(Animal.id==aid,Animal.user_id==user.id))).scalar_one_or_none()
    if not a: raise HTTPException(404,'Chorva topilmadi')
    # Preserve financial and operational history by archiving instead of hard deletion.
    a.status='archived'
    await session.commit()
    return {'ok':True,'archived':True}

@router.post('/animals/{aid}/weights')
async def add_weight(aid:int,payload:WeightCreate,user:User=Depends(current_user),session:AsyncSession=Depends(db_session)):
    a=(await session.execute(select(Animal).where(Animal.id==aid,Animal.user_id==user.id,Animal.status=='active'))).scalar_one_or_none()
    if not a: raise HTTPException(404,'Faol chorva topilmadi')
    try: dt=datetime.fromisoformat(payload.recorded_date) if payload.recorded_date else datetime.utcnow()
    except ValueError: raise HTTPException(422,'Sana noto‘g‘ri')
    a.current_weight=payload.weight; session.add(WeightRecord(user_id=user.id,animal_id=aid,weight=payload.weight,recorded_at=dt,note=payload.note)); await session.commit(); return {'ok':True,'current_weight':a.current_weight}

@router.post('/animals/{aid}/notes')
async def add_note(aid:int,payload:dict,user:User=Depends(current_user),session:AsyncSession=Depends(db_session)):
    a=(await session.execute(select(Animal).where(Animal.id==aid,Animal.user_id==user.id))).scalar_one_or_none()
    if not a: raise HTTPException(404,'Chorva topilmadi')
    body=str(payload.get('body','')).strip()
    if not body: raise HTTPException(422,'Qayd matnini kiriting')
    session.add(Note(user_id=user.id,animal_id=aid,body=body)); await session.commit(); return {'ok':True}

@router.get('/feeds')
async def list_feeds(user:User=Depends(current_user),session:AsyncSession=Depends(db_session)):
    fs=(await session.execute(select(FeedType).where(FeedType.user_id==user.id).order_by(FeedType.name))).scalars().all(); out=[]
    for f in fs:
        lots=(await session.execute(select(FeedLot).where(FeedLot.user_id==user.id,FeedLot.feed_type_id==f.id).order_by(FeedLot.purchased_at))).scalars().all()
        qty=sum(x.quantity_remaining for x in lots); out.append({'id':f.id,'name':f.name,'remaining':round(qty,2),'alert':f.low_stock_alert,'lots':len(lots),'low':qty<=f.low_stock_alert,'lots_detail':[{'date':x.purchased_at,'initial':x.quantity_initial,'remaining':x.quantity_remaining,'unit_price':x.unit_price} for x in lots]})
    return out

@router.post('/feeds/purchases')
async def add_feed_purchase(payload:FeedPurchaseCreate,user:User=Depends(current_user),session:AsyncSession=Depends(db_session)):
    f=(await session.execute(select(FeedType).where(FeedType.user_id==user.id,func.lower(FeedType.name)==payload.name.strip().lower()))).scalar_one_or_none()
    if not f: f=FeedType(user_id=user.id,name=payload.name.strip(),low_stock_alert=float(user.low_stock_default or 5)); session.add(f); await session.flush()
    session.add(FeedLot(user_id=user.id,feed_type_id=f.id,purchased_at=payload.purchased_at,quantity_initial=payload.quantity,quantity_remaining=payload.quantity,unit_price=payload.unit_price,supplier=payload.supplier))
    session.add(Expense(user_id=user.id,category='Yem-xashak xaridi',amount=payload.quantity*payload.unit_price,expense_date=payload.purchased_at,description=f'{f.name} {payload.quantity:g} kg xarid'))
    await session.commit(); return {'ok':True,'feed':f.name}

@router.post('/feeds/usage')
async def use_feed(payload:dict,user:User=Depends(current_user),session:AsyncSession=Depends(db_session)):
    fid=int(payload.get('feed_id',0)); qty=float(payload.get('quantity',0)); aid=payload.get('animal_id'); used=str(payload.get('used_at') or date.today().isoformat())
    if qty<=0: raise HTTPException(422,'Miqdor musbat bo‘lishi kerak')
    f=(await session.execute(select(FeedType).where(FeedType.id==fid,FeedType.user_id==user.id))).scalar_one_or_none()
    if not f: raise HTTPException(404,'Yem turi topilmadi')
    lots=(await session.execute(select(FeedLot).where(FeedLot.user_id==user.id,FeedLot.feed_type_id==fid,FeedLot.quantity_remaining>0).order_by(FeedLot.purchased_at,FeedLot.id))).scalars().all()
    available=sum(x.quantity_remaining for x in lots)
    if available+1e-8<qty: raise HTTPException(409,f'Omborda {available:g} kg bor, yetarli emas')
    left=qty
    for lot in lots:
        take=min(left,lot.quantity_remaining); lot.quantity_remaining-=take; left-=take
        if left<=1e-8: break
    session.add(FeedUsage(user_id=user.id,animal_id=aid,feed_type_id=fid,quantity=qty,used_at=used,note=str(payload.get('note',''))))
    await session.commit(); return {'ok':True,'remaining':round(available-qty,2),'low':available-qty<=f.low_stock_alert}

@router.get('/feeds/usage')
async def usage_history(user:User=Depends(current_user),session:AsyncSession=Depends(db_session)):
    rows=(await session.execute(select(FeedUsage).where(FeedUsage.user_id==user.id).order_by(FeedUsage.used_at.desc()).limit(100))).scalars().all()
    return [{'id':x.id,'feed_id':x.feed_type_id,'animal_id':x.animal_id,'quantity':x.quantity,'date':x.used_at,'note':x.note} for x in rows]

@router.post('/feeds/{fid}/adjust')
async def adjust_feed_stock(fid:int,payload:dict,user:User=Depends(current_user),session:AsyncSession=Depends(db_session)):
    f=(await session.execute(select(FeedType).where(FeedType.id==fid,FeedType.user_id==user.id))).scalar_one_or_none()
    if not f: raise HTTPException(404,'Yem topilmadi')
    qty=float(payload.get('quantity',0)); direction=str(payload.get('direction','add'))
    if qty<=0: raise HTTPException(422,'Miqdor musbat bo‘lishi kerak')
    if direction=='add':
        session.add(FeedLot(user_id=user.id,feed_type_id=f.id,purchased_at=date.today().isoformat(),quantity_initial=qty,quantity_remaining=qty,unit_price=0,supplier='Qo‘lda tuzatish'))
    elif direction=='subtract':
        lots=(await session.execute(select(FeedLot).where(FeedLot.user_id==user.id,FeedLot.feed_type_id==fid,FeedLot.quantity_remaining>0).order_by(FeedLot.purchased_at,FeedLot.id))).scalars().all()
        available=sum(x.quantity_remaining for x in lots)
        if available+1e-8<qty: raise HTTPException(409,f'Omborda faqat {available:g} kg bor')
        left=qty
        for lot in lots:
            take=min(left,lot.quantity_remaining); lot.quantity_remaining-=take; left-=take
            if left<=1e-8: break
        session.add(FeedUsage(user_id=user.id,feed_type_id=f.id,quantity=qty,used_at=date.today().isoformat(),note='Ombor qoldig‘ini qo‘lda kamaytirish'))
    else: raise HTTPException(422,'Amal noto‘g‘ri')
    await session.commit(); return {'ok':True}

@router.patch('/feeds/{fid}')
async def rename_feed(fid:int,payload:dict,user:User=Depends(current_user),session:AsyncSession=Depends(db_session)):
    f=(await session.execute(select(FeedType).where(FeedType.id==fid,FeedType.user_id==user.id))).scalar_one_or_none()
    if not f: raise HTTPException(404,'Yem topilmadi')
    name=str(payload.get('name',f.name)).strip()
    if not name: raise HTTPException(422,'Yem nomini kiriting')
    duplicate=(await session.execute(select(FeedType).where(FeedType.user_id==user.id,func.lower(FeedType.name)==name.lower(),FeedType.id!=fid))).scalar_one_or_none()
    if duplicate: raise HTTPException(409,'Bu nomdagi yem mavjud')
    f.name=name
    await session.commit(); return {'ok':True}

@router.delete('/feeds/{fid}')
async def delete_feed(fid:int,user:User=Depends(current_user),session:AsyncSession=Depends(db_session)):
    f=(await session.execute(select(FeedType).where(FeedType.id==fid,FeedType.user_id==user.id))).scalar_one_or_none()
    if not f: raise HTTPException(404,'Yem topilmadi')
    used=(await session.execute(select(FeedUsage.id).where(FeedUsage.user_id==user.id,FeedUsage.feed_type_id==fid).limit(1))).scalar_one_or_none()
    if used: raise HTTPException(409,'Bu yemda sarf tarixi bor. Tarixni saqlash uchun o‘chirish mumkin emas, nomini tahrirlang.')
    lots=(await session.execute(select(FeedLot).where(FeedLot.user_id==user.id,FeedLot.feed_type_id==fid))).scalars().all()
    for lot in lots: await session.delete(lot)
    await session.delete(f); await session.commit(); return {'ok':True}

@router.post('/feeds/{fid}/alert')
async def set_feed_alert(fid:int,payload:dict,user:User=Depends(current_user),session:AsyncSession=Depends(db_session)):
    f=(await session.execute(select(FeedType).where(FeedType.id==fid,FeedType.user_id==user.id))).scalar_one_or_none()
    if not f: raise HTTPException(404,'Yem topilmadi')
    f.low_stock_alert=max(0,float(payload.get('alert',10))); await session.commit(); return {'ok':True}

@router.get('/finance')
async def finance(user:User=Depends(current_user),session:AsyncSession=Depends(db_session)):
    ex=(await session.execute(select(Expense).where(Expense.user_id==user.id).order_by(Expense.expense_date.desc()))).scalars().all(); inc=(await session.execute(select(Income).where(Income.user_id==user.id).order_by(Income.income_date.desc()))).scalars().all()
    return {'income':sum(x.amount for x in inc),'expenses':sum(x.amount for x in ex),'net':sum(x.amount for x in inc)-sum(x.amount for x in ex),'expenses_list':[{'id':x.id,'date':x.expense_date,'category':x.category,'amount':x.amount,'description':x.description,'animal_id':x.animal_id} for x in ex],'incomes_list':[{'id':x.id,'date':x.income_date,'category':x.category,'amount':x.amount,'description':x.description,'animal_id':x.animal_id} for x in inc]}
@router.post('/finance/expenses')
async def add_expense(payload:MoneyCreate,user:User=Depends(current_user),session:AsyncSession=Depends(db_session)):
    session.add(Expense(user_id=user.id,animal_id=payload.animal_id,category=payload.category,amount=payload.amount,expense_date=payload.date,description=payload.description)); await session.commit(); return {'ok':True}
@router.post('/finance/incomes')
async def add_income(payload:MoneyCreate,user:User=Depends(current_user),session:AsyncSession=Depends(db_session)):
    session.add(Income(user_id=user.id,animal_id=payload.animal_id,category=payload.category,amount=payload.amount,income_date=payload.date,description=payload.description)); await session.commit(); return {'ok':True}

@router.get('/schedules')
async def schedules(user:User=Depends(current_user),session:AsyncSession=Depends(db_session)):
    rows=(await session.execute(select(FeedingSchedule).where(FeedingSchedule.user_id==user.id))).scalars().all()
    return [{'id':x.id,'animal_id':x.animal_id,'times':json.loads(x.times_json),'items':json.loads(x.items_json),'active':x.active} for x in rows]
@router.post('/schedules')
async def create_schedule(payload:dict,user:User=Depends(current_user),session:AsyncSession=Depends(db_session)):
    aid=int(payload.get('animal_id',0)); a=(await session.execute(select(Animal).where(Animal.id==aid,Animal.user_id==user.id,Animal.status=='active'))).scalar_one_or_none()
    if not a: raise HTTPException(404,'Faol chorva topilmadi')
    times=payload.get('times',[]); items=[{**x,'qty':float(x.get('quantity',x.get('qty',0)))} for x in payload.get('items',[])]
    if not times or not items: raise HTTPException(422,'Vaqt va yem tarkibini kiriting')
    row=FeedingSchedule(user_id=user.id,animal_id=aid,times_json=json.dumps(times,ensure_ascii=False),items_json=json.dumps(items,ensure_ascii=False),active=True); session.add(row); await session.commit(); return {'ok':True,'id':row.id}
@router.patch('/schedules/{sid}')
async def update_schedule(sid:int,payload:dict,user:User=Depends(current_user),session:AsyncSession=Depends(db_session)):
    row=(await session.execute(select(FeedingSchedule).where(FeedingSchedule.id==sid,FeedingSchedule.user_id==user.id))).scalar_one_or_none()
    if not row: raise HTTPException(404,'Jadval topilmadi')
    if 'active' in payload: row.active=bool(payload['active'])
    if 'animal_id' in payload:
        animal=(await session.execute(select(Animal).where(Animal.id==int(payload['animal_id']),Animal.user_id==user.id,Animal.status=='active'))).scalar_one_or_none()
        if not animal: raise HTTPException(404,'Faol chorva topilmadi')
        row.animal_id=animal.id
    if 'times' in payload: row.times_json=json.dumps(payload['times'],ensure_ascii=False)
    if 'items' in payload: row.items_json=json.dumps([{**x,'qty':float(x.get('quantity',x.get('qty',0)))} for x in payload['items']],ensure_ascii=False)
    await session.commit(); return {'ok':True}

@router.delete('/schedules/{sid}')
async def delete_schedule(sid:int,user:User=Depends(current_user),session:AsyncSession=Depends(db_session)):
    row=(await session.execute(select(FeedingSchedule).where(FeedingSchedule.id==sid,FeedingSchedule.user_id==user.id))).scalar_one_or_none()
    if not row: raise HTTPException(404,'Jadval topilmadi')
    await session.delete(row); await session.commit(); return {'ok':True}

@router.get('/reports/monthly')
async def monthly_report(month:str=Query(default_factory=lambda:date.today().strftime('%Y-%m')),user:User=Depends(current_user),session:AsyncSession=Depends(db_session)):
    ex=(await session.execute(select(Expense).where(Expense.user_id==user.id,Expense.expense_date.startswith(month)))).scalars().all(); inc=(await session.execute(select(Income).where(Income.user_id==user.id,Income.income_date.startswith(month)))).scalars().all()
    usage=(await session.execute(select(FeedUsage).where(FeedUsage.user_id==user.id,FeedUsage.used_at.startswith(month)))).scalars().all()
    return {'month':month,'income':sum(x.amount for x in inc),'expenses':sum(x.amount for x in ex),'net':sum(x.amount for x in inc)-sum(x.amount for x in ex),'feed_used_kg':sum(x.quantity for x in usage),'expense_categories':{c:sum(x.amount for x in ex if x.category==c) for c in {x.category for x in ex}}}

@router.get('/reports/export')
async def export_report(user:User=Depends(current_user),session:AsyncSession=Depends(db_session)):
    from io import BytesIO
    from openpyxl import Workbook
    from fastapi.responses import StreamingResponse
    wb=Workbook(); ws=wb.active; ws.title='Chorva'
    ws.append(['ID','Turi','Zoti','Jinsi','Yosh (oy)','Vazn (kg)','Holat','Xarid sanasi','Xarid narxi'])
    rows=(await session.execute(select(Animal).where(Animal.user_id==user.id).order_by(Animal.code))).scalars().all()
    for a in rows: ws.append([a.code,a.kind,a.breed,a.sex,a.age_months,a.current_weight,a.status,a.purchase_date,a.purchase_price])
    fs=wb.create_sheet('Yem ombori'); fs.append(['Yem','Sana','Boshlang‘ich kg','Qoldiq kg','1 kg narxi'])
    lots=(await session.execute(select(FeedLot).where(FeedLot.user_id==user.id))).scalars().all()
    for lot in lots:
        f=(await session.execute(select(FeedType).where(FeedType.id==lot.feed_type_id))).scalar_one(); fs.append([f.name,lot.purchased_at,lot.quantity_initial,lot.quantity_remaining,lot.unit_price])
    bio=BytesIO(); wb.save(bio); bio.seek(0)
    return StreamingResponse(bio,media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',headers={'Content-Disposition':'attachment; filename=chorva-pro-hisobot.xlsx'})

@router.post('/animals/{aid}/sell')
async def sell_animal(aid:int,payload:dict,user:User=Depends(current_user),session:AsyncSession=Depends(db_session)):
    a=(await session.execute(select(Animal).where(Animal.id==aid,Animal.user_id==user.id,Animal.status=='active'))).scalar_one_or_none()
    if not a: raise HTTPException(404,'Faol chorva topilmadi')
    amount=float(payload.get('amount',0)); sold_date=str(payload.get('date') or date.today().isoformat())
    if amount<=0: raise HTTPException(422,'Sotish narxini kiriting')
    session.add(Income(user_id=user.id,animal_id=aid,category='Chorva sotish',amount=amount,income_date=sold_date,description=f'#{a.code} {a.kind} sotildi'))
    a.status='archived'; await session.commit(); return {'ok':True,'profit_estimate':amount-a.purchase_price}

@router.get('/backup')
async def backup_json(user:User=Depends(current_user),session:AsyncSession=Depends(db_session)):
    from fastapi.responses import JSONResponse
    tables={}
    for name,model in [('animals',Animal),('weights',WeightRecord),('feeds',FeedType),('feed_lots',FeedLot),('feed_usage',FeedUsage),('expenses',Expense),('incomes',Income),('schedules',FeedingSchedule),('notes',Note)]:
        rows=(await session.execute(select(model).where(model.user_id==user.id))).scalars().all()
        tables[name]=[{c.name:getattr(r,c.name) for c in model.__table__.columns if c.name!='user_id'} for r in rows]
    return JSONResponse({'format':'chorva-pro-backup-v1','created_at':datetime.utcnow().isoformat(),'telegram_id':user.telegram_id,'data':tables},headers={'Content-Disposition':'attachment; filename=chorva-pro-backup.json'})
