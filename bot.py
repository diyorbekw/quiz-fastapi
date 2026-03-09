import sqlite3
import logging
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, ReplyKeyboardMarkup, KeyboardButton, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot token - replace with your actual token
BOT_TOKEN = "BOT_TOKEN_HERE"

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

# Database setup
def init_db():
    conn = sqlite3.connect('quiz.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            first_name TEXT,
            last_name TEXT,
            phone_number TEXT,
            region TEXT,
            district TEXT,
            school TEXT,
            grade INTEGER
        )
    ''')
    conn.commit()
    conn.close()

# FSM States
class Registration(StatesGroup):
    first_name = State()
    last_name = State()
    phone_number = State()
    region = State()
    district = State()
    school = State()
    grade = State()

# Uzbekistan regions, districts, and schools data
UZBEKISTAN_REGIONS = {
    "tashkent": "Toshkent shahri",
    "tashkent_region": "Toshkent viloyati",
    "samarkand": "Samarqand viloyati",
    "bukhara": "Buxoro viloyati",
    "andijan": "Andijon viloyati",
    "fergana": "Farg'ona viloyati",
    "namangan": "Namangan viloyati",
    "kashkadarya": "Qashqadaryo viloyati",
    "surkhandarya": "Surxondaryo viloyati",
    "jizzakh": "Jizzax viloyati",
    "sirdarya": "Sirdaryo viloyati",
    "navoiy": "Navoiy viloyati",
    "khorezm": "Xorazm viloyati",
    "karakalpakstan": "Qoraqalpog'iston Respublikasi"
}

DISTRICTS = {
    "tashkent": ["Yunusobod", "Mirzo Ulug'bek", "Yakkasaroy", "Shayxontohur", "Olmazor", "Bektemir", "Mirobod", "Sirg'ali", "Chilonzor", "Uchtepa"],
    "tashkent_region": ["Olmaliq", "Angren", "Chirchiq", "Bekobod", "Ohangaron", "Yangiyo'l", "Nurafshon", "Zangiota", "Qibray", "Parkent"],
    "samarkand": ["Samarqand shahri", "Kattaqo'rg'on", "Urgut", "Bulung'ur", "Jomboy", "Ishtixon", "Payariq", "Pastdarg'om", "Narpay", "Oqdaryo"],
    "bukhara": ["Buxoro shahri", "Kogon", "Olot", "Gazli", "Vobkent", "Romitan", "Shofirkon", "Jondor", "Peshku", "Qorako'l"],
    "andijan": ["Andijon shahri", "Xonobod", "Asaka", "Shahrixon", "Qo'rg'ontepa", "Baliqchi", "Oltinko'l", "Jalaquduq", "Xo'jaobod", "Boz"],
    "fergana": ["Farg'ona shahri", "Marg'ilon", "Quvasoy", "Quva", "Rishton", "Bog'dod", "Oltiariq", "Beshariq", "Uchko'prik", "Dang'ara"],
    "namangan": ["Namangan shahri", "Kosonsoy", "Chust", "Uchqo'rg'on", "To'raqo'rg'on", "Pop", "Mingbuloq", "Norin", "Chortoq", "Yangiqo'rg'on"],
    "kashkadarya": ["Qarshi shahri", "Shahrisabz", "Kitob", "Muborak", "Qamashi", "G'uzor", "Dehqonobod", "Kasbi", "Nishon", "Chiroqchi"],
    "surkhandarya": ["Termiz shahri", "Denov", "Sherobod", "Sariosiyo", "Uzun", "Qumqo'rg'on", "Jarqo'rg'on", "Bandixon", "Angor", "Muzrobod"],
    "jizzakh": ["Jizzax shahri", "G'allaorol", "Do'stlik", "Forish", "Zarbdor", "Zafarobod", "Paxtakor", "Mirzacho'l", "Baxmal", "Sharof Rashidov"],
    "sirdarya": ["Guliston shahri", "Yangiyer", "Shirin", "Boyovut", "Oqoltin", "Sardoba", "Xovos", "Sayxunobod", "Guliston tumani", "Mirzaobod"],
    "navoiy": ["Navoiy shahri", "Zarafshon", "Uchquduq", "Qiziltepa", "Konimex", "Tomdi", "Xatirchi", "Nurota", "Karmana", "Navbahor"],
    "khorezm": ["Urganch shahri", "Xiva", "Xonqa", "Hazorasp", "Shovot", "Yangiariq", "Gurlan", "Bog'ot", "Qo'shko'pir", "Tuproqqal'a"],
    "karakalpakstan": ["Nukus shahri", "Xo'jayli", "Qo'ng'irot", "Chimboy", "Mo'ynoq", "Qonliko'l", "Qorao'zak", "Shumanay", "Taxtako'pir", "To'rtko'l"]
}

SCHOOLS = {}
for districts_list in DISTRICTS.values():
    for district_name in districts_list:
        SCHOOLS[district_name] = [f"{i}-maktab" for i in range(1, 31)]

# Check if user exists in database
def user_exists(user_id):
    conn = sqlite3.connect('quiz.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user is not None

# Get user data from database
def get_user_data(user_id):
    conn = sqlite3.connect('quiz.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

# Save user to database
def save_user(user_data):
    conn = sqlite3.connect('quiz.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO users 
        (user_id, first_name, last_name, phone_number, region, district, school, grade) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', user_data)
    conn.commit()
    conn.close()

# Main menu keyboard
def get_main_menu():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🧠 Test yechish", web_app=WebAppInfo(url="https://example.com/quiz"))],
            [InlineKeyboardButton(text="📊 Statistika", web_app=WebAppInfo(url="https://example.com/stats"))],
            [InlineKeyboardButton(text="🏆 Yetakchilar ro‘yxati", web_app=WebAppInfo(url="https://example.com/stats"))],
            [InlineKeyboardButton(text="✏️ Ma'lumotlarni tahrirlash", callback_data="edit_profile")]
        ]
    )
    return keyboard

def get_back_to_main_menu_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_main_menu")]
        ]
    )
    return keyboard

# Regions keyboard
def get_regions_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=region_name, callback_data=f"region_{region_code}")]
            for region_code, region_name in UZBEKISTAN_REGIONS.items()
        ]
    )
    return keyboard

# Districts keyboard
def get_districts_keyboard(region):
    districts = DISTRICTS.get(region, [])
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=district, callback_data=f"district_{district}")]
            for district in districts
        ]
    )
    return keyboard

# Schools keyboard
def get_schools_keyboard(district):
    schools = SCHOOLS.get(district, [f"{i}-maktab" for i in range(1, 31)])
    
    # Har bir qatorda 2 ta tugma bo'lishi uchun
    keyboard_buttons = []
    row = []
    for i, school in enumerate(schools, 1):
        row.append(InlineKeyboardButton(text=school, callback_data=f"school_{school}"))
        if i % 2 == 0:  # Har 2 ta tugmadan keyin yangi qator
            keyboard_buttons.append(row)
            row = []
    
    # Qolgan tugmalar (agar toq son bo'lsa)
    if row:
        keyboard_buttons.append(row)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    return keyboard

# Grades keyboard
def get_grades_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=str(grade), callback_data=f"grade_{grade}") for grade in range(1, 4)],
            [InlineKeyboardButton(text=str(grade), callback_data=f"grade_{grade}") for grade in range(4, 7)],
            [InlineKeyboardButton(text=str(grade), callback_data=f"grade_{grade}") for grade in range(7, 10)],
            [InlineKeyboardButton(text="10", callback_data="grade_10"), InlineKeyboardButton(text="11", callback_data="grade_11")]
        ]
    )
    return keyboard

# Phone number keyboard
def get_phone_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📞 Telefon raqamimni yuborish", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard

# Start command handler
@router.message(Command("start"))
async def start_handler(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    if user_exists(user_id):
        # User exists, show main menu
        await message.answer(
            "Asosiy menyu:",
            reply_markup=get_main_menu()
        )
    else:
        # Start registration process
        await message.answer("Assalomu alaykum! Botimizga xush kelibsiz.\nRo'yxatdan o'tish uchun quyidagi ma'lumotlarni kiriting.")
        await message.answer("Ismingizni kiriting:")
        await state.set_state(Registration.first_name)

# First name handler
@router.message(Registration.first_name)
async def process_first_name(message: Message, state: FSMContext):
    await state.update_data(first_name=message.text)
    await message.answer("Familiyangizni kiriting:")
    await state.set_state(Registration.last_name)

# Last name handler
@router.message(Registration.last_name)
async def process_last_name(message: Message, state: FSMContext):
    await state.update_data(last_name=message.text)
    await message.answer(
        "Telefon raqamingizni yuboring:",
        reply_markup=get_phone_keyboard()
    )
    await state.set_state(Registration.phone_number)

# Phone number handler
@router.message(Registration.phone_number, F.contact)
async def process_phone_number(message: Message, state: FSMContext):
    phone_number = message.contact.phone_number
    await state.update_data(phone_number=phone_number)
    await message.answer(
        "Viloyatingizni tanlang:",
        reply_markup=get_regions_keyboard()
    )
    await state.set_state(Registration.region)

# Region selection handler
@router.callback_query(Registration.region, F.data.startswith("region_"))
async def process_region(callback: CallbackQuery, state: FSMContext):
    region_code = callback.data.split("_")[1]
    region_name = UZBEKISTAN_REGIONS[region_code]
    await state.update_data(region=region_name)
    
    await callback.message.edit_text(
        f"Viloyat: {region_name}\nTumaningizni tanlang:",
        reply_markup=get_districts_keyboard(region_code)
    )
    await state.set_state(Registration.district)
    await callback.answer()

# District selection handler
@router.callback_query(Registration.district, F.data.startswith("district_"))
async def process_district(callback: CallbackQuery, state: FSMContext):
    district = callback.data.split("_")[1]
    await state.update_data(district=district)
    
    await callback.message.edit_text(
        f"Tuman: {district}\nMaktabingizni tanlang:",
        reply_markup=get_schools_keyboard(district)
    )
    await state.set_state(Registration.school)
    await callback.answer()

# School selection handler
@router.callback_query(Registration.school, F.data.startswith("school_"))
async def process_school(callback: CallbackQuery, state: FSMContext):
    school = callback.data.split("_")[1]
    await state.update_data(school=school)
    
    await callback.message.edit_text(
        f"Maktab: {school}\nSinfingizni tanlang:",
        reply_markup=get_grades_keyboard()
    )
    await state.set_state(Registration.grade)
    await callback.answer()

# Grade selection handler
@router.callback_query(Registration.grade, F.data.startswith("grade_"))
async def process_grade(callback: CallbackQuery, state: FSMContext):
    grade = int(callback.data.split("_")[1])
    user_data = await state.get_data()
    
    # Save user to database
    user_id = callback.from_user.id
    user_tuple = (
        user_id,
        user_data['first_name'],
        user_data['last_name'],
        user_data['phone_number'],
        user_data['region'],
        user_data['district'],
        user_data['school'],
        grade
    )
    
    save_user(user_tuple)
    
    await callback.message.edit_text(
        "✅ Ro'yxatdan muvaffaqiyatli o'tdingiz!\n\n"
        f"👤 Ism: {user_data['first_name']}\n"
        f"📋 Familiya: {user_data['last_name']}\n"
        f"📞 Telefon: {user_data['phone_number']}\n"
        f"🏙️ Viloyat: {user_data['region']}\n"
        f"📍 Tuman: {user_data['district']}\n"
        f"🏫 Maktab: {user_data['school']}\n"
        f"🎓 Sinf: {grade}"
    )
    
    await callback.message.answer(
        "Asosiy menyu:",
        reply_markup=get_main_menu()
    )
    await state.clear()
    await callback.answer()

# Edit profile handler
@router.callback_query(F.data == "edit_profile")
async def edit_profile(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.message.answer("Ma'lumotlaringizni qayta kiritish uchun quyidagi amallarni bajarishingiz kerak.\n\nIsmingizni kiriting.", reply_markup=get_back_to_main_menu_keyboard())
    await state.set_state(Registration.first_name)
    await callback.answer()

@router.callback_query(F.data == "back_to_main_menu")
async def back_to_main_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.message.answer(
        "Asosiy menyu:",
        reply_markup=get_main_menu()
    )
    await callback.answer()

# Main function
async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
