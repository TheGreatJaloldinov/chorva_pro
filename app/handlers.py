import json, os, tempfile
from datetime import datetime, date, timedelta
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, FSInputFile
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from app.db import Session, get_user, Animal, WeightRecord, FeedType, FeedLot, FeedingSchedule, FeedingReminder, Expense, Income, Note
from app.keyboards import MAIN, BACK, ID_MODE, KIND_KB, UNKNOWN, SKIP, animals_kb, animal_profile_kb, calendar_kb, schedule_times_kb
from app.config import DATA_DIR
from app.states import AddAnimal, AddAnimalPhoto, AddFeed, AddWeight, AddSchedule, EditReminder, AddNote, AddExpense, AddIncome, SearchAnimals, SellAnimal, RestoreBackup, SetFeedAlert, EditAnimal

router = Router()

async def owner(session, tg_id):
    return await get_user(session, tg_id)

async def get_animal(session, user_id, animal_id):
    return (await session.execute(select(Animal).where(Animal.id==animal_id, Animal.user_id==user_id))).scalar_one_or_none()

async def flow_prompt(message: Message, state: FSMContext, text: str, reply_markup=None, parse_mode=None):
    """Keep a single bot prompt for multi-step forms; remove typed replies when Telegram permits."""
    data=await state.get_data()
    try:
        await message.bot.delete_message(message.chat.id, message.message_id)
    except Exception:
        pass
    chat_id=data.get("flow_chat_id", message.chat.id)
    message_id=data.get("flow_message_id")
    if message_id:
        try:
            await message.bot.edit_message_text(text, chat_id=chat_id, message_id=message_id, reply_markup=reply_markup, parse_mode=parse_mode)
            return
        except Exception:
            pass
    sent=await message.answer(text,reply_markup=reply_markup,parse_mode=parse_mode)
    await state.update_data(flow_chat_id=sent.chat.id,flow_message_id=sent.message_id)

async def callback_flow_prompt(call: CallbackQuery, state: FSMContext, text: str, reply_markup=None, parse_mode=None):
    await state.update_data(flow_chat_id=call.message.chat.id,flow_message_id=call.message.message_id)
    await call.message.edit_text(text,reply_markup=reply_markup,parse_mode=parse_mode)

@router.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()
    async with Session() as s:
        await get_user(s, message.from_user.id, message.from_user.full_name)
    await message.answer(
        f"🌿 <b>CHORVA PRO</b>ga xush kelibsiz, {message.from_user.first_name}!\n\n🐄 Xo‘jaligingizni qulay boshqarish uchun bo‘limni tanlang.",
        reply_markup=MAIN, parse_mode="HTML")

@router.callback_query(F.data == "nav:home")
async def nav_home(call: CallbackQuery, state: FSMContext):
    await state.clear()
    text = "🌿 <b>CHORVA PRO</b>\n\n🐄 Xo‘jaligingizni boshqarish uchun bo‘limni tanlang."
    try: await call.message.edit_text(text, reply_markup=MAIN, parse_mode="HTML")
    except Exception: await call.message.answer(text, reply_markup=MAIN, parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data == "nav:back")
async def nav_back(call: CallbackQuery, state: FSMContext):
    await state.clear()
    try: await call.message.edit_text("🏠 <b>Bosh menyu</b>\nKerakli bo‘limni tanlang.", reply_markup=MAIN, parse_mode="HTML")
    except Exception: await call.message.answer("🏠 Bosh menyu", reply_markup=MAIN)
    await call.answer()

@router.callback_query(F.data == "menu:animals")
async def menu_animals(call: CallbackQuery):
    async with Session() as s:
        u = await owner(s, call.from_user.id)
        rows = (await s.execute(select(Animal).where(Animal.user_id==u.id, Animal.status=="active").order_by(Animal.code))).scalars().all()
        if not rows:
            text = "🐾 <b>Chorvalar ro‘yxati bo‘sh</b>\n\nBirinchi chorvangizni qo‘shish uchun quyidagi tugmani bosing."
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="➕ Chorva qo‘shish", callback_data="menu:add_animal")], [InlineKeyboardButton(text="🗃 Arxiv", callback_data="animals:archive")], [InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="nav:home")]])
        else:
            text = "🐄 <b>Chorvalaringiz</b>\n\n" + "\n".join([f"• <b>{a.code}</b> | {a.kind} | {a.current_weight:g} kg" for a in rows]) + "\n\nBatafsil ko‘rish uchun hayvonni tanlang:"
            kb = animals_kb(rows)
    try: await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception: await call.message.answer(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data == "menu:add_animal")
async def menu_add_animal(call: CallbackQuery, state: FSMContext):
    await state.clear(); await state.set_state(AddAnimal.code); await state.update_data(flow_chat_id=call.message.chat.id,flow_message_id=call.message.message_id)
    await call.message.edit_text("🐾 <b>Yangi chorva qo‘shish</b>\n\nID raqamini tanlang:", reply_markup=ID_MODE, parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data == "menu:feed")
async def menu_feed_callback(call: CallbackQuery):
    await show_feed_menu(call.message, call.from_user.id, edit=True)
    await call.answer()

@router.callback_query(F.data == "menu:schedule")
async def menu_schedule_callback(call: CallbackQuery):
    async with Session() as s:
        u=await owner(s,call.from_user.id); rows=(await s.execute(select(Animal).where(Animal.user_id==u.id,Animal.status=="active"))).scalars().all()
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"🐾 {a.code} · {a.kind}",callback_data=f"schedule:{a.id}")] for a in rows] + [[InlineKeyboardButton(text="🏠 Bosh menyu",callback_data="nav:home")]])
    text="⏰ <b>Oziqlantirish</b>\n\n" + ("Jadval yaratish yoki ko‘rish uchun chorvani tanlang:" if rows else "Avval chorva qo‘shing.")
    await call.message.edit_text(text,reply_markup=kb,parse_mode="HTML"); await call.answer()

@router.callback_query(F.data == "menu:weight")
async def menu_weight_callback(call: CallbackQuery):
    async with Session() as s:
        u=await owner(s,call.from_user.id); rows=(await s.execute(select(Animal).where(Animal.user_id==u.id,Animal.status=="active"))).scalars().all()
    kb=animals_kb(rows,"weight")
    await call.message.edit_text("⚖️ <b>Vazn nazorati</b>\n\nVazn kiritiladigan chorvani tanlang:",reply_markup=kb,parse_mode="HTML"); await call.answer()

@router.callback_query(F.data == "menu:finance")
async def menu_finance_callback(call: CallbackQuery):
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➖ Xarajat qo‘shish",callback_data="finance:expense")],
        [InlineKeyboardButton(text="➕ Daromad qo‘shish",callback_data="finance:income")],
        [InlineKeyboardButton(text="📊 Moliyaviy natija",callback_data="finance:summary")],
        [InlineKeyboardButton(text="🏠 Bosh menyu",callback_data="nav:home")]])
    await call.message.edit_text("💰 <b>Moliyaviy boshqaruv</b>\n\nXarajat va daromadlarni boshqaring.",reply_markup=kb,parse_mode="HTML"); await call.answer()

@router.callback_query(F.data == "menu:reports")
async def menu_reports_callback(call: CallbackQuery):
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📈 Umumiy hisobot",callback_data="report:summary")],
        [InlineKeyboardButton(text="📅 Kunlik",callback_data="report:period:day"),InlineKeyboardButton(text="📆 Haftalik",callback_data="report:period:week"),InlineKeyboardButton(text="🗓 Oylik",callback_data="report:period:month")],
        [InlineKeyboardButton(text="🌾 Yem sarfi",callback_data="report:feed")],
        [InlineKeyboardButton(text="📥 Excel yuklab olish",callback_data="report:excel")],
        [InlineKeyboardButton(text="💾 Backup olish",callback_data="report:backup")],
        [InlineKeyboardButton(text="♻️ Backupdan tiklash",callback_data="report:restore")],
        [InlineKeyboardButton(text="🏠 Bosh menyu",callback_data="nav:home")]])
    await call.message.edit_text("📊 <b>Hisobotlar markazi</b>\n\nKerakli hisobotni tanlang:",reply_markup=kb,parse_mode="HTML"); await call.answer()

@router.callback_query(F.data == "menu:settings")
async def menu_settings_callback(call: CallbackQuery):
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 Bosh menyu",callback_data="nav:home")]])
    await call.message.edit_text("⚙️ <b>Sozlamalar</b>\n\n🇺🇿 Til: O‘zbekcha (lotin)\n💵 Valyuta: UZS\n⚖️ Vazn: kg\n🕒 Vaqt mintaqasi: Asia/Tashkent\n\n💾 Backup va hisobotlar «Hisobotlar» bo‘limida.",reply_markup=kb,parse_mode="HTML"); await call.answer()

@router.callback_query(F.data.startswith("animal:"))
async def animal_profile(call: CallbackQuery):
    animal_id=int(call.data.split(":")[1])
    async with Session() as s:
        u=await owner(s,call.from_user.id); a=await get_animal(s,u.id,animal_id)
        if not a: await call.answer("Chorva topilmadi", show_alert=True); return
        text=(f"🐾 <b>{a.kind} #{a.code}</b>\n\n📸 Rasm: {'Biriktirilgan' if a.photo_file_id else 'Hali yo‘q'}\n🧬 Zoti: {a.breed or 'Kiritilmagan'}\n⚧ Jinsi: {a.sex or 'Kiritilmagan'}\nYoshi: {a.age_months} oy\nOxirgi vazni: {a.current_weight:g} kg\nXarid sanasi: {a.purchase_date or 'Kiritilmagan'}\nXarid narxi: {a.purchase_price:,.0f} so‘m\nIzoh: {a.note or 'Yo‘q'}")
        if a.photo_file_id:
            await call.message.edit_text(text, reply_markup=animal_profile_kb(a.id), parse_mode="HTML")
        else:
            await call.message.edit_text(text, reply_markup=animal_profile_kb(a.id), parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data.startswith("animalphoto:view:"))
async def animal_photo_view(call: CallbackQuery):
    aid=int(call.data.split(":")[2])
    async with Session() as s:
        u=await owner(s,call.from_user.id); a=await get_animal(s,u.id,aid)
        if not a or not a.photo_file_id:
            await call.answer("Bu chorva profilida rasm yo‘q.",show_alert=True); return
        await call.message.answer_photo(a.photo_file_id,caption=f"📸 {a.kind} · ID {a.code}")
    await call.answer()

@router.callback_query(F.data.startswith("animalphoto:"))
async def animal_photo_start(call: CallbackQuery, state: FSMContext):
    aid=int(call.data.split(":")[1]); await state.clear(); await state.update_data(animal_id=aid,flow_chat_id=call.message.chat.id,flow_message_id=call.message.message_id); await state.set_state(AddAnimalPhoto.photo)
    await call.message.edit_text("📸 <b>Chorva rasmini yuboring</b>\n\nYangi rasm profilga biriktiriladi.", reply_markup=BACK, parse_mode="HTML")
    await call.answer()

@router.message(AddAnimalPhoto.photo, F.photo)
async def animal_photo_save(message: Message, state: FSMContext):
    d=await state.get_data()
    async with Session() as s:
        u=await owner(s,message.from_user.id); a=await get_animal(s,u.id,d["animal_id"])
        if not a: await message.answer("⚠️ Chorva topilmadi.",reply_markup=MAIN); await state.clear(); return
        a.photo_file_id=message.photo[-1].file_id; await s.commit()
        code=a.code
    try: await message.bot.delete_message(message.chat.id,message.message_id)
    except Exception: pass
    await state.clear()
    from aiogram.types import InlineKeyboardMarkup,InlineKeyboardButton
    kb=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Profilga qaytish",callback_data=f"animal:{d['animal_id']}")],[InlineKeyboardButton(text="🏠 Bosh menyu",callback_data="nav:home")]])
    try: await message.bot.edit_message_text(f"📸 <b>{code}</b> uchun rasm muvaffaqiyatli saqlandi.",chat_id=d["flow_chat_id"],message_id=d["flow_message_id"],reply_markup=kb,parse_mode="HTML")
    except Exception: await message.answer(f"📸 {code} uchun rasm saqlandi.",reply_markup=kb)

@router.callback_query(F.data=="animals:search")
async def search_start(call:CallbackQuery,state:FSMContext):
    await state.clear(); await state.set_state(SearchAnimals.query); await state.update_data(prompt_message_id=call.message.message_id, prompt_chat_id=call.message.chat.id)
    await call.message.edit_text("🔎 <b>Chorva qidirish</b>\n\nID, turi, zot yoki yoshni kiriting:",reply_markup=BACK,parse_mode="HTML")
    await call.answer()

@router.message(SearchAnimals.query)
async def search_results(message:Message,state:FSMContext):
    q=message.text.strip().lower()
    d=await state.get_data()
    async with Session() as s:
        u=await owner(s,message.from_user.id)
        rows=(await s.execute(select(Animal).where(Animal.user_id==u.id,Animal.status=="active"))).scalars().all()
        matches=[a for a in rows if q in a.code.lower() or q in a.kind.lower() or q in (a.breed or "").lower() or q in str(a.age_months)]
    await state.clear()
    text="🔎 <b>Qidiruv natijalari</b>\n\n"+(f"{len(matches)} ta chorva topildi. Tanlang:" if matches else "Mos chorva topilmadi.")
    try: await message.bot.edit_message_text(text,chat_id=d["prompt_chat_id"],message_id=d["prompt_message_id"],reply_markup=animals_kb(matches) if matches else MAIN,parse_mode="HTML")
    except Exception: await message.answer(text,reply_markup=animals_kb(matches) if matches else MAIN,parse_mode="HTML")

@router.callback_query(F.data=="animals:archive")
async def show_archive(call:CallbackQuery):
    async with Session() as s:
        u=await owner(s,call.from_user.id)
        rows=(await s.execute(select(Animal).where(Animal.user_id==u.id,Animal.status=="archived").order_by(Animal.code))).scalars().all()
        if not rows: await call.message.edit_text("🗃 Arxiv hozircha bo‘sh.",reply_markup=animals_kb([],"arch")); await call.answer(); return
        await call.message.edit_text("🗃 <b>Arxivdagi chorvalar</b>\n\nKerakli chorvani tanlang:",reply_markup=animals_kb(rows,"arch"),parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data.startswith("arch:"))
async def restore_animal(call:CallbackQuery):
    aid=int(call.data.split(":")[1])
    async with Session() as s:
        u=await owner(s,call.from_user.id); a=await get_animal(s,u.id,aid)
        if not a: await call.answer("Topilmadi",show_alert=True); return
        a.status="active"; await s.commit()
    await call.message.edit_text(f"♻️ <b>{a.code}</b> yana faol ro‘yxatga qaytarildi. Oziqlantirish jadvalini kerak bo‘lsa qayta yoqing.",reply_markup=animal_profile_kb(a.id),parse_mode="HTML")
    await call.answer()

@router.message(F.text == "➕ Chorva qo‘shish")
async def add_animal_start(message: Message, state: FSMContext):
    await state.clear(); await state.set_state(AddAnimal.code)
    await message.answer("🐾 Yangi chorva ID raqamini tanlang:", reply_markup=ID_MODE)

async def _next_animal_kind(target, state, code):
    await state.update_data(code=code); await state.set_state(AddAnimal.kind)
    await target.edit_text(f"🆔 ID: <b>{code}</b>\n\n🐄 Chorva turini tanlang. Jins avtomatik belgilanadi:", reply_markup=KIND_KB, parse_mode="HTML")

@router.callback_query(F.data == "animalid:auto")
async def animal_id_auto(call: CallbackQuery, state: FSMContext):
    async with Session() as s:
        u=await owner(s,call.from_user.id)
        existing=(await s.execute(select(Animal.code).where(Animal.user_id==u.id))).scalars().all()
        nums=[int(x) for x in existing if x.isdigit()]
        code=f"{max(nums,default=0)+1:03d}"
        while code in existing:
            nums.append(int(code)); code=f"{max(nums)+1:03d}"
    await _next_animal_kind(call.message,state,code); await call.answer()

@router.callback_query(F.data == "animalid:manual")
async def animal_id_manual(call: CallbackQuery, state: FSMContext):
    await state.set_state(AddAnimal.code); await state.update_data(flow_chat_id=call.message.chat.id,flow_message_id=call.message.message_id)
    await call.message.edit_text("✍️ Chorva uchun ID raqamini kiriting:", reply_markup=BACK)
    await call.answer()

@router.message(AddAnimal.code)
async def animal_code(message: Message, state: FSMContext):
    code=(message.text or "").strip()
    if not code or len(code)>40:
        await flow_prompt(message,state,"⚠️ ID 1–40 belgidan iborat bo‘lishi kerak. Qayta kiriting:",reply_markup=BACK); return
    async with Session() as s:
        u=await owner(s,message.from_user.id)
        exists=(await s.execute(select(Animal).where(Animal.user_id==u.id,Animal.code==code))).scalar_one_or_none()
        if exists: await flow_prompt(message,state,"⚠️ Bu ID band. Boshqa ID kiriting:",reply_markup=BACK); return
    await state.update_data(code=code); await state.set_state(AddAnimal.kind)
    await flow_prompt(message,state,f"🆔 ID: <b>{code}</b>\n\n🐄 Chorva turini tanlang. Jins avtomatik belgilanadi:", reply_markup=KIND_KB, parse_mode="HTML")

@router.callback_query(F.data.startswith("kind:"))
async def animal_kind_button(call: CallbackQuery, state: FSMContext):
    value=call.data.split(":",1)[1]
    mapping={"sigir":("Sigir","Urg‘ochi"),"buqa":("Buqa","Erkak"),"qochqor":("Qo‘chqor","Erkak"),"sovliq":("Sovliq","Urg‘ochi")}
    kind,sex=mapping[value]
    await state.update_data(kind=kind,sex=sex,subtype=value); await state.set_state(AddAnimal.breed)
    await callback_flow_prompt(call,state,f"🐾 {kind} ({sex.lower()})\n\n🧬 Zotini kiriting yoki bilmasangiz tugmani bosing:",reply_markup=UNKNOWN)
    await call.answer()

@router.callback_query(F.data == "skip:unknown")
async def skip_unknown(call: CallbackQuery, state: FSMContext):
    current=await state.get_state()
    if current==AddAnimal.breed.state:
        await state.update_data(breed=""); await state.set_state(AddAnimal.age)
        await callback_flow_prompt(call,state,"🎂 Yoshini oyda kiriting. Masalan: 12",reply_markup=UNKNOWN)
    elif current==AddAnimal.date.state:
        await state.update_data(purchase_date=""); await state.set_state(AddAnimal.price)
        await callback_flow_prompt(call,state,"💰 Xarid narxini so‘mda kiriting. Noma'lum bo‘lsa 0 kiriting:",reply_markup=BACK)
    elif current==AddAnimal.age.state:
        await state.update_data(age_months=0); await state.set_state(AddAnimal.weight)
        await callback_flow_prompt(call,state,"⚖️ Hozirgi vaznini kilogrammda kiriting. Masalan: 250",reply_markup=BACK)
    elif current==AddAnimal.price.state:
        await state.update_data(price=0); await state.set_state(AddAnimal.photo)
        await callback_flow_prompt(call,state,"📸 Chorva rasmini yuboring yoki tugma orqali o‘tkazing:",reply_markup=SKIP)
    await call.answer()

@router.callback_query(F.data == "skip:field")
async def skip_field(call: CallbackQuery, state: FSMContext):
    current=await state.get_state()
    if current==AddAnimal.photo.state:
        await state.update_data(photo=""); await state.set_state(AddAnimal.note)
        await callback_flow_prompt(call,state,"📝 Qo‘shimcha izoh kiriting yoki tugma orqali o‘tkazing:",reply_markup=SKIP)
    elif current==AddAnimal.note.state:
        await save_animal_from_state(call.message, state, call.from_user.id, "")
    await call.answer()


@router.message(AddAnimal.kind)
async def animal_kind(message: Message,state:FSMContext):
    if message.text not in ["Sigir","Buqa","Qo‘y"]: await message.answer("Sigir, Buqa yoki Qo‘y tugmasidan birini tanlang."); return
    await state.update_data(kind=message.text); await state.set_state(AddAnimal.breed); await flow_prompt(message,state,"🧬 Zotini kiriting:",reply_markup=UNKNOWN)

@router.message(AddAnimal.breed)
async def animal_breed(message:Message,state:FSMContext):
    await state.update_data(breed="" if message.text.strip()=="-" else message.text.strip()); await state.set_state(AddAnimal.age); await flow_prompt(message,state,"🎂 Yoshini oyda kiriting. Masalan: 12",reply_markup=UNKNOWN)

@router.message(AddAnimal.age)
async def animal_age(message:Message,state:FSMContext):
    try: age=int(message.text); assert age>=0
    except: await flow_prompt(message,state,"⚠️ Yoshni oyda butun son bilan kiriting:",reply_markup=UNKNOWN); return
    await state.update_data(age_months=age); await state.set_state(AddAnimal.weight); await flow_prompt(message,state,"⚖️ Hozirgi vaznini kilogrammda kiriting. Masalan: 250",reply_markup=BACK)

@router.message(AddAnimal.weight)
async def animal_weight(message:Message,state:FSMContext):
    try: weight=float(message.text.replace(",",".")); assert weight>=0
    except: await flow_prompt(message,state,"⚠️ Vaznni kg da raqam bilan kiriting:",reply_markup=BACK); return
    await state.update_data(weight=weight); await state.set_state(AddAnimal.date); today=date.today(); await flow_prompt(message,state,"📅 <b>Xarid sanasini tanlang</b>\n\nKunni kalendardan bosing yoki Bugun/Kecha tugmasidan foydalaning:",reply_markup=calendar_kb(today.year,today.month,True),parse_mode="HTML")

@router.message(AddAnimal.date)
async def animal_date_text(message:Message,state:FSMContext):
    await flow_prompt(message,state,"📅 Sanani yozish shart emas. Quyidagi kalendardan kunni tanlang:",reply_markup=calendar_kb(date.today().year,date.today().month,True))


async def _calendar_selected(call:CallbackQuery,state:FSMContext,value:str):
    current=await state.get_state(); d=await state.get_data()
    if current==AddAnimal.date.state:
        await state.update_data(purchase_date=value); await state.set_state(AddAnimal.price)
        await callback_flow_prompt(call,state,"💰 Xarid narxini so‘mda kiriting. Noma’lum bo‘lsa 0 kiriting:",reply_markup=BACK)
    elif current==AddFeed.date.state:
        await state.update_data(date=value); await state.set_state(AddFeed.supplier)
        await callback_flow_prompt(call,state,"🚚 Yetkazib beruvchi nomini kiriting yoki o‘tkazib yuboring:",reply_markup=SKIP)
    elif current==SellAnimal.sale_date.state:
        price=d.get("price",0); aid=d.get("animal_id")
        async with Session() as s:
            u=await owner(s,call.from_user.id); a=await get_animal(s,u.id,aid)
            if not a: await call.answer("Chorva topilmadi",show_alert=True); return
            a.status="archived"; s.add(Income(user_id=u.id,animal_id=a.id,category="Chorva sotish",amount=price,income_date=value,description=f"{a.code} chorva sotildi"))
            schedules=(await s.execute(select(FeedingSchedule).where(FeedingSchedule.user_id==u.id,FeedingSchedule.animal_id==a.id))).scalars().all()
            for x in schedules: x.active=False
            await s.commit()
        await state.clear(); await callback_flow_prompt(call,state,f"✅ {a.code} sotildi va arxivga o‘tkazildi. Sana: {value}\n💰 Narx: {price:,.0f} so‘m",reply_markup=MAIN)
    elif current==AddExpense.date.state:
        await state.update_data(date=value); await state.set_state(AddExpense.description)
        await callback_flow_prompt(call,state,"📝 Xarajat izohini kiriting yoki ⏭ tugmasini bosing:",reply_markup=SKIP)
    elif current==AddIncome.date.state:
        await state.update_data(date=value); await state.set_state(AddIncome.description)
        await callback_flow_prompt(call,state,"📝 Daromad izohini kiriting yoki ⏭ tugmasini bosing:",reply_markup=SKIP)
    else:
        await call.answer("Sana tanlash jarayoni faol emas.",show_alert=True); return
    await call.answer()

@router.callback_query(F.data=="cal:noop")
async def calendar_noop(call:CallbackQuery): await call.answer()

@router.callback_query(F.data=="cal:today")
async def calendar_today(call:CallbackQuery,state:FSMContext): await _calendar_selected(call,state,date.today().isoformat())

@router.callback_query(F.data=="cal:yesterday")
async def calendar_yesterday(call:CallbackQuery,state:FSMContext): await _calendar_selected(call,state,(date.today()-timedelta(days=1)).isoformat())

@router.callback_query(F.data=="cal:unknown")
async def calendar_unknown(call:CallbackQuery,state:FSMContext):
    if await state.get_state()!=AddAnimal.date.state: await call.answer("Bu sana majburiy.",show_alert=True); return
    await state.update_data(purchase_date=""); await state.set_state(AddAnimal.price)
    await callback_flow_prompt(call,state,"💰 Xarid narxini so‘mda kiriting. Noma’lum bo‘lsa 0 kiriting:",reply_markup=BACK); await call.answer()

@router.callback_query(F.data.startswith("cal:month:"))
async def calendar_month(call:CallbackQuery,state:FSMContext):
    y,m=map(int,call.data.split(":")[2].split("-")); current=await state.get_state()
    kb=calendar_kb(y,m,current==AddAnimal.date.state)
    months=["Yanvar","Fevral","Mart","Aprel","May","Iyun","Iyul","Avgust","Sentabr","Oktabr","Noyabr","Dekabr"]
    title="📅 <b>Sanani tanlang</b>\n\n"+months[m-1]+f" {y}"
    try: await call.message.edit_text(title,reply_markup=kb,parse_mode="HTML")
    except Exception: await call.message.edit_reply_markup(reply_markup=kb)
    await call.answer()

@router.callback_query(F.data.startswith("cal:day:"))
async def calendar_day(call:CallbackQuery,state:FSMContext): await _calendar_selected(call,state,call.data.split(":",2)[2])

@router.message(AddAnimal.price)
async def animal_price(message:Message,state:FSMContext):
    try: price=float(message.text.replace(" ","").replace(",",".")); assert price>=0
    except: await flow_prompt(message,state,"⚠️ Narxni raqam bilan kiriting:",reply_markup=BACK); return
    await state.update_data(price=price); await state.set_state(AddAnimal.photo); await flow_prompt(message,state,"📸 Chorva rasmini yuboring yoki tugma orqali o‘tkazing:",reply_markup=SKIP)

@router.message(AddAnimal.photo, F.photo)
async def animal_photo(message:Message,state:FSMContext):
    await state.update_data(photo=message.photo[-1].file_id); await state.set_state(AddAnimal.note)
    await flow_prompt(message,state,"📝 Qo‘shimcha izoh kiriting yoki tugma orqali o‘tkazing:",reply_markup=SKIP)

@router.message(AddAnimal.photo)
async def animal_photo_invalid(message:Message,state:FSMContext):
    await flow_prompt(message,state,"📸 Iltimos, rasm yuboring yoki pastdagi ⏭ O‘tkazib yuborish tugmasini bosing.",reply_markup=SKIP)

@router.message(AddAnimal.note)
async def animal_save(message:Message,state:FSMContext):
    await save_animal_from_state(message,state,message.from_user.id,(message.text or "").strip())

async def save_animal_from_state(target,state,telegram_id,note_text):
    d=await state.get_data(); note="" if note_text in ["-", ""] else note_text
    async with Session() as s:
        u=await owner(s,telegram_id)
        a=Animal(user_id=u.id,code=d['code'],kind=d['kind'],breed=d.get('breed',''),sex=d.get('sex',''),age_months=d['age_months'],current_weight=d['weight'],purchase_date=d.get('purchase_date',''),purchase_price=d['price'],photo_file_id=d.get('photo',''),note=note)
        s.add(a); await s.flush()
        if d['weight']>0: s.add(WeightRecord(user_id=u.id,animal_id=a.id,weight=d['weight']))
        if d['price']>0: s.add(Expense(user_id=u.id,animal_id=a.id,category="Chorva xaridi",amount=d['price'],expense_date=d.get('purchase_date') or date.today().isoformat(),description=f"Chorva #{a.code} xaridi"))
        await s.commit()
    await state.clear()
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🐄 Chorvalarim",callback_data="menu:animals")],[InlineKeyboardButton(text="➕ Yana chorva qo‘shish",callback_data="menu:add_animal")],[InlineKeyboardButton(text="🏠 Bosh menyu",callback_data="nav:home")]])
    result=f"✅ <b>Chorva muvaffaqiyatli qo‘shildi!</b>\n\n🆔 ID: {d['code']}\n🐾 Turi: {d['kind']}\n⚧ Jinsi: {d.get('sex','')}"
    if d.get("flow_message_id"):
        try:
            await target.bot.edit_message_text(result,chat_id=d["flow_chat_id"],message_id=d["flow_message_id"],reply_markup=kb,parse_mode="HTML"); return
        except Exception: pass
    await target.answer(result,reply_markup=kb,parse_mode="HTML")

@router.callback_query(F.data.startswith("editmenu:"))
async def edit_animal_menu(call:CallbackQuery):
    aid=int(call.data.split(":")[1])
    from aiogram.types import InlineKeyboardMarkup,InlineKeyboardButton
    kb=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧬 Zot",callback_data=f"edit:{aid}:breed")],
        [InlineKeyboardButton(text="Yoshi",callback_data=f"edit:{aid}:age_months"),InlineKeyboardButton(text="Vazni",callback_data=f"edit:{aid}:current_weight")],
        [InlineKeyboardButton(text="Xarid sanasi",callback_data=f"edit:{aid}:purchase_date"),InlineKeyboardButton(text="Xarid narxi",callback_data=f"edit:{aid}:purchase_price")],
        [InlineKeyboardButton(text="Izoh",callback_data=f"edit:{aid}:note")]
    ])
    await call.message.edit_text("✏️ <b>Qaysi ma’lumotni o‘zgartiramiz?</b>",reply_markup=kb,parse_mode="HTML"); await call.answer()

@router.callback_query(F.data.startswith("edit:"))
async def edit_animal_start(call:CallbackQuery,state:FSMContext):
    _,aid,field=call.data.split(":"); aid=int(aid)
    labels={"breed":"Yangi zot nomi","age_months":"Yangi yosh (oyda)","current_weight":"Yangi vazn (kg)","purchase_date":"Xarid sanasi YYYY-MM-DD yoki -","purchase_price":"Xarid narxi (so‘m)","note":"Yangi izoh"}
    if field not in labels: await call.answer("Maydon noto‘g‘ri",show_alert=True); return
    await state.clear(); await state.update_data(animal_id=aid,field=field); await state.set_state(EditAnimal.value)
    await call.message.answer(labels[field]+":",reply_markup=BACK); await call.answer()

@router.message(EditAnimal.value)
async def edit_animal_save(message:Message,state:FSMContext):
    d=await state.get_data(); field=d['field']; raw=message.text.strip()
    try:
        if field in ["age_months"]: value=int(raw); assert value>=0
        elif field in ["current_weight","purchase_price"]: value=float(raw.replace(" ","").replace(",",".")); assert value>=0
        elif field=="purchase_date":
            value="" if raw=="-" else raw
            if value: datetime.strptime(value,"%Y-%m-%d")
        else: value=raw
    except: await message.answer("Kiritilgan qiymat noto‘g‘ri. Qayta urinib ko‘ring:"); return
    async with Session() as s:
        u=await owner(s,message.from_user.id); a=await get_animal(s,u.id,d['animal_id'])
        if not a: await message.answer("Chorva topilmadi.",reply_markup=MAIN); await state.clear(); return
        setattr(a,field,value)
        if field=="current_weight": s.add(WeightRecord(user_id=u.id,animal_id=a.id,weight=value))
        if field in ["purchase_price","purchase_date"]:
            purchase=(await s.execute(select(Expense).where(Expense.user_id==u.id,Expense.animal_id==a.id,Expense.category=="Chorva xaridi"))).scalar_one_or_none()
            if purchase:
                if field=="purchase_price": purchase.amount=value
                else: purchase.expense_date=value or date.today().isoformat()
        await s.commit()
    await state.clear(); await message.answer("✅ Chorva profili yangilandi.",reply_markup=MAIN)

@router.message(F.text == "⚖️ Vazn nazorati")
async def weight_menu(message:Message):
    async with Session() as s:
        u=await owner(s,message.from_user.id); rows=(await s.execute(select(Animal).where(Animal.user_id==u.id,Animal.status=="active"))).scalars().all()
        if not rows: await message.answer("Avval chorva qo‘shing.",reply_markup=MAIN); return
        await message.answer("Vazn kiritiladigan chorvani tanlang:",reply_markup=animals_kb(rows,"weight"))

@router.callback_query(F.data.startswith("weight:"))
async def weight_start(call:CallbackQuery,state:FSMContext):
    aid=int(call.data.split(":")[1])
    async with Session() as s:
        u=await owner(s,call.from_user.id); a=await get_animal(s,u.id,aid)
        if not a: await call.answer("Topilmadi",show_alert=True); return
    await state.clear(); await state.update_data(animal_id=aid); await state.set_state(AddWeight.value)
    await call.message.answer(f"{a.code} ID chorvaning yangi vaznini kg da kiriting:",reply_markup=BACK); await call.answer()

@router.message(AddWeight.value)
async def weight_save(message:Message,state:FSMContext):
    try: value=float(message.text.replace(",",".")); assert value>0
    except: await message.answer("Vaznni musbat raqam bilan kiriting:"); return
    d=await state.get_data()
    async with Session() as s:
        u=await owner(s,message.from_user.id); a=await get_animal(s,u.id,d['animal_id'])
        if not a: await message.answer("Chorva topilmadi.",reply_markup=MAIN); await state.clear(); return
        old=a.current_weight; a.current_weight=value; s.add(WeightRecord(user_id=u.id,animal_id=a.id,weight=value)); await s.commit()
    await state.clear(); diff=value-old
    await message.answer(f"✅ Vazn saqlandi: {value:g} kg\nO‘zgarish: {'+' if diff>=0 else ''}{diff:g} kg",reply_markup=MAIN)

async def show_feed_menu(message, telegram_id, edit=False):
    async with Session() as s:
        u=await owner(s,telegram_id)
        rows=(await s.execute(select(FeedType).where(FeedType.user_id==u.id).order_by(FeedType.name))).scalars().all()
        lines=[]
        for f in rows:
            lots=(await s.execute(select(func.sum(FeedLot.quantity_remaining)).where(FeedLot.user_id==u.id,FeedLot.feed_type_id==f.id))).scalar() or 0
            lines.append(f"🌾 <b>{f.name}</b>: {lots:g} kg  ·  ogohlantirish {f.low_stock_alert:g} kg")
    from aiogram.types import InlineKeyboardMarkup,InlineKeyboardButton
    kb=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="➕ Yem xaridi",callback_data="feed:add")],[InlineKeyboardButton(text="📊 Ombor hisoboti",callback_data="feed:report"),InlineKeyboardButton(text="⚠️ Qoldiq chegarasi",callback_data="feed:alerts")],[InlineKeyboardButton(text="🏠 Bosh menyu",callback_data="nav:home")]])
    text="🌾 <b>Yem-xashak ombori</b>\n\n"+("\n".join(lines) if lines else "📦 Omborda hali yem yo‘q.")
    if edit:
        await message.edit_text(text,reply_markup=kb,parse_mode="HTML")
    else:
        await message.answer(text,reply_markup=kb,parse_mode="HTML")

@router.message(F.text == "🌾 Yem-xashak")
async def feed_menu(message:Message):
    await show_feed_menu(message,message.from_user.id)

@router.callback_query(F.data=="feed:add")
async def feed_add_start(call:CallbackQuery,state:FSMContext):
    await state.clear(); await state.set_state(AddFeed.name); await state.update_data(flow_chat_id=call.message.chat.id,flow_message_id=call.message.message_id); await call.message.edit_text("🌾 <b>Yem xaridini kiritish</b>\n\nYem nomini kiriting (masalan, Kepak, Beda, Arpa):",reply_markup=BACK,parse_mode="HTML"); await call.answer()

@router.message(AddFeed.name)
async def feed_name(message:Message,state:FSMContext):
    await state.update_data(name=message.text.strip()); await state.set_state(AddFeed.quantity); await flow_prompt(message,state,"⚖️ Sotib olingan miqdor (kg):",reply_markup=BACK)

@router.message(AddFeed.quantity)
async def feed_qty(message:Message,state:FSMContext):
    try: q=float(message.text.replace(",",".")); assert q>0
    except: await flow_prompt(message,state,"⚠️ Miqdorni kg da musbat raqam bilan kiriting:",reply_markup=BACK); return
    await state.update_data(quantity=q); await state.set_state(AddFeed.price); await flow_prompt(message,state,"💰 1 kg narxi (so‘m):",reply_markup=BACK)

@router.message(AddFeed.price)
async def feed_price(message:Message,state:FSMContext):
    try: p=float(message.text.replace(" ","").replace(",",".")); assert p>=0
    except: await flow_prompt(message,state,"⚠️ Narxni raqam bilan kiriting:",reply_markup=BACK); return
    await state.update_data(price=p); await state.set_state(AddFeed.date); today=date.today(); await flow_prompt(message,state,"📅 <b>Yem xarid sanasini tanlang</b>",reply_markup=calendar_kb(today.year,today.month),parse_mode="HTML")

@router.message(AddFeed.date)
async def feed_date_text(message:Message,state:FSMContext):
    await flow_prompt(message,state,"📅 Xarid sanasini kalendardan tanlang:",reply_markup=calendar_kb(date.today().year,date.today().month))

@router.message(AddFeed.supplier)
async def feed_save(message:Message,state:FSMContext):
    d=await state.get_data(); supplier="" if message.text.strip()=="-" else message.text.strip()
    async with Session() as s:
        u=await owner(s,message.from_user.id)
        f=(await s.execute(select(FeedType).where(FeedType.user_id==u.id,func.lower(FeedType.name)==d['name'].lower()))).scalar_one_or_none()
        if not f: f=FeedType(user_id=u.id,name=d['name']); s.add(f); await s.flush()
        s.add(FeedLot(user_id=u.id,feed_type_id=f.id,purchased_at=d['date'],quantity_initial=d['quantity'],quantity_remaining=d['quantity'],unit_price=d['price'],supplier=supplier))
        s.add(Expense(user_id=u.id,category="Yem-xashak xaridi",amount=d['quantity']*d['price'],expense_date=d['date'],description=f"{d['name']} {d['quantity']:g} kg xarid"))
        await s.commit()
    await state.clear()
    from aiogram.types import InlineKeyboardMarkup,InlineKeyboardButton
    kb=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🌾 Omborga qaytish",callback_data="menu:feed")],[InlineKeyboardButton(text="🏠 Bosh menyu",callback_data="nav:home")]])
    try: await message.bot.edit_message_text(f"✅ <b>{d['name']}</b> omborga qo‘shildi: {d['quantity']:g} kg.\n💰 Jami: {d['quantity']*d['price']:,.0f} so‘m",chat_id=d["flow_chat_id"],message_id=d["flow_message_id"],reply_markup=kb,parse_mode="HTML")
    except Exception: await message.answer(f"✅ {d['name']} omborga qo‘shildi.",reply_markup=kb)

@router.callback_query(F.data=="feed:report")
async def feed_report(call:CallbackQuery):
    async with Session() as s:
        u=await owner(s,call.from_user.id); rows=(await s.execute(select(FeedType).where(FeedType.user_id==u.id))).scalars().all(); out=[]
        for f in rows:
            lots=(await s.execute(select(FeedLot).where(FeedLot.user_id==u.id,FeedLot.feed_type_id==f.id).order_by(FeedLot.purchased_at))).scalars().all()
            qty=sum(x.quantity_remaining for x in lots); value=sum(x.quantity_remaining*x.unit_price for x in lots)
            out.append(f"<b>{f.name}</b>: {qty:g} kg | ombor qiymati {value:,.0f} so‘m")
        await call.message.edit_text("📦 <b>Ombor hisoboti</b>\n\n"+("\n".join(out) if out else "Ma'lumot yo‘q."),reply_markup=BACK,parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data=="feed:alerts")
async def feed_alerts(call:CallbackQuery):
    from aiogram.types import InlineKeyboardMarkup,InlineKeyboardButton
    async with Session() as s:
        u=await owner(s,call.from_user.id); feeds=(await s.execute(select(FeedType).where(FeedType.user_id==u.id).order_by(FeedType.name))).scalars().all()
        kb=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"{f.name} · {f.low_stock_alert:g} kg",callback_data=f"feedalert:{f.id}")] for f in feeds])
    if not feeds: await call.message.edit_text("📦 Avval yem turini omborga kiriting.",reply_markup=BACK)
    else: await call.message.edit_text("⚠️ Qoldiq ogohlantirish chegarasini o‘zgartirish uchun yemni tanlang:",reply_markup=kb)
    await call.answer()

@router.callback_query(F.data.startswith("feedalert:"))
async def feed_alert_set_start(call:CallbackQuery,state:FSMContext):
    fid=int(call.data.split(":")[1]); await state.clear(); await state.update_data(feed_id=fid,flow_chat_id=call.message.chat.id,flow_message_id=call.message.message_id); await state.set_state(SetFeedAlert.value)
    await call.message.edit_text("⚠️ Qoldiq necha kg dan kamayganda ogohlantirish yuborilsin? Masalan: 10",reply_markup=BACK)
    await call.answer()

@router.message(SetFeedAlert.value)
async def feed_alert_set_save(message:Message,state:FSMContext):
    try: val=float(message.text.replace(",",".")); assert val>=0
    except: await flow_prompt(message,state,"⚠️ 0 yoki undan katta miqdorni kg da kiriting:",reply_markup=BACK); return
    d=await state.get_data()
    async with Session() as s:
        u=await owner(s,message.from_user.id); f=(await s.execute(select(FeedType).where(FeedType.id==d['feed_id'],FeedType.user_id==u.id))).scalar_one_or_none()
        if not f: await message.answer("Yem topilmadi.",reply_markup=MAIN); await state.clear(); return
        f.low_stock_alert=val; await s.commit()
    await state.clear();
    from aiogram.types import InlineKeyboardMarkup,InlineKeyboardButton
    kb=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🌾 Yem-xashak",callback_data="menu:feed")],[InlineKeyboardButton(text="🏠 Bosh menyu",callback_data="nav:home")]])
    try: await message.bot.edit_message_text(f"✅ Ogohlantirish chegarasi {val:g} kg qilib saqlandi.",chat_id=d["flow_chat_id"],message_id=d["flow_message_id"],reply_markup=kb)
    except Exception: await message.answer(f"✅ Ogohlantirish chegarasi {val:g} kg qilib saqlandi.",reply_markup=kb)

@router.message(F.text == "⏰ Oziqlantirish")
async def schedule_menu(message:Message):
    async with Session() as s:
        u=await owner(s,message.from_user.id); rows=(await s.execute(select(Animal).where(Animal.user_id==u.id,Animal.status=="active"))).scalars().all()
        if not rows: await message.answer("Avval chorva qo‘shing.",reply_markup=MAIN); return
        from aiogram.types import InlineKeyboardMarkup,InlineKeyboardButton
        kb=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"{a.code} · {a.kind}",callback_data=f"schedule:{a.id}")] for a in rows])
        await message.answer("Oziqlantirish jadvali qo‘shish yoki ko‘rish uchun chorvani tanlang:",reply_markup=kb)

@router.callback_query(F.data.regexp(r"^schedule:[0-9]+$"))
async def schedule_start(call:CallbackQuery,state:FSMContext):
    aid=int(call.data.split(":")[1])
    async with Session() as s:
        u=await owner(s,call.from_user.id); a=await get_animal(s,u.id,aid)
        if not a: await call.answer("Topilmadi",show_alert=True); return
        rows=(await s.execute(select(FeedingSchedule).where(FeedingSchedule.user_id==u.id,FeedingSchedule.animal_id==aid))).scalars().all()
    from aiogram.types import InlineKeyboardMarkup,InlineKeyboardButton
    lines=[]; buttons=[]
    for x in rows:
        times=", ".join(json.loads(x.times_json))
        lines.append(f"• {times} | {'Faol' if x.active else 'To‘xtatilgan'}")
        buttons.append([InlineKeyboardButton(text=("⏸ To‘xtatish · " if x.active else "▶️ Yoqish · ")+times,callback_data=f"schedule:toggle:{x.id}")])
    buttons.append([InlineKeyboardButton(text="➕ Yangi jadval qo‘shish",callback_data=f"schedule:new:{aid}")])
    await state.clear(); await call.message.edit_text(f"🐂 {a.code} uchun oziqlantirish jadvali\n\n"+("\n".join(lines) if lines else "Hozircha jadval yo‘q."),reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)); await call.answer()

@router.callback_query(F.data.startswith("schedule:new:"))
async def schedule_new(call:CallbackQuery,state:FSMContext):
    aid=int(call.data.split(":")[2]); await state.clear(); await state.update_data(animal_id=aid,selected_times=[],flow_chat_id=call.message.chat.id,flow_message_id=call.message.message_id); await state.set_state(AddSchedule.times)
    await call.message.edit_text("⏰ <b>Oziqlantirish vaqtlarini tanlang</b>\n\nBir nechta vaqtni belgilashingiz mumkin. Tanlangan vaqt yonida ✅ paydo bo‘ladi.",reply_markup=schedule_times_kb([]),parse_mode="HTML"); await call.answer()

@router.callback_query(F.data.startswith("stime:toggle:"))
async def schedule_time_toggle(call:CallbackQuery,state:FSMContext):
    t=call.data.split(":")[2]; d=await state.get_data(); selected=list(d.get("selected_times",[]))
    if t in selected: selected.remove(t)
    else: selected.append(t)
    selected.sort(); await state.update_data(selected_times=selected)
    await call.message.edit_text("⏰ <b>Oziqlantirish vaqtlarini tanlang</b>\n\nTanlangan: "+(", ".join(selected) if selected else "hali tanlanmagan"),reply_markup=schedule_times_kb(selected),parse_mode="HTML"); await call.answer()

@router.callback_query(F.data=="stime:custom")
async def schedule_time_custom(call:CallbackQuery,state:FSMContext):
    await state.update_data(custom_time_mode=True)
    await call.message.edit_text("⌚ Qo‘shimcha vaqtni HH:MM formatida yuboring. Masalan 07:30. So‘ngra tanlash oynasiga qaytasiz.",reply_markup=BACK); await call.answer()

@router.callback_query(F.data=="stime:done")
async def schedule_time_done(call:CallbackQuery,state:FSMContext):
    d=await state.get_data(); vals=d.get("selected_times",[])
    if not vals: await call.answer("Kamida bitta vaqt tanlang.",show_alert=True); return
    await state.update_data(times=vals); await state.set_state(AddSchedule.items)
    await callback_flow_prompt(call,state,"🌾 <b>Ozuqa tarkibini belgilang</b>\n\nHar bir yemni <code>Nomi:miqdor</code> shaklida kiriting, vergul bilan ajrating.\nMasalan: Kepak:2, Beda:3, Suv:0\n💧 Suv ombordan ayrilmaydi.",reply_markup=BACK,parse_mode="HTML"); await call.answer()

@router.callback_query(F.data.startswith("schedule:toggle:"))
async def schedule_toggle(call:CallbackQuery):
    sid=int(call.data.split(":")[2])
    async with Session() as s:
        u=await owner(s,call.from_user.id); sch=(await s.execute(select(FeedingSchedule).where(FeedingSchedule.id==sid,FeedingSchedule.user_id==u.id))).scalar_one_or_none()
        if not sch: await call.answer("Jadval topilmadi",show_alert=True); return
        sch.active=not sch.active; active=sch.active; await s.commit()
    try: await call.message.edit_text(("▶️ Eslatmalar yoqildi." if active else "⏸ Eslatmalar vaqtincha to‘xtatildi."),reply_markup=BACK)
    except Exception: pass
    await call.answer()

@router.message(AddSchedule.times)
async def schedule_times_text(message:Message,state:FSMContext):
    d=await state.get_data()
    if not d.get("custom_time_mode"):
        await flow_prompt(message,state,"⏰ Vaqtlarni yozish shart emas. Tugmalardan birini tanlang:",reply_markup=schedule_times_kb(d.get("selected_times",[])))
        return
    try: datetime.strptime(message.text.strip(),"%H:%M")
    except: await flow_prompt(message,state,"⚠️ Vaqtni HH:MM ko‘rinishida kiriting. Masalan 07:30:",reply_markup=BACK); return
    vals=list(d.get("selected_times",[])); t=message.text.strip()
    if t not in vals: vals.append(t)
    vals.sort(); await state.update_data(selected_times=vals,custom_time_mode=False)
    await flow_prompt(message,state,"⏰ <b>Oziqlantirish vaqtlarini tanlang</b>\n\nTanlangan: "+", ".join(vals),reply_markup=schedule_times_kb(vals),parse_mode="HTML")

@router.message(AddSchedule.items)
async def schedule_save(message:Message,state:FSMContext):
    items=[]
    try:
        for part in message.text.split(","):
            name,qty=part.strip().rsplit(":",1); items.append({"name":name.strip(),"qty":float(qty.strip()),"water":name.strip().lower()=="suv"})
        assert items and all(x['qty']>=0 for x in items)
    except: await message.answer("Format noto‘g‘ri. Masalan: Kepak:2, Beda:3, Suv:0"); return
    d=await state.get_data()
    async with Session() as s:
        u=await owner(s,message.from_user.id)
        s.add(FeedingSchedule(user_id=u.id,animal_id=d['animal_id'],times_json=json.dumps(d['times']),items_json=json.dumps(items,ensure_ascii=False),active=True)); await s.commit()
    d=await state.get_data(); await state.clear()
    try:
        await message.bot.delete_message(message.chat.id,message.message_id)
    except Exception: pass
    try:
        await message.bot.edit_message_text("✅ Oziqlantirish jadvali saqlandi. Bot belgilangan vaqtlarda eslatma yuboradi.",chat_id=d["flow_chat_id"],message_id=d["flow_message_id"],reply_markup=MAIN)
    except Exception:
        await message.answer("✅ Oziqlantirish jadvali saqlandi. Bot belgilangan vaqtlarda eslatma yuboradi.",reply_markup=MAIN)

@router.callback_query(F.data.startswith("rem:"))
async def reminder_action(call:CallbackQuery,state:FSMContext):
    _,action,rid=call.data.split(":"); rid=int(rid)
    async with Session() as s:
        u=await owner(s,call.from_user.id); r=(await s.execute(select(FeedingReminder).where(FeedingReminder.id==rid,FeedingReminder.user_id==u.id))).scalar_one_or_none()
        if not r: await call.answer("Eslatma topilmadi",show_alert=True); return
        if r.status!="pending": await call.answer("Bu eslatma oldin qayta ishlangan.",show_alert=True); return
        if action=="skip": r.status="skipped"; await s.commit(); await call.message.edit_reply_markup(reply_markup=None); await call.message.answer("⏭ Oziqlantirish o‘tkazib yuborildi. Ombor sarfi hisoblanmadi."); await call.answer(); return
        if action=="edit":
            await state.clear(); await state.update_data(reminder_id=rid); await state.set_state(EditReminder.amounts)
            items=json.loads(r.items_json); await call.message.answer("Haqiqiy berilgan miqdorlarni tartib bilan vergul orqali kiriting (kg).\n"+"\n".join([f"{i+1}. {x['name']} reja: {x['qty']:g} kg" for i,x in enumerate(items) if not x.get('water')])+"\nMasalan: 1.5, 3.5"); await call.answer(); return
        await complete_reminder(s,r,call)
    await call.answer()

async def complete_reminder(s,r,call,actual=None):
    items=json.loads(r.items_json)
    if actual is not None:
        j=0
        for item in items:
            if not item.get('water'):
                item['qty']=actual[j]; j+=1
    u=await s.get(__import__('app.db',fromlist=['User']).User,r.user_id)
    a=await s.get(Animal,r.animal_id)
    costs=[]; shortages=[]; low_stock=[]
    for item in items:
        if item.get('water') or item['qty']<=0: continue
        f=(await s.execute(select(FeedType).where(FeedType.user_id==r.user_id,func.lower(FeedType.name)==item['name'].lower()))).scalar_one_or_none()
        if not f:
            shortages.append(f"{item['name']}: omborda ro‘yxatdan o‘tmagan"); continue
        lots=(await s.execute(select(FeedLot).where(FeedLot.user_id==r.user_id,FeedLot.feed_type_id==f.id,FeedLot.quantity_remaining>0).order_by(FeedLot.purchased_at,FeedLot.id))).scalars().all()
        available=sum(x.quantity_remaining for x in lots)
        if available+1e-6<item['qty']:
            shortages.append(f"{item['name']}: kerak {item['qty']:g} kg, mavjud {available:g} kg"); continue
        total_value=sum(x.quantity_remaining*x.unit_price for x in lots); avg=total_value/available if available else 0
        remaining=item['qty']
        for lot in lots:
            take=min(lot.quantity_remaining,remaining); lot.quantity_remaining-=take; remaining-=take
            if remaining<=1e-6: break
        cost=item['qty']*avg
        s.add(Expense(user_id=r.user_id,animal_id=r.animal_id,category="Oziqlantirish",amount=cost,expense_date=r.scheduled_for[:10],description=f"{a.code} · {item['name']} {item['qty']:g} kg"))
        costs.append(f"{item['name']}: {item['qty']:g} kg ({cost:,.0f} so‘m)")
        remaining_stock=sum(x.quantity_remaining for x in lots)
        if remaining_stock <= f.low_stock_alert: low_stock.append(f"{f.name}: {remaining_stock:g} kg qoldi")
    if shortages:
        await s.rollback()
        await call.message.answer("⚠️ Omborda yetarli yem yo‘q yoki yem nomi topilmadi. Avval omborni to‘ldiring yoki miqdorni o‘zgartiring:\n\n"+"\n".join(shortages))
        return False
    r.status="done"; r.items_json=json.dumps(items,ensure_ascii=False); await s.commit()
    if hasattr(call,"answer"):
        await call.message.edit_reply_markup(reply_markup=None)
    await call.message.answer("✅ Oziqlantirish tasdiqlandi. Ombordan sarf chiqarildi:\n"+"\n".join(costs))
    if low_stock:
        await call.bot.send_message(u.telegram_id,"⚠️ Yem-xashak qoldig‘i kamaydi:\n"+"\n".join(low_stock))
    return True

@router.message(EditReminder.amounts)
async def reminder_edit_amounts(message:Message,state:FSMContext):
    d=await state.get_data()
    try: vals=[float(x.strip().replace(",",".")) for x in message.text.split(",")]; assert all(x>=0 for x in vals)
    except: await message.answer("Miqdorlarni vergul bilan ajrating. Masalan: 1.5, 3.5"); return
    async with Session() as s:
        u=await owner(s,message.from_user.id); r=(await s.execute(select(FeedingReminder).where(FeedingReminder.id==d['reminder_id'],FeedingReminder.user_id==u.id))).scalar_one_or_none()
        if not r or r.status!="pending": await message.answer("Eslatma topilmadi yoki oldin bajarilgan.",reply_markup=MAIN); await state.clear(); return
        count=sum(1 for x in json.loads(r.items_json) if not x.get('water'))
        if len(vals)!=count: await message.answer(f"{count} ta yem miqdorini kiriting."); return
        from types import SimpleNamespace
        ok=await complete_reminder(s,r,SimpleNamespace(message=message,bot=message.bot),vals)
    await state.clear()
    if ok: await message.answer("Miqdorlar qayta ishlash uchun qabul qilindi.",reply_markup=MAIN)
    else: await message.answer("Miqdorlar ombor bilan mos kelmadi. Eslatmadagi tugma orqali qayta urinib ko‘ring.",reply_markup=MAIN)

@router.callback_query(F.data.startswith("note:"))
async def note_start(call:CallbackQuery,state:FSMContext):
    aid=int(call.data.split(":")[1]); await state.clear(); await state.update_data(animal_id=aid); await state.set_state(AddNote.body)
    await call.message.edit_text("📝 Chorva haqidagi qaydni kiriting:",reply_markup=BACK); await call.answer()

@router.message(AddNote.body)
async def note_save(message:Message,state:FSMContext):
    d=await state.get_data()
    async with Session() as s:
        u=await owner(s,message.from_user.id); a=await get_animal(s,u.id,d['animal_id'])
        if not a: await message.answer("Chorva topilmadi.",reply_markup=MAIN); await state.clear(); return
        s.add(Note(user_id=u.id,animal_id=a.id,body=message.text)); await s.commit()
    await state.clear(); await message.answer("✅ Qayd saqlandi.",reply_markup=MAIN)

@router.callback_query(F.data.startswith("chart:"))
async def animal_chart(call:CallbackQuery):
    aid=int(call.data.split(":")[1])
    async with Session() as s:
        u=await owner(s,call.from_user.id); a=await get_animal(s,u.id,aid)
        rows=(await s.execute(select(WeightRecord).where(WeightRecord.user_id==u.id,WeightRecord.animal_id==aid).order_by(WeightRecord.recorded_at))).scalars().all()
        if not a or len(rows)<2:
            await call.message.answer("Vazn grafigi uchun kamida 2 ta o‘lchov kiriting."); await call.answer(); return
        dates=[x.recorded_at.strftime("%d.%m") for x in rows]; values=[x.weight for x in rows]
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(7,4)); ax.plot(dates,values,marker="o",linewidth=2); ax.set_title(f"{a.code} · Vazn o‘zgarishi"); ax.set_ylabel("Vazn (kg)"); ax.grid(True,alpha=.25); fig.autofmt_xdate(); fig.tight_layout()
    os.makedirs(DATA_DIR,exist_ok=True); path=os.path.join(DATA_DIR,f"weight_{call.from_user.id}_{aid}.png"); fig.savefig(path,dpi=140); plt.close(fig)
    await call.message.answer_photo(FSInputFile(path),caption=f"📈 {a.code} vazn grafigi")
    await call.answer()

@router.callback_query(F.data.startswith("history:"))
async def animal_history(call:CallbackQuery):
    aid=int(call.data.split(":")[1])
    async with Session() as s:
        u=await owner(s,call.from_user.id); a=await get_animal(s,u.id,aid)
        if not a: await call.answer("Topilmadi",show_alert=True); return
        weights=(await s.execute(select(WeightRecord).where(WeightRecord.user_id==u.id,WeightRecord.animal_id==aid).order_by(WeightRecord.recorded_at.desc()).limit(8))).scalars().all()
        notes=(await s.execute(select(Note).where(Note.user_id==u.id,Note.animal_id==aid).order_by(Note.created_at.desc()).limit(5))).scalars().all()
        expenses=(await s.execute(select(Expense).where(Expense.user_id==u.id,Expense.animal_id==aid))).scalars().all()
        incomes=(await s.execute(select(Income).where(Income.user_id==u.id,Income.animal_id==aid))).scalars().all()
        total_exp=sum(x.amount for x in expenses); total_inc=sum(x.amount for x in incomes)
        text=f"📚 <b>{a.code} tarixi</b>\n\n<b>Vazn:</b>\n"+("\n".join([f"{x.recorded_at:%Y-%m-%d}: {x.weight:g} kg" for x in weights]) or "Hali yo‘q")+f"\n\n<b>Jami xarajat:</b> {total_exp:,.0f} so‘m\n<b>Daromad:</b> {total_inc:,.0f} so‘m\n<b>Moliyaviy natija:</b> {total_inc-total_exp:,.0f} so‘m\n\n<b>Qaydlar:</b>\n"+("\n".join([f"• {x.created_at:%Y-%m-%d}: {x.body}" for x in notes]) or "Yo‘q")
        await call.message.answer(text,parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data.regexp(r"^archive:[0-9]+$"))
async def archive_options(call:CallbackQuery):
    aid=int(call.data.split(":")[1])
    from aiogram.types import InlineKeyboardMarkup,InlineKeyboardButton
    kb=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💵 Sotildi",callback_data=f"archive:sell:{aid}")],[InlineKeyboardButton(text="📦 Boshqa sabab bilan arxivlash",callback_data=f"archive:other:{aid}")],[InlineKeyboardButton(text="Bekor qilish",callback_data="archive:cancel")]])
    await call.message.answer("Chorva bilan qanday amal bajaramiz?",reply_markup=kb); await call.answer()

@router.callback_query(F.data=="archive:cancel")
async def archive_cancel(call:CallbackQuery):
    await call.message.answer("Amal bekor qilindi."); await call.answer()

@router.callback_query(F.data.startswith("archive:sell:"))
async def sell_start(call:CallbackQuery,state:FSMContext):
    aid=int(call.data.split(":")[2]); await state.clear(); await state.update_data(animal_id=aid); await state.set_state(SellAnimal.price)
    await call.message.answer("Sotilgan narxni so‘mda kiriting:",reply_markup=BACK); await call.answer()

@router.message(SellAnimal.price)
async def sell_price(message:Message,state:FSMContext):
    try: p=float(message.text.replace(" ","").replace(",",".")); assert p>=0
    except: await message.answer("Sotuv narxini raqam bilan kiriting:"); return
    await state.update_data(price=p); await state.set_state(SellAnimal.sale_date); today=date.today(); await flow_prompt(message,state,"📅 <b>Sotilgan sanani tanlang</b>",reply_markup=calendar_kb(today.year,today.month),parse_mode="HTML")

@router.message(SellAnimal.sale_date)
async def sell_date_text(message:Message,state:FSMContext):
    await flow_prompt(message,state,"📅 Sotilgan sanani kalendardan tanlang:",reply_markup=calendar_kb(date.today().year,date.today().month))

@router.callback_query(F.data.startswith("archive:other:"))
async def archive_other(call:CallbackQuery):
    aid=int(call.data.split(":")[2])
    async with Session() as s:
        u=await owner(s,call.from_user.id); a=await get_animal(s,u.id,aid)
        if not a: await call.answer("Topilmadi",show_alert=True); return
        a.status="archived"
        schedules=(await s.execute(select(FeedingSchedule).where(FeedingSchedule.user_id==u.id,FeedingSchedule.animal_id==aid))).scalars().all()
        for x in schedules: x.active=False
        await s.commit()
    await call.message.answer(f"📦 {a.code} arxivga o‘tkazildi. Oldingi tarix saqlandi.")
    await call.answer()

@router.message(F.text == "💰 Moliya")
async def finance_menu(message:Message):
    from aiogram.types import InlineKeyboardMarkup,InlineKeyboardButton
    kb=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="➖ Xarajat qo‘shish",callback_data="finance:expense")],[InlineKeyboardButton(text="➕ Daromad qo‘shish",callback_data="finance:income")],[InlineKeyboardButton(text="📊 Moliyaviy natija",callback_data="finance:summary")]])
    await message.answer("💰 <b>Moliyaviy boshqaruv</b>\nXarajat va daromadlarni boshqaring.",reply_markup=kb,parse_mode="HTML")

@router.callback_query(F.data=="finance:expense")
async def expense_start(call:CallbackQuery,state:FSMContext):
    await state.clear(); await state.set_state(AddExpense.category); await call.message.answer("Xarajat turi (masalan, Transport, Dori, Boshqa):",reply_markup=BACK); await call.answer()

@router.message(AddExpense.category)
async def expense_category(message:Message,state:FSMContext):
    await state.update_data(category=message.text.strip()); await state.set_state(AddExpense.amount); await message.answer("Summa (so‘m):")
@router.message(AddExpense.amount)
async def expense_amount(message:Message,state:FSMContext):
    try: x=float(message.text.replace(" ","").replace(",",".")); assert x>=0
    except: await message.answer("Summani raqam bilan kiriting:"); return
    await state.update_data(amount=x); await state.set_state(AddExpense.date); today=date.today(); await flow_prompt(message,state,"📅 <b>Xarajat sanasini tanlang</b>",reply_markup=calendar_kb(today.year,today.month),parse_mode="HTML")
@router.message(AddExpense.date)
async def expense_date_text(message:Message,state:FSMContext):
    await flow_prompt(message,state,"📅 Xarajat sanasini kalendardan tanlang:",reply_markup=calendar_kb(date.today().year,date.today().month))
@router.message(AddExpense.description)
async def expense_save(message:Message,state:FSMContext):
    d=await state.get_data()
    async with Session() as s:
        u=await owner(s,message.from_user.id); s.add(Expense(user_id=u.id,category=d['category'],amount=d['amount'],expense_date=d['date'],description="" if message.text.strip()=="-" else message.text.strip())); await s.commit()
    await state.clear(); await message.answer("✅ Xarajat saqlandi.",reply_markup=MAIN)

@router.callback_query(F.data=="finance:income")
async def income_start(call:CallbackQuery,state:FSMContext):
    await state.clear(); await state.set_state(AddIncome.category); await call.message.answer("Daromad turi (masalan, Sut, Chorva sotish):",reply_markup=BACK); await call.answer()
@router.message(AddIncome.category)
async def income_category(message:Message,state:FSMContext):
    await state.update_data(category=message.text.strip()); await state.set_state(AddIncome.amount); await message.answer("Summa (so‘m):")
@router.message(AddIncome.amount)
async def income_amount(message:Message,state:FSMContext):
    try: x=float(message.text.replace(" ","").replace(",",".")); assert x>=0
    except: await message.answer("Summani raqam bilan kiriting:"); return
    await state.update_data(amount=x); await state.set_state(AddIncome.date); today=date.today(); await flow_prompt(message,state,"📅 <b>Daromad sanasini tanlang</b>",reply_markup=calendar_kb(today.year,today.month),parse_mode="HTML")
@router.message(AddIncome.date)
async def income_date_text(message:Message,state:FSMContext):
    await flow_prompt(message,state,"📅 Daromad sanasini kalendardan tanlang:",reply_markup=calendar_kb(date.today().year,date.today().month))
@router.message(AddIncome.description)
async def income_save(message:Message,state:FSMContext):
    d=await state.get_data()
    async with Session() as s:
        u=await owner(s,message.from_user.id); s.add(Income(user_id=u.id,category=d['category'],amount=d['amount'],income_date=d['date'],description="" if message.text.strip()=="-" else message.text.strip())); await s.commit()
    await state.clear(); await message.answer("✅ Daromad saqlandi.",reply_markup=MAIN)

@router.callback_query(F.data=="finance:summary")
async def finance_summary(call:CallbackQuery):
    async with Session() as s:
        u=await owner(s,call.from_user.id)
        exp=(await s.execute(select(func.sum(Expense.amount)).where(Expense.user_id==u.id,Expense.category!="Oziqlantirish"))).scalar() or 0
        inc=(await s.execute(select(func.sum(Income.amount)).where(Income.user_id==u.id))).scalar() or 0
        feed=(await s.execute(select(func.sum(Expense.amount)).where(Expense.user_id==u.id,Expense.category=="Yem-xashak xaridi"))).scalar() or 0
        await call.message.answer(f"💰 <b>Moliyaviy natija</b>\n\nDaromad: {inc:,.0f} so‘m\nXarajat: {exp:,.0f} so‘m\nShundan yem: {feed:,.0f} so‘m\n\n<b>Natija: {inc-exp:,.0f} so‘m</b>",parse_mode="HTML")
    await call.answer()

@router.message(F.text == "📊 Hisobotlar")
async def reports(message:Message):
    from aiogram.types import InlineKeyboardMarkup,InlineKeyboardButton
    kb=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📈 Umumiy hisobot",callback_data="report:summary")],[InlineKeyboardButton(text="📅 Kunlik",callback_data="report:period:day"),InlineKeyboardButton(text="📆 Haftalik",callback_data="report:period:week"),InlineKeyboardButton(text="🗓 Oylik",callback_data="report:period:month")],[InlineKeyboardButton(text="🌾 Yem sarfi",callback_data="report:feed")],[InlineKeyboardButton(text="📥 Excel yuklab olish",callback_data="report:excel")],[InlineKeyboardButton(text="💾 Backup olish",callback_data="report:backup")],[InlineKeyboardButton(text="♻️ Backupdan tiklash",callback_data="report:restore")]])
    await message.answer("📊 Hisobot turini tanlang:",reply_markup=kb)

def reports_keyboard():
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Hisobotlar bo‘limi", callback_data="menu:reports")],
        [InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="nav:home")],
    ])

@router.callback_query(F.data=="report:summary")
async def report_summary(call:CallbackQuery):
    async with Session() as s:
        u=await owner(s,call.from_user.id)
        animals=(await s.execute(select(Animal).where(Animal.user_id==u.id,Animal.status=="active"))).scalars().all()
        exp=(await s.execute(select(func.sum(Expense.amount)).where(Expense.user_id==u.id,Expense.category!="Oziqlantirish"))).scalar() or 0
        inc=(await s.execute(select(func.sum(Income.amount)).where(Income.user_id==u.id))).scalar() or 0
        weights=sum(a.current_weight for a in animals)
        text=f"📊 <b>Umumiy hisobot</b>\n\n🐄 Faol chorva: {len(animals)} ta\n⚖️ Jami tirik vazn: {weights:g} kg\n💵 Daromad: {inc:,.0f} so‘m\n💸 Xarajat: {exp:,.0f} so‘m\n📈 Moliyaviy natija: {inc-exp:,.0f} so‘m"
    try:
        await call.message.edit_text(text, reply_markup=reports_keyboard(), parse_mode="HTML")
    except Exception:
        await call.message.answer(text, reply_markup=reports_keyboard(), parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data=="report:feed")
async def report_feed(call:CallbackQuery):
    from datetime import timedelta
    async with Session() as s:
        u=await owner(s,call.from_user.id); rows=(await s.execute(select(FeedType).where(FeedType.user_id==u.id))).scalars().all(); lines=[]; names=[]; quantities=[]
        for f in rows:
            lots=(await s.execute(select(FeedLot).where(FeedLot.user_id==u.id,FeedLot.feed_type_id==f.id))).scalars().all()
            qty=sum(x.quantity_remaining for x in lots); names.append(f.name); quantities.append(qty); lines.append(f"{f.name}: {qty:g} kg qoldi")
        since=(date.today()-timedelta(days=29)).isoformat()
        reminders=(await s.execute(select(FeedingReminder).where(FeedingReminder.user_id==u.id,FeedingReminder.status=="done",FeedingReminder.scheduled_for>=since))).scalars().all()
        monthly=(await s.execute(select(Expense).where(Expense.user_id==u.id,Expense.category=="Oziqlantirish",Expense.expense_date>=since))).scalars().all()
    await call.message.answer("🌾 <b>Yem-xashak hisoboti</b>\n\n<b>Ombor qoldig‘i:</b>\n"+("\n".join(lines) if lines else "Omborda yem yo‘q."),parse_mode="HTML")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    os.makedirs(DATA_DIR,exist_ok=True)
    if names:
        fig,ax=plt.subplots(figsize=(7,4)); ax.bar(names,quantities); ax.set_title("Ombordagi yem qoldig‘i"); ax.set_ylabel("Kilogramm"); ax.grid(axis="y",alpha=.25); fig.tight_layout()
        path=os.path.join(DATA_DIR,f"feed_stock_{call.from_user.id}.png"); fig.savefig(path,dpi=140); plt.close(fig)
        await call.message.answer_photo(FSInputFile(path),caption="📦 Ombordagi yem qoldig‘i")
    daily={}
    for r in reminders:
        day=r.scheduled_for[:10]; total=sum(float(x.get("qty",0)) for x in json.loads(r.items_json) if not x.get("water")); daily[day]=daily.get(day,0)+total
    if daily:
        dates_sorted=sorted(daily); vals=[daily[x] for x in dates_sorted]
        fig,ax=plt.subplots(figsize=(8,4)); ax.bar(dates_sorted,vals); ax.set_title("Oxirgi 30 kunlik yem sarfi"); ax.set_ylabel("Kg"); ax.tick_params(axis="x",rotation=60); ax.grid(axis="y",alpha=.25); fig.tight_layout()
        path=os.path.join(DATA_DIR,f"feed_usage_{call.from_user.id}.png"); fig.savefig(path,dpi=140); plt.close(fig)
        await call.message.answer_photo(FSInputFile(path),caption="📉 Tasdiqlangan oziqlantirish bo‘yicha kunlik sarf")
    if monthly:
        month_cost={}
        for x in monthly:
            m=x.expense_date[:7]; month_cost[m]=month_cost.get(m,0)+x.amount
        keys=sorted(month_cost); vals=[month_cost[x] for x in keys]
        fig,ax=plt.subplots(figsize=(7,4)); ax.bar(keys,vals); ax.set_title("Yem sarfining tannarxi"); ax.set_ylabel("So‘m"); ax.grid(axis="y",alpha=.25); fig.tight_layout()
        path=os.path.join(DATA_DIR,f"feed_cost_{call.from_user.id}.png"); fig.savefig(path,dpi=140); plt.close(fig)
        await call.message.answer_photo(FSInputFile(path),caption="💰 Oziqlantirish tannarxi")
    await call.answer()

@router.callback_query(F.data.startswith("report:period:"))
async def report_period(call:CallbackQuery):
    from datetime import timedelta
    period=call.data.split(":")[2]; today=date.today()
    if period=="day": start=today; title="Kunlik"
    elif period=="week": start=today-timedelta(days=6); title="Oxirgi 7 kun"
    else: start=today.replace(day=1); title="Oylik"
    start_s=start.isoformat(); end_s=today.isoformat()
    async with Session() as s:
        u=await owner(s,call.from_user.id)
        expenses=(await s.execute(select(Expense).where(Expense.user_id==u.id,Expense.expense_date>=start_s,Expense.expense_date<=end_s,Expense.category!="Oziqlantirish"))).scalars().all()
        incomes=(await s.execute(select(Income).where(Income.user_id==u.id,Income.income_date>=start_s,Income.income_date<=end_s))).scalars().all()
        exp=sum(x.amount for x in expenses); inc=sum(x.amount for x in incomes)
        text=f"📊 <b>{title} hisobot</b>\n📅 Davr: {start_s} – {end_s}\n\n💵 Daromad: {inc:,.0f} so‘m\n💸 Xarajat: {exp:,.0f} so‘m\n📈 Natija: {inc-exp:,.0f} so‘m"
    try:
        await call.message.edit_text(text, reply_markup=reports_keyboard(), parse_mode="HTML")
    except Exception:
        await call.message.answer(text, reply_markup=reports_keyboard(), parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data=="report:excel")
async def report_excel(call:CallbackQuery):
    from openpyxl import Workbook
    async with Session() as s:
        u=await owner(s,call.from_user.id); animals=(await s.execute(select(Animal).where(Animal.user_id==u.id))).scalars().all(); expenses=(await s.execute(select(Expense).where(Expense.user_id==u.id))).scalars().all(); incomes=(await s.execute(select(Income).where(Income.user_id==u.id))).scalars().all()
        wb=Workbook(); ws=wb.active; ws.title="Chorva"; ws.append(["ID","Turi","Zoti","Jinsi","Yosh (oy)","Vazn (kg)","Holat","Xarid narxi"])
        for a in animals: ws.append([a.code,a.kind,a.breed,a.sex,a.age_months,a.current_weight,a.status,a.purchase_price])
        we=wb.create_sheet("Xarajatlar"); we.append(["Sana","Kategoriya","Summa","Izoh"])
        for x in expenses: we.append([x.expense_date,x.category,x.amount,x.description])
        wi=wb.create_sheet("Daromadlar"); wi.append(["Sana","Kategoriya","Summa","Izoh"])
        for x in incomes: wi.append([x.income_date,x.category,x.amount,x.description])
        os.makedirs(DATA_DIR,exist_ok=True); path=os.path.join(DATA_DIR,f"chorva_hisobot_{call.from_user.id}.xlsx"); wb.save(path)
    await call.message.answer_document(FSInputFile(path),caption="CHORVA PRO Excel hisoboti")
    await call.answer()

@router.callback_query(F.data=="report:backup")
async def report_backup(call:CallbackQuery):
    from app.backup import make_user_backup
    path=await make_user_backup(call.from_user.id)
    if not path: await call.message.answer("Backup yaratish uchun avval botni ishga tushiring."); await call.answer(); return
    await call.message.answer_document(FSInputFile(path),caption="💾 CHORVA PRO zaxira nusxasi. Faylni xavfsiz joyda saqlang.")
    await call.answer()

@router.callback_query(F.data=="report:restore")
async def restore_start(call:CallbackQuery,state:FSMContext):
    await state.clear(); await state.set_state(RestoreBackup.file)
    await call.message.answer("♻️ Tiklash uchun avval CHORVA PRO yaratgan JSON backup faylini yuboring. Diqqat: tiklash hozirgi ma'lumotlaringizni backupdagi ma'lumotlar bilan almashtiradi.",reply_markup=BACK)
    await call.answer()

@router.message(RestoreBackup.file, F.document)
async def restore_file(message:Message,state:FSMContext):
    import io
    try:
        file=await message.bot.get_file(message.document.file_id)
        data=await message.bot.download_file(file.file_path)
        payload=json.loads(data.getvalue().decode("utf-8"))
        from app.backup import restore_user_backup
        await restore_user_backup(message.from_user.id,payload)
    except Exception as e:
        await message.answer(f"❌ Backup tiklanmadi: {e}",reply_markup=MAIN); await state.clear(); return
    await state.clear(); await message.answer("✅ Backup muvaffaqiyatli tiklandi.",reply_markup=MAIN)

@router.message(RestoreBackup.file)
async def restore_file_wrong(message:Message):
    await message.answer("Iltimos, JSON backup faylini hujjat sifatida yuboring.")

@router.message(F.text == "⚙️ Sozlamalar")
async def settings(message:Message):
    await message.answer("⚙️ <b>Sozlamalar</b>\n\nTil: O‘zbekcha (lotin)\nValyuta: UZS\nVazn: kg\nVaqt mintaqasi: Asia/Tashkent\n\nBackup va hisobotlar «Hisobotlar» bo‘limida.",reply_markup=MAIN,parse_mode="HTML")
