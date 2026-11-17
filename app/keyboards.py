from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from app.config import WEBAPP_URL
from aiogram.utils.keyboard import InlineKeyboardBuilder

MAIN = InlineKeyboardMarkup(inline_keyboard=(([ [InlineKeyboardButton(text="🌿 CHORVA PRO ilovasini ochish", web_app=WebAppInfo(url=WEBAPP_URL))] ] if WEBAPP_URL else []) + [
    [InlineKeyboardButton(text="🐄 Chorvalarim", callback_data="menu:animals"), InlineKeyboardButton(text="➕ Chorva qo‘shish", callback_data="menu:add_animal")],
    [InlineKeyboardButton(text="🌾 Yem-xashak", callback_data="menu:feed"), InlineKeyboardButton(text="⏰ Oziqlantirish", callback_data="menu:schedule")],
    [InlineKeyboardButton(text="⚖️ Vazn nazorati", callback_data="menu:weight"), InlineKeyboardButton(text="💰 Moliya", callback_data="menu:finance")],
    [InlineKeyboardButton(text="📊 Hisobotlar", callback_data="menu:reports"), InlineKeyboardButton(text="⚙️ Sozlamalar", callback_data="menu:settings")],
]))

BACK = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Orqaga", callback_data="nav:back"), InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="nav:home")]])

ID_MODE = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="✨ Avtomatik ID", callback_data="animalid:auto")],
    [InlineKeyboardButton(text="✍️ ID ni qo‘lda kiritish", callback_data="animalid:manual")],
    [InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="nav:home")],
])

KIND_KB = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🐄 Sigir · urg‘ochi", callback_data="kind:sigir"), InlineKeyboardButton(text="🐂 Buqa · erkak", callback_data="kind:buqa")],
    [InlineKeyboardButton(text="🐏 Qo‘chqor · erkak", callback_data="kind:qochqor"), InlineKeyboardButton(text="🐑 Sovliq · urg‘ochi", callback_data="kind:sovliq")],
])

UNKNOWN = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❔ Bilmayman", callback_data="skip:unknown")], [InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="nav:home")]])
SKIP = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⏭ O‘tkazib yuborish", callback_data="skip:field")], [InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="nav:home")]])


def animals_kb(rows, prefix="animal"):
    b = InlineKeyboardBuilder()
    for a in rows:
        emoji = {"Sigir": "🐄", "Buqa": "🐂", "Qo‘y": "🐑", "Qo‘chqor": "🐏", "Sovliq": "🐑"}.get(a.kind, "🐾")
        b.button(text=f"{emoji} {a.code} · {a.kind}", callback_data=f"{prefix}:{a.id}")
    b.adjust(2)
    b.row(InlineKeyboardButton(text="🔎 Qidirish", callback_data="animals:search"), InlineKeyboardButton(text="🗃 Arxiv", callback_data="animals:archive"))
    b.row(InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="nav:home"))
    return b.as_markup()


def reminder_kb(reminder_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Bajarildi", callback_data=f"rem:done:{reminder_id}")],
        [InlineKeyboardButton(text="✏️ Miqdorni o‘zgartirish", callback_data=f"rem:edit:{reminder_id}")],
        [InlineKeyboardButton(text="⏭ O‘tkazib yuborish", callback_data=f"rem:skip:{reminder_id}")],
    ])


def animal_profile_kb(animal_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Profilni tahrirlash", callback_data=f"editmenu:{animal_id}")],
        [InlineKeyboardButton(text="📸 Rasm qo‘shish / almashtirish", callback_data=f"animalphoto:{animal_id}")],
        [InlineKeyboardButton(text="🖼 Rasmni ko‘rish", callback_data=f"animalphoto:view:{animal_id}")],
        [InlineKeyboardButton(text="⚖️ Vazn kiritish", callback_data=f"weight:{animal_id}"), InlineKeyboardButton(text="📈 Vazn grafigi", callback_data=f"chart:{animal_id}")],
        [InlineKeyboardButton(text="🌾 Oziqlantirish jadvali", callback_data=f"schedule:{animal_id}")],
        [InlineKeyboardButton(text="📝 Qayd qo‘shish", callback_data=f"note:{animal_id}"), InlineKeyboardButton(text="📚 Tarix", callback_data=f"history:{animal_id}")],
        [InlineKeyboardButton(text="📦 Sotish / Arxiv", callback_data=f"archive:{animal_id}")],
        [InlineKeyboardButton(text="⬅️ Chorvalar ro‘yxati", callback_data="menu:animals"), InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="nav:home")],
    ])


def calendar_kb(year, month, allow_unknown=False):
    import calendar
    from datetime import date
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    cal = calendar.Calendar(firstweekday=0)
    months=["Yanvar","Fevral","Mart","Aprel","May","Iyun","Iyul","Avgust","Sentabr","Oktabr","Noyabr","Dekabr"]
    rows = [[InlineKeyboardButton(text=f"📅 {months[month-1]} {year}", callback_data="cal:noop")]]
    rows.append([InlineKeyboardButton(text=x, callback_data="cal:noop") for x in ["Du", "Se", "Ch", "Pa", "Ju", "Sh", "Ya"]])
    for week in cal.monthdayscalendar(year, month):
        row=[]
        for day in week:
            row.append(InlineKeyboardButton(text=(str(day) if day else "·"), callback_data=(f"cal:day:{year:04d}-{month:02d}-{day:02d}" if day else "cal:noop")))
        rows.append(row)
    prev_y, prev_m = (year-1,12) if month==1 else (year,month-1)
    next_y, next_m = (year+1,1) if month==12 else (year,month+1)
    rows.append([InlineKeyboardButton(text="◀️", callback_data=f"cal:month:{prev_y}-{prev_m:02d}"), InlineKeyboardButton(text="Bugun", callback_data="cal:today"), InlineKeyboardButton(text="▶️", callback_data=f"cal:month:{next_y}-{next_m:02d}")])
    rows.append([InlineKeyboardButton(text="⏪ Kecha", callback_data="cal:yesterday")])
    if allow_unknown:
        rows.append([InlineKeyboardButton(text="❔ Bilmayman", callback_data="cal:unknown")])
    rows.append([InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="nav:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def schedule_times_kb(selected):
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    presets=["06:00","07:00","08:00","09:00","10:00","11:00","12:00","13:00","14:00","15:00","16:00","17:00","18:00","19:00","20:00","21:00"]
    rows=[]
    for i in range(0,len(presets),4):
        rows.append([InlineKeyboardButton(text=("✅ " if t in selected else "▫️ ")+t,callback_data=f"stime:toggle:{t}") for t in presets[i:i+4]])
    rows.append([InlineKeyboardButton(text="➕ Boshqa vaqtni kiritish",callback_data="stime:custom")])
    rows.append([InlineKeyboardButton(text="✅ Vaqtlarni tasdiqlash",callback_data="stime:done")])
    rows.append([InlineKeyboardButton(text="🏠 Bosh menyu",callback_data="nav:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
