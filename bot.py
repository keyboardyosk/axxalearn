import os
import logging
from datetime import datetime, timedelta, time
from calendar import monthrange, weekday
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from aiogram.enums import ChatAction
from aiogram.filters import Command
import asyncpg
from dotenv import load_dotenv
import asyncio
import sys
import random

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Загрузка конфигурации
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://axxalearn.up.railway.app")

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Подключение к базе данных
async def get_db_connection():
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        return conn
    except Exception as e:
        logger.error(f"Ошибка подключения к БД: {e}")
        raise

# Инициализация базы данных
async def init_db():
    conn = await get_db_connection()
    try:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id BIGINT PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                role TEXT DEFAULT 'student',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(telegram_id),
                subject TEXT NOT NULL,
                booking_date DATE NOT NULL,
                booking_time TIME NOT NULL,
                phone TEXT,
                status TEXT DEFAULT 'confirmed',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS quiz_progress (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(telegram_id),
                subject TEXT NOT NULL,
                score INTEGER DEFAULT 0,
                total_questions INTEGER DEFAULT 0,
                completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS schedule (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(telegram_id),
                subject TEXT NOT NULL,
                lesson_date DATE NOT NULL,
                lesson_time TIME NOT NULL,
                status TEXT DEFAULT 'scheduled',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        logger.info("База данных инициализирована")
    except Exception as e:
        logger.error(f"Ошибка инициализации БД: {e}")
        raise
    finally:
        await conn.close()

# FSM состояния
class BookingState(StatesGroup):
    waiting_for_subject = State()
    waiting_for_date = State()
    waiting_for_time = State()
    waiting_for_phone = State()
    waiting_for_confirmation = State()

# Функция для создания календаря с фильтрацией по дням недели
def build_subject_calendar(current_date, subject):
    today = datetime.now()
    year = current_date.year
    month = current_date.month
    month_name = current_date.strftime("%B")
    days_in_month = monthrange(year, month)[1]
    first_day = weekday(year, month, 1)
    calendar = []

    # Определяем нужный день недели
    if subject == "science":
        allowed_weekday = 2  # среда (0=понедельник)
        subject_name = "Наука"
    elif subject == "programming":
        allowed_weekday = 4  # пятница
        subject_name = "Программирование"
    else:
        allowed_weekday = None
        subject_name = "Предмет"

    # Навигация по месяцам
    prev_month = current_date - timedelta(days=30)
    next_month = current_date + timedelta(days=30)

    if current_date <= today.replace(day=1, hour=0, minute=0, second=0, microsecond=0):
        prev_button = InlineKeyboardButton(text="◀️", callback_data="ignore")
    else:
        prev_button = InlineKeyboardButton(text="◀️", callback_data=f"prev_{subject}_{prev_month.year}_{prev_month.month}")

    header = [
        InlineKeyboardButton(text=f"{subject_name}", callback_data="ignore"),
        InlineKeyboardButton(text=f"{month_name} {year}", callback_data="ignore"),
        prev_button,
        InlineKeyboardButton(text="▶️", callback_data=f"next_{subject}_{next_month.year}_{next_month.month}")
    ]
    calendar.append(header)

    # Дни недели
    days_of_week = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    calendar.append([InlineKeyboardButton(text=day, callback_data="ignore") for day in days_of_week])

    # Дни месяца
    week = []
    for _ in range(first_day):
        week.append(InlineKeyboardButton(text=" ", callback_data="ignore"))

    for day in range(1, days_in_month + 1):
        current_day = datetime(year, month, day)

        # Проверяем: день в прошлом или не тот день недели
        if current_day < today or (allowed_weekday is not None and current_day.weekday() != allowed_weekday):
            week.append(InlineKeyboardButton(text="·", callback_data="ignore"))
        else:
            week.append(InlineKeyboardButton(text=str(day), callback_data=f"date_{subject}_{year}_{month}_{day}"))

        if (first_day + day - 1) % 7 == 6:  # Конец недели
            calendar.append(week)
            week = []

    if week:
        while len(week) < 7:
            week.append(InlineKeyboardButton(text=" ", callback_data="ignore"))
        calendar.append(week)

    return InlineKeyboardMarkup(inline_keyboard=calendar)

# Основное меню
def get_main_menu():
    keyboard = [
        [InlineKeyboardButton(text="📚 Пройти домашку", web_app=WebAppInfo(url=f"{WEBAPP_URL}/quiz"))],
        [InlineKeyboardButton(text="📅 Записаться на занятие", callback_data="book_lesson")],
        [InlineKeyboardButton(text="📊 Мой прогресс", web_app=WebAppInfo(url=f"{WEBAPP_URL}/progress"))],
        [InlineKeyboardButton(text="🗓 Моё расписание", web_app=WebAppInfo(url=f"{WEBAPP_URL}/schedule"))],
        [InlineKeyboardButton(text="🎯 Секретный раздел", web_app=WebAppInfo(url=f"{WEBAPP_URL}/secret"))]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Меню выбора предмета для записи
def get_subject_menu():
    keyboard = [
        [InlineKeyboardButton(text="🧪 Наука (среда)", callback_data="subject_science")],
        [InlineKeyboardButton(text="💻 Программирование (пятница)", callback_data="subject_programming")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Меню выбора времени
def get_time_menu(subject):
    times = ["16:00", "17:00", "18:00", "19:00", "20:00"]
    keyboard = []
    for time_slot in times:
        keyboard.append([InlineKeyboardButton(text=f"🕐 {time_slot}", callback_data=f"time_{subject}_{time_slot}")])
    keyboard.append([InlineKeyboardButton(text="◀️ Назад к календарю", callback_data=f"back_to_calendar_{subject}")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Команда /start
@dp.message(Command("start"))
async def start_command(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.full_name

    await state.clear()

    # Сохраняем пользователя в БД
    conn = await get_db_connection()
    try:
        await conn.execute(
            "INSERT INTO users (telegram_id, username, full_name) VALUES ($1, $2, $3) ON CONFLICT (telegram_id) DO UPDATE SET username = $2, full_name = $3",
            user_id, username, full_name
        )
        logger.info(f"Пользователь {user_id} ({username}) сохранён в БД")
    finally:
        await conn.close()

    welcome_text = f"""
🎓 Привет, {full_name}! 

Добро пожаловать в твой персональный образовательный помощник! 

Здесь ты можешь:
• Проходить домашние задания в виде квизов
• Записываться на занятия
• Отслеживать свой прогресс
• Смотреть расписание
• Открыть секретный раздел 🎯

Выбери, что хочешь сделать:
    """

    await message.answer(welcome_text, reply_markup=get_main_menu())

# Обработка записи на занятие
@dp.callback_query(lambda c: c.data == "book_lesson")
async def book_lesson_start(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.edit_text(
    "📅 Выбери предмет для записи:\n"
    "🧪 Наука — по средам\n"
    "💻 Программирование — по пятницам",
    reply_markup=get_subject_menu()
)
    await state.set_state(BookingState.waiting_for_subject)
    await callback_query.answer()

# Выбор предмета
@dp.callback_query(lambda c: c.data.startswith("subject_"))
async def select_subject(callback_query: types.CallbackQuery, state: FSMContext):
    subject = callback_query.data.split("_")[1]  # science или programming
    await state.update_data(subject=subject)

    subject_names = {"science": "Наука", "programming": "Программирование"}
    subject_days = {"science": "среды", "programming": "пятницы"}

    current_date = datetime.now()
    calendar_markup = build_subject_calendar(current_date, subject)

    await callback_query.message.edit_text(
        f"📅 Выбери дату для занятия по предмету {subject_names[subject]}
"
        f"Доступны только {subject_days[subject]}:",
        reply_markup=calendar_markup
    )
    await state.set_state(BookingState.waiting_for_date)
    await callback_query.answer()

# Навигация по календарю
@dp.callback_query(lambda c: c.data.startswith("prev_") or c.data.startswith("next_"))
async def navigate_calendar(callback_query: types.CallbackQuery, state: FSMContext):
    data_parts = callback_query.data.split("_")
    direction = data_parts[0]  # prev или next
    subject = data_parts[1]
    year = int(data_parts[2])
    month = int(data_parts[3])

    current_date = datetime(year, month, 1)
    calendar_markup = build_subject_calendar(current_date, subject)

    subject_names = {"science": "Наука", "programming": "Программирование"}
    subject_days = {"science": "среды", "programming": "пятницы"}

    await callback_query.message.edit_reply_markup(reply_markup=calendar_markup)
    await callback_query.answer()

# Выбор даты
@dp.callback_query(lambda c: c.data.startswith("date_"))
async def select_date(callback_query: types.CallbackQuery, state: FSMContext):
    data_parts = callback_query.data.split("_")
    subject = data_parts[1]
    year = int(data_parts[2])
    month = int(data_parts[3])
    day = int(data_parts[4])

    selected_date = datetime(year, month, day)
    await state.update_data(booking_date=selected_date)

    subject_names = {"science": "Наука", "programming": "Программирование"}

    await callback_query.message.edit_text(
        f"🕐 Выбери время для занятия по предмету {subject_names[subject]}
"
        f"📅 Дата: {selected_date.strftime('%d.%m.%Y')} ({selected_date.strftime('%A')})",
        reply_markup=get_time_menu(subject)
    )
    await state.set_state(BookingState.waiting_for_time)
    await callback_query.answer()

# Выбор времени
@dp.callback_query(lambda c: c.data.startswith("time_"))
async def select_time(callback_query: types.CallbackQuery, state: FSMContext):
    data_parts = callback_query.data.split("_")
    subject = data_parts[1]
    selected_time = data_parts[2]

    await state.update_data(booking_time=selected_time)

    # Запрашиваем номер телефона
    phone_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Поделиться номером", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await callback_query.message.answer(
        "📱 Поделись номером телефона для подтверждения записи:",
        reply_markup=phone_keyboard
    )
    await state.set_state(BookingState.waiting_for_phone)
    await callback_query.answer()

# Получение номера телефона
@dp.message(BookingState.waiting_for_phone)
async def get_phone(message: types.Message, state: FSMContext):
    phone = None

    if message.contact:
        phone = message.contact.phone_number
    elif message.text and message.text.replace("+", "").replace(" ", "").replace("-", "").isdigit():
        phone = message.text
    else:
        await message.answer("❌ Пожалуйста, поделись номером телефона или введи корректный номер")
        return

    await state.update_data(phone=phone)

    # Показываем подтверждение
    data = await state.get_data()
    subject = data["subject"]
    booking_date = data["booking_date"]
    booking_time = data["booking_time"]

    subject_names = {"science": "Наука", "programming": "Программирование"}

    confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить запись", callback_data="confirm_booking")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_booking")]
    ])

    confirmation_text = f"""
📋 Подтверди запись:

👤 Имя: {message.from_user.full_name}
📚 Предмет: {subject_names[subject]}
📅 Дата: {booking_date.strftime('%d.%m.%Y')} ({booking_date.strftime('%A')})
🕐 Время: {booking_time}
📱 Телефон: {phone}

Всё верно?
    """

    await message.answer(
        confirmation_text,
        reply_markup=confirm_keyboard,
        reply_keyboard_remove=True
    )
    await state.set_state(BookingState.waiting_for_confirmation)

# Подтверждение записи
@dp.callback_query(lambda c: c.data == "confirm_booking")
async def confirm_booking(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    data = await state.get_data()

    subject = data["subject"]
    booking_date = data["booking_date"]
    booking_time = data["booking_time"]
    phone = data["phone"]

    # Сохраняем в БД
    conn = await get_db_connection()
    try:
        await conn.execute(
            "INSERT INTO bookings (user_id, subject, booking_date, booking_time, phone) VALUES ($1, $2, $3, $4, $5)",
            user_id, subject, booking_date.date(), time.fromisoformat(booking_time), phone
        )
        logger.info(f"Запись создана: {user_id} - {subject} - {booking_date} - {booking_time}")
    finally:
        await conn.close()

    subject_names = {"science": "Наука", "programming": "Программирование"}

    success_text = f"""
✅ Запись подтверждена!

📚 {subject_names[subject]}
📅 {booking_date.strftime('%d.%m.%Y')} в {booking_time}

Мы отправим напоминание за день до занятия.
Увидимся на уроке! 🎓
    """

    await callback_query.message.edit_text(success_text, reply_markup=get_main_menu())
    await state.clear()
    await callback_query.answer("Запись успешно создана! ✅")

# Отмена записи
@dp.callback_query(lambda c: c.data == "cancel_booking")
async def cancel_booking(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.edit_text(
        "❌ Запись отменена.

Можешь записаться в любое время!",
        reply_markup=get_main_menu()
    )
    await state.clear()
    await callback_query.answer("Запись отменена")

# Возврат в главное меню
@dp.callback_query(lambda c: c.data == "back_to_main")
async def back_to_main(callback_query: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback_query.message.edit_text(
        "🎓 Главное меню

Выбери, что хочешь сделать:",
        reply_markup=get_main_menu()
    )
    await callback_query.answer()

# Возврат к календарю
@dp.callback_query(lambda c: c.data.startswith("back_to_calendar_"))
async def back_to_calendar(callback_query: types.CallbackQuery, state: FSMContext):
    subject = callback_query.data.split("_")[3]

    current_date = datetime.now()
    calendar_markup = build_subject_calendar(current_date, subject)

    subject_names = {"science": "Наука", "programming": "Программирование"}
    subject_days = {"science": "среды", "programming": "пятницы"}

    await callback_query.message.edit_text(
        f"📅 Выбери дату для занятия по предмету {subject_names[subject]}
"
        f"Доступны только {subject_days[subject]}:",
        reply_markup=calendar_markup
    )
    await state.set_state(BookingState.waiting_for_date)
    await callback_query.answer()

# Игнорирование пустых кнопок
@dp.callback_query(lambda c: c.data == "ignore")
async def ignore_callback(callback_query: types.CallbackQuery):
    await callback_query.answer()

# Обработка текстовых сообщений (возврат в меню)
@dp.message()
async def handle_text(message: types.Message, state: FSMContext):
    current_state = await state.get_state()

    # Если пользователь не в процессе записи, показываем главное меню
    if current_state is None:
        await message.answer(
            "🎓 Главное меню

Выбери, что хочешь сделать:",
            reply_markup=get_main_menu()
        )

# Запуск бота
async def main():
    logger.info("Запуск образовательного бота...")
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
