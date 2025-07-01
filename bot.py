import logging
import os
import asyncio
import asyncpg
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import uvicorn
from threading import Thread

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация
TOKEN = os.getenv('TELEGRAM_TOKEN', '7513180696:AAHEhAcGDDxgic3ITpzN_jsfxSsxsLpH0Q0')
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://user:password@localhost/dbname')
PORT = int(os.getenv('PORT', 8000))
WEBAPP_URL = os.getenv('WEBAPP_URL', 'https://your-app.railway.app')

# FastAPI приложение
app = FastAPI()

# Подключение статических файлов
app.mount("/static", StaticFiles(directory="static"), name="static")

# Вопросы для квиза
QUESTIONS = [
    {"id": 1, "question": "Что такое Python?", "answer": "язык программирования", "options": ["язык программирования", "змея", "фрукт", "игра"]},
    {"id": 2, "question": "Сколько будет 2 + 2?", "answer": "4", "options": ["3", "4", "5", "6"]},
    {"id": 3, "question": "Столица России?", "answer": "москва", "options": ["москва", "питер", "казань", "сочи"]},
    {"id": 4, "question": "Что означает HTML?", "answer": "hypertext markup language", "options": ["hypertext markup language", "home tool markup language", "hyperlinks and text markup language", "hyperlinking text markup language"]},
    {"id": 5, "question": "Какой год сейчас?", "answer": "2025", "options": ["2023", "2024", "2025", "2026"]}
]

# Инициализация базы данных
async def init_db():
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS user_progress (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                question_id INT NOT NULL,
                user_answer TEXT NOT NULL,
                is_correct BOOLEAN NOT NULL,
                answered_at TIMESTAMP DEFAULT NOW()
            )
        ''')
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS user_stats (
                user_id BIGINT PRIMARY KEY,
                total_questions INT DEFAULT 0,
                correct_answers INT DEFAULT 0,
                last_quiz_at TIMESTAMP DEFAULT NOW()
            )
        ''')
        await conn.close()
        logger.info("База данных инициализирована")
    except Exception as e:
        logger.error(f"Ошибка инициализации БД: {e}")

# API эндпоинты
@app.get("/")
async def read_root():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.get("/api/questions")
async def get_questions():
    return {"questions": QUESTIONS}

@app.post("/api/submit_answer")
async def submit_answer(request: Request):
    try:
        data = await request.json()
        user_id = data.get("user_id")
        question_id = data.get("question_id")
        user_answer = data.get("user_answer", "").lower().strip()

        if not user_id or not question_id:
            raise HTTPException(status_code=400, detail="Missing user_id or question_id")

        # Найти правильный ответ
        correct_answer = None
        for q in QUESTIONS:
            if q["id"] == question_id:
                correct_answer = q["answer"].lower().strip()
                break

        if correct_answer is None:
            raise HTTPException(status_code=400, detail="Invalid question_id")

        is_correct = user_answer == correct_answer

        # Сохранить в базу
        conn = await asyncpg.connect(DATABASE_URL)

        # Сохранить ответ
        await conn.execute(
            "INSERT INTO user_progress (user_id, question_id, user_answer, is_correct) VALUES ($1, $2, $3, $4)",
            user_id, question_id, user_answer, is_correct
        )

        # Обновить статистику
        await conn.execute('''
            INSERT INTO user_stats (user_id, total_questions, correct_answers, last_quiz_at)
            VALUES ($1, 1, $2, NOW())
            ON CONFLICT (user_id) DO UPDATE SET
                total_questions = user_stats.total_questions + 1,
                correct_answers = user_stats.correct_answers + $2,
                last_quiz_at = NOW()
        ''', user_id, 1 if is_correct else 0)

        await conn.close()

        return {
            "is_correct": is_correct,
            "correct_answer": correct_answer if not is_correct else None
        }

    except Exception as e:
        logger.error(f"Ошибка при сохранении ответа: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/user_stats/{user_id}")
async def get_user_stats(user_id: int):
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        stats = await conn.fetchrow(
            "SELECT total_questions, correct_answers FROM user_stats WHERE user_id = $1",
            user_id
        )
        await conn.close()

        if stats:
            return {
                "total_questions": stats["total_questions"],
                "correct_answers": stats["correct_answers"],
                "accuracy": round((stats["correct_answers"] / stats["total_questions"]) * 100, 1) if stats["total_questions"] > 0 else 0
            }
        else:
            return {"total_questions": 0, "correct_answers": 0, "accuracy": 0}

    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Telegram Bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    # Получить статистику пользователя
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        stats = await conn.fetchrow(
            "SELECT total_questions, correct_answers FROM user_stats WHERE user_id = $1",
            user_id
        )
        await conn.close()

        if stats and stats["total_questions"] > 0:
            accuracy = round((stats["correct_answers"] / stats["total_questions"]) * 100, 1)
            stats_text = f"\n\nТвоя статистика:\n📊 Вопросов отвечено: {stats['total_questions']}\n✅ Правильных ответов: {stats['correct_answers']}\n🎯 Точность: {accuracy}%"
        else:
            stats_text = ""

    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        stats_text = ""

    keyboard = [
        [InlineKeyboardButton("🧠 Пройти квиз", web_app=WebAppInfo(url=WEBAPP_URL))]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f'Привет, {update.effective_user.first_name}! 👋\n\n'
        f'Добро пожаловать в квиз-бот! Проверь свои знания, ответив на 5 вопросов.{stats_text}',
        reply_markup=reply_markup
    )

async def run_bot():
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    await application.run_polling()

def run_fastapi():
    uvicorn.run(app, host="0.0.0.0", port=PORT)

async def main():
    # Инициализация БД
    await init_db()

    # Запуск бота в отдельном потоке
    bot_thread = Thread(target=lambda: asyncio.run(run_bot()))
    bot_thread.daemon = True
    bot_thread.start()

    # Запуск FastAPI
    run_fastapi()

if __name__ == '__main__':
    asyncio.run(main())
