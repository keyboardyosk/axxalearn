const tg = window.Telegram.WebApp;

// Инициализация Telegram WebApp
tg.expand();
tg.ready();

// Получение данных пользователя
const user = tg.initDataUnsafe?.user;
const userId = user?.id || 12345; // Fallback для тестирования

let questions = [];
let currentQuestionIndex = 0;
let correctAnswers = 0;
let userAnswers = [];

// Загрузка вопросов с сервера
async function loadQuestions() {
    try {
        const response = await fetch('/api/questions');
        const data = await response.json();
        questions = data.questions;
        loadQuestion();
    } catch (error) {
        console.error('Ошибка загрузки вопросов:', error);
        document.getElementById('question').textContent = 'Ошибка загрузки вопросов';
    }
}

// Отображение текущего вопроса
function loadQuestion() {
    if (currentQuestionIndex >= questions.length) {
        showFinalResult();
        return;
    }

    const question = questions[currentQuestionIndex];

    // Обновление прогресса
    updateProgress();

    // Отображение вопроса
    document.getElementById('question').textContent = question.question;

    // Создание вариантов ответов
    const optionsContainer = document.getElementById('options-container');
    optionsContainer.innerHTML = '';

    question.options.forEach((option, index) => {
        const button = document.createElement('button');
        button.className = 'option-button';
        button.textContent = option;
        button.onclick = () => selectAnswer(option, button);
        optionsContainer.appendChild(button);
    });

    // Скрытие результата предыдущего вопроса
    document.getElementById('result-container').style.display = 'none';
}

// Обновление прогресс-бара
function updateProgress() {
    const progress = ((currentQuestionIndex + 1) / questions.length) * 100;
    document.getElementById('progress-fill').style.width = progress + '%';
    document.getElementById('current-question').textContent = currentQuestionIndex + 1;
    document.getElementById('total-questions').textContent = questions.length;
}

// Выбор ответа
async function selectAnswer(selectedAnswer, buttonElement) {
    // Отключение всех кнопок
    const allButtons = document.querySelectorAll('.option-button');
    allButtons.forEach(btn => btn.disabled = true);

    const question = questions[currentQuestionIndex];

    try {
        // Отправка ответа на сервер
        const response = await fetch('/api/submit_answer', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                user_id: userId,
                question_id: question.id,
                user_answer: selectedAnswer
            })
        });

        const result = await response.json();

        // Сохранение результата
        userAnswers.push({
            question: question.question,
            userAnswer: selectedAnswer,
            correctAnswer: question.answer,
            isCorrect: result.is_correct
        });

        if (result.is_correct) {
            correctAnswers++;
            buttonElement.classList.add('correct');
        } else {
            buttonElement.classList.add('incorrect');
            // Подсветка правильного ответа
            allButtons.forEach(btn => {
                if (btn.textContent.toLowerCase() === question.answer.toLowerCase()) {
                    btn.classList.add('correct');
                }
            });
        }

        // Показ результата
        showQuestionResult(result.is_correct, question.answer);

    } catch (error) {
        console.error('Ошибка отправки ответа:', error);
        alert('Ошибка отправки ответа. Попробуйте еще раз.');
        // Включение кнопок обратно
        allButtons.forEach(btn => btn.disabled = false);
    }
}

// Показ результата вопроса
function showQuestionResult(isCorrect, correctAnswer) {
    const resultContainer = document.getElementById('result-container');
    const resultMessage = document.getElementById('result-message');

    if (isCorrect) {
        resultMessage.innerHTML = '✅ <strong>Правильно!</strong>';
        resultMessage.className = 'result-correct';
    } else {
        resultMessage.innerHTML = `❌ <strong>Неправильно!</strong><br>Правильный ответ: <em>${correctAnswer}</em>`;
        resultMessage.className = 'result-incorrect';
    }

    resultContainer.style.display = 'block';
}

// Переход к следующему вопросу
function nextQuestion() {
    currentQuestionIndex++;
    loadQuestion();
}

// Показ финального результата
async function showFinalResult() {
    try {
        // Получение статистики пользователя
        const response = await fetch(`/api/user_stats/${userId}`);
        const stats = await response.json();

        const finalResult = document.getElementById('final-result');
        const finalStats = document.getElementById('final-stats');

        const percentage = Math.round((correctAnswers / questions.length) * 100);
        let emoji = '😔';
        let message = 'Попробуй еще раз!';

        if (percentage >= 80) {
            emoji = '🎉';
            message = 'Отлично!';
        } else if (percentage >= 60) {
            emoji = '👍';
            message = 'Хорошо!';
        } else if (percentage >= 40) {
            emoji = '🤔';
            message = 'Неплохо!';
        }

        finalStats.innerHTML = `
            <div class="final-score">
                <div class="score-circle">
                    <span class="score-number">${correctAnswers}/${questions.length}</span>
                    <span class="score-percentage">${percentage}%</span>
                </div>
                <div class="score-message">${emoji} ${message}</div>
            </div>
            <div class="overall-stats">
                <h3>📊 Общая статистика:</h3>
                <p>Всего вопросов отвечено: <strong>${stats.total_questions}</strong></p>
                <p>Правильных ответов: <strong>${stats.correct_answers}</strong></p>
                <p>Общая точность: <strong>${stats.accuracy}%</strong></p>
            </div>
        `;

        // Скрытие контейнера с вопросами
        document.getElementById('quiz-container').style.display = 'none';
        finalResult.style.display = 'block';

        // Уведомление Telegram о завершении
        tg.showAlert(`Квиз завершен! Результат: ${correctAnswers}/${questions.length} (${percentage}%)`);

    } catch (error) {
        console.error('Ошибка получения статистики:', error);
        document.getElementById('final-stats').innerHTML = `
            <div class="final-score">
                <div class="score-circle">
                    <span class="score-number">${correctAnswers}/${questions.length}</span>
                    <span class="score-percentage">${Math.round((correctAnswers / questions.length) * 100)}%</span>
                </div>
            </div>
        `;
        document.getElementById('quiz-container').style.display = 'none';
        document.getElementById('final-result').style.display = 'block';
    }
}

// Перезапуск квиза
function restartQuiz() {
    currentQuestionIndex = 0;
    correctAnswers = 0;
    userAnswers = [];

    document.getElementById('final-result').style.display = 'none';
    document.getElementById('quiz-container').style.display = 'block';

    loadQuestion();
}

// Обработчики событий
document.getElementById('next-button').addEventListener('click', nextQuestion);
document.getElementById('restart-button').addEventListener('click', restartQuiz);

// Инициализация приложения
loadQuestions();

// Настройка главной кнопки Telegram
tg.MainButton.text = "Закрыть";
tg.MainButton.show();
tg.MainButton.onClick(() => {
    tg.close();
});