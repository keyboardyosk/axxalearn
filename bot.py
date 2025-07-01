import logging
import nest_asyncio
import asyncio  # Импортируем asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Включаем логирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен API вашего бота
TOKEN = '7513180696:AAHEhAcGDDxgic3ITpzN_jsfxSsxsLpH0Q0'

# Функция для обработки команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    web_app_url = "https://keyboardyosk.github.io/axxalearn"  # Замените на корректный URL твоего веб-приложения
    keyboard = [
        [InlineKeyboardButton("Open Quiz Mini App", web_app=WebAppInfo(url=web_app_url))]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Welcome to the Quiz Bot! Press the button to open the mini app.', reply_markup=reply_markup)

async def main() -> None:
    # Создаем ApplicationBuilder и передаем ему токен API бота
    application = ApplicationBuilder().token(TOKEN).build()

    # Регистрируем обработчики
    application.add_handler(CommandHandler("start", start))

    # Запускаем бота
    await application.run_polling()

if __name__ == '__main__':
    nest_asyncio.apply()
    asyncio.run(main())
