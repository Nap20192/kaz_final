import sqlite3
import datetime
import random
import asyncio

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.bot import DefaultBotProperties

# Replace with your bot token
API_TOKEN = "7694346593:AAHBoasbnvD6A3t349su8yJJLnxDgb2Uobw"

# ---------------------------
# Database Setup (SQLite)
# ---------------------------

# Connect (or create) the SQLite database
conn = sqlite3.connect("phone_time_tracker.db")
cursor = conn.cursor()

# Create the users table (if not exists)
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    full_name TEXT,
    daily_goal INTEGER DEFAULT 240
)
""")

# Create the phone_time table (if not exists)
cursor.execute("""
CREATE TABLE IF NOT EXISTS phone_time (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    date TEXT,
    hours REAL,
    timestamp TEXT
)
""")
conn.commit()

# ---------------------------
# Some Motivational Messages
# ---------------------------

MOTIVATIONAL_MESSAGES = [
    "Мысығың саған қарап отыр—онымен ойнауға уақыт тап! 🐱",
    "Экраннан басыңды көтер—мысықтар сені шынайы өмірде күтеді! 😺",
    "Сен телефонға қарағанда, мысығың саған мейіріммен қарап тұр! 🐾",
    "Мысық секілді өмір сүр—артық уайымсыз, қазіргі сәттен ләззат ал! 🐈",
    "Нағыз жылулық экранда емес, мысығыңның құшақтауында! 🤗",
    "Мысығыңның мияулауы – сенің демалысыңды сұрағаны! 🎶🐾",
    "Телефоныңды қой да, мысығыңды сипа—екеуіңе де пайдасы тиеді! 😻",
    "Мысықтар виртуалды әлемде өмір сүрмейді, олар сені қазір күтеді! 🏡🐈",
    "Бір сәтке телефонды қойып, мысығыңның көздеріне қара—олардың сүйіспеншілігі шынайы! 💕",
    "Мысықтай еркін бол—ғаламтордан емес, өмірден ләззат ал! 🌍🐾"
]


# ---------------------------
# Finite State Machine (FSM) States
# ---------------------------

class PhoneTimeStates(StatesGroup):
    waiting_for_time = State()   # Waiting for phone usage time input
    waiting_for_goal = State()   # Waiting for daily goal input

# ---------------------------
# Bot and Dispatcher Setup (Aiogram 3.x)
# ---------------------------

bot = Bot(token=API_TOKEN, session=AiohttpSession(), default=DefaultBotProperties(parse_mode="HTML"))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# ---------------------------
# Handlers
# ---------------------------

# /start and /help command
@dp.message(Command(commands=["start", "help"]))
async def cmd_start(message: types.Message) -> None:
    user_id = message.from_user.id
    username = message.from_user.username or ""
    full_name = message.from_user.full_name or ""

    # Register the user in the database (if not already present)
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?, ?, ?)",
        (user_id, username, full_name)
    )
    conn.commit()

    welcome_text = (
"📱 <b>Телефон уақыты трекер боты</b>\n\n"
"Телефон қолдану уақытыңызды бақылаңыз және интернетке тәуелділікті жеңіңіз!\n\n"
"Командалар:\n"
"/add_time - Бүгінгі телефон қолдану уақытыңызды қосу\n"
"/today - Бүгінгі қолдану уақытын көрсету\n"
"/week - Апталық статистиканы көрсету\n"
"/set_goal - Күнделікті телефон қолдану мақсатын орнату\n"
"/motivation - Мотивациялық хабарлама алу\n"
"/compare - Қолдану уақытыңызды ғаламдық ортамен салыстыру\n"
"/stats - Соңғы 10 күннің егжей-тегжейлі статистикасы"
    )
    await message.answer(welcome_text)

# /add_time command: Ask user to input today’s phone usage time in hours
@dp.message(Command(commands=["add_time"]))
async def add_time_command(message: types.Message, state: FSMContext) -> None:
    await state.set_state(PhoneTimeStates.waiting_for_time)
    await message.answer("Бүгінгі телефонды пайдалану уақытын сағатпен енгізіңіз (0-24):")

# Handler for processing the phone time input
@dp.message(PhoneTimeStates.waiting_for_time)
async def process_phone_time(message: types.Message, state: FSMContext) -> None:
    try:
        hours = float(message.text)
        if not (0 <= hours <= 24):
            raise ValueError("Жарамсыз ауқым енгізілді")
        
        user_id = message.from_user.id
        today = datetime.date.today().isoformat()
        timestamp = datetime.datetime.now().isoformat()

        # Insert the phone time record into the database
        cursor.execute(
            "INSERT INTO phone_time (user_id, date, hours, timestamp) VALUES (?, ?, ?, ?)",
            (user_id, today, hours, timestamp)
        )
        conn.commit()

        # Retrieve user's daily goal in hours
        cursor.execute("SELECT daily_goal FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        daily_goal = result[0] / 60 if result else 4 

        if hours > daily_goal:
            reply_text = f"⚠️ Күнделікті {daily_goal} сағат мақсатыңыздан асып кеттіңіз. Үзіліс жасап көріңіз!"
        else:
            remaining = daily_goal - hours
            reply_text = f"✅ Деректер сақталды! Күнделікті мақсатыңызға жету үшін әлі {daily_goal} сағатыңыз бар."

        await message.answer(reply_text)
        await state.clear()
    except ValueError:
        await message.answer("❌ 0 мен 24 арасындағы жарамды санды енгізіңіз.")

# /today command: Show today's total phone usage time in hours
@dp.message(Command(commands=["today"]))
async def today_usage(message: types.Message) -> None:
    user_id = message.from_user.id
    today = datetime.date.today().isoformat()

    cursor.execute(
        "SELECT SUM(hours) FROM phone_time WHERE user_id = ? AND date = ?",
        (user_id, today)
    )
    total_hours = cursor.fetchone()[0] or 0
    await message.answer(f"📊 Бүгінгі телефонды пайдалану: {total_hours} сағат.")

# /week command: Show phone usage statistics for the last 7 days in hours
@dp.message(Command(commands=["week"]))
async def week_usage(message: types.Message) -> None:
    user_id = message.from_user.id
    today = datetime.date.today()
    start_date = today - datetime.timedelta(days=6)  # Last 7 days including today

    cursor.execute("""
        SELECT date, SUM(hours)
        FROM phone_time
        WHERE user_id = ? AND date BETWEEN ? AND ?
        GROUP BY date
        ORDER BY date ASC
    """, (user_id, start_date.isoformat(), today.isoformat()))
    rows = cursor.fetchall()

    if rows:
        reply_lines = ["📆 <b>Апталық телефонды пайдалану:</b>"]
        total = 0
        for rec_date, hours in rows:
            reply_lines.append(f"{rec_date}: {hours} сағат")
            total += hours
        reply_lines.append(f"\nБарлығы: {total} сағат")
        avg = total / 7
        reply_lines.append(f"Күніне орташа: {avg:.2f} сағат")
        await message.answer("\n".join(reply_lines))
    else:
        await message.answer("Өткен аптаға деректер табылмады.")

# /set_goal command: Allow user to set a daily phone usage goal in hours
@dp.message(Command(commands=["set_goal"]))
async def set_goal_command(message: types.Message, state: FSMContext) -> None:
    await state.set_state(PhoneTimeStates.waiting_for_goal)
    await message.answer("Телефонды күнделікті пайдалану мақсатын сағатпен енгізіңіз (0,5 пен 24 арасында):")

# Handler for processing the daily goal input
@dp.message(PhoneTimeStates.waiting_for_goal)
async def process_set_goal(message: types.Message, state: FSMContext) -> None:
    try:
        goal = float(message.text)
        if not (0.5 <= goal <= 24):
            raise ValueError("Мақсат жарамды ауқымнан тыс")
        
        user_id = message.from_user.id
        cursor.execute(
            "UPDATE users SET daily_goal = ? WHERE user_id = ?",
            (goal * 60, user_id)  # Convert hours to minutes for storage
        )
        conn.commit()
        await message.answer(f"🎯 Телефонды күнделікті пайдалану мақсатыңыз {goal} сағатқа белгіленген!")
        await state.clear()
    except ValueError:
        await message.answer("❌ 0.5 пен 24 арасындағы жарамды санды енгізіңіз.")

# /motivation command: Send a random motivational message
@dp.message(Command(commands=["motivation"]))
async def send_motivation(message: types.Message) -> None:
    msg = random.choice(MOTIVATIONAL_MESSAGES)
    await message.answer(f"💡 {msg}")

# /compare command: Compare user's average usage with global average in hours
@dp.message(Command(commands=["compare"]))
async def compare_usage(message: types.Message) -> None:
    user_id = message.from_user.id
    # Global average phone usage (across all users)
    cursor.execute("SELECT AVG(hours) FROM phone_time")
    global_avg = 3.75

    # User's average phone usage
    cursor.execute("SELECT AVG(hours) FROM phone_time WHERE user_id = ?", (user_id,))
    user_avg = cursor.fetchone()[0] or 0

    if user_avg < global_avg:
        comparison = "Аздау"
    elif user_avg > global_avg:
        comparison = "көбірек"
    else:
        comparison = "тең"

    reply_text = (
        f"🌍 Жаһандық орташа телефонды пайдалану: күніне {global_avg:.2f} сағат\n"
        f"📊 Орташа телефонды пайдалану: күніне {user_avg:.2f} сағат\n"
        f"Сіз әлемдік орташа көрсеткіштен {comparison}сыз."
    )
    await message.answer(reply_text)

# /stats command: Show detailed statistics (last 10 days) in hours
@dp.message(Command(commands=["stats"]))
async def detailed_stats(message: types.Message) -> None:
    user_id = message.from_user.id
    cursor.execute("""
        SELECT date, SUM(hours) AS total_hours
        FROM phone_time
        WHERE user_id = ?
        GROUP BY date
        ORDER BY date DESC
        LIMIT 10
    """, (user_id,))
    rows = cursor.fetchall()

    if rows:
        reply_lines = ["📈 <b>Соңғы 10 күндегі пайдалануыңыз:</b>"]
        for rec_date, total_hours in rows:
            reply_lines.append(f"{rec_date}: {total_hours} сағат")
        await message.answer("\n".join(reply_lines))
    else:
        await message.answer("Қолдану деректері әлі жоқ.")

# ---------------------------
# Main entry point
# ---------------------------

async def main():
    print("Bot is starting...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
