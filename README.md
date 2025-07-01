# 🧠 Telegram Quiz Mini App

Мини-приложение для Telegram с квизом и базой данных PostgreSQL.

## 🚀 Деплой на Railway

### 1. Подготовка репозитория

1. Создай новый репозиторий на GitHub
2. Загрузи все файлы из этого проекта
3. Убедись, что структура выглядит так:

```
├── bot.py
├── requirements.txt
├── Procfile
├── .gitignore
├── README.md
└── static/
    ├── index.html
    ├── script.js
    └── style.css
```

### 2. Настройка Railway

1. Зайди на [railway.app](https://railway.app)
2. Подключи свой GitHub аккаунт
3. Создай новый проект → "Deploy from GitHub repo"
4. Выбери свой репозиторий

### 3. Добавление PostgreSQL

1. В проекте Railway нажми "New Service"
2. Выбери "Database" → "PostgreSQL"
3. Дождись создания базы данных

### 4. Настройка переменных окружения

В разделе "Variables" добавь:

```
TELEGRAM_TOKEN=твой_токен_бота
DATABASE_URL=postgresql://... (автоматически появится после создания БД)
WEBAPP_URL=https://твой-проект.railway.app
```

### 5. Получение URL приложения

1. После деплоя Railway покажет URL твоего приложения
2. Скопируй его и обнови переменную `WEBAPP_URL`
3. Также обнови URL в коде бота, если нужно

## 🔧 Локальная разработка

### Установка зависимостей

```bash
pip install -r requirements.txt
```

### Настройка переменных окружения

Создай файл `.env`:

```
TELEGRAM_TOKEN=твой_токен_бота
DATABASE_URL=postgresql://user:password@localhost/dbname
WEBAPP_URL=http://localhost:8000
```

### Запуск

```bash
python bot.py
```

## 📊 Функции

- ✅ 5 вопросов с вариантами ответов
- ✅ Сохранение прогресса в PostgreSQL
- ✅ Статистика пользователя
- ✅ Красивый интерфейс с анимациями
- ✅ Адаптивный дизайн
- ✅ Поддержка темной темы

## 🛠 Технологии

- **Backend**: Python, FastAPI, python-telegram-bot
- **Database**: PostgreSQL
- **Frontend**: HTML, CSS, JavaScript
- **Deploy**: Railway

## 📝 API Endpoints

- `GET /` - Главная страница с квизом
- `GET /api/questions` - Получение списка вопросов
- `POST /api/submit_answer` - Отправка ответа
- `GET /api/user_stats/{user_id}` - Статистика пользователя

## 🎯 Структура базы данных

### user_progress
- `id` - ID записи
- `user_id` - ID пользователя Telegram
- `question_id` - ID вопроса
- `user_answer` - Ответ пользователя
- `is_correct` - Правильность ответа
- `answered_at` - Время ответа

### user_stats
- `user_id` - ID пользователя (PRIMARY KEY)
- `total_questions` - Общее количество отвеченных вопросов
- `correct_answers` - Количество правильных ответов
- `last_quiz_at` - Время последнего прохождения квиза

## 🔄 Обновление вопросов

Чтобы добавить новые вопросы, отредактируй массив `QUESTIONS` в файле `bot.py`:

```python
QUESTIONS = [
    {
        "id": 1,
        "question": "Твой вопрос?",
        "answer": "правильный ответ",
        "options": ["вариант 1", "вариант 2", "вариант 3", "вариант 4"]
    },
    # ... другие вопросы
]
```

## 🐛 Отладка

### Проверка логов Railway
1. Зайди в свой проект на Railway
2. Открой вкладку "Deployments"
3. Кликни на последний деплой
4. Посмотри логи в разделе "Build Logs" и "Deploy Logs"

### Частые проблемы
- **Бот не отвечает**: Проверь `TELEGRAM_TOKEN`
- **Ошибка БД**: Проверь `DATABASE_URL`
- **WebApp не открывается**: Проверь `WEBAPP_URL`

## 📞 Поддержка

Если что-то не работает:
1. Проверь переменные окружения
2. Посмотри логи в Railway
3. Убедись, что все файлы загружены в репозиторий
