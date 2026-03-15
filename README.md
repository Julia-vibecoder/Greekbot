# 🤖 Vocab Bot Workshop

## Структура проекта

```
vocab-bot-workshop/
├── README.md           ← Этот файл
├── env_example.txt     ← Шаблон токенов → переименуй в .env
├── agents.json         ← Описание AI-агентов (изучи!)
├── best_practice.md    ← Методология обучения (обязательно прочти!)
├── data/
│   ├── raw/
│   │   └── KLIK_A2_glossary.csv  ← Словарь греческого A2 (1700+ слов)
│   └── enriched/                 ← Обогащённые данные
└── outputs/                      ← Результаты работы агентов
```

---

## Твоя задача

Создать Telegram-бота для изучения лексики с:
- 🔄 Spaced repetition (9 повторений)
- 🗣️ Чтением вслух
- 🤖 AI-агентами для генерации контента

---

## Шаг 1: Токены

### Telegram
1. @BotFather → `/newbot` → скопируй токен

### OpenAI
1. platform.openai.com/api-keys → создай ключ

### Настройка
```bash
mv env_example.txt .env
# Открой .env и вставь токены
```

---

## Шаг 2: Данные

Словарь уже готов: `data/raw/KLIK_A2_glossary.csv` содержит 1700+ греческих слов уровня A2.

Формат CSV:
| Колонка | Описание |
|---------|----------|
| `greek` | Греческое слово с артиклем |
| `english` | Перевод на английский |

---

## Шаг 3: Напиши код

Тебе нужно создать:

| Файл | Что делает |
|------|------------|
| `bot.py` | Telegram бот |
| `database.py` | Хранение прогресса |

### Минимальный bot.py

```python
from telegram import Update
from telegram.ext import Application, CommandHandler

async def start(update, context):
    await update.message.reply_text("Привет! /learn чтобы начать")

async def learn(update, context):
    # TODO: показать слово из CSV
    pass

def main():
    app = Application.builder().token("YOUR_TOKEN").build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("learn", learn))
    app.run_polling()

if __name__ == "__main__":
    main()
```

---

## Шаг 4: Реализуй фичи

- [ ] Загрузка слов из CSV
- [ ] Показ слова → ответа → следующее
- [ ] Кнопка "Прочёл вслух!"
- [ ] Подсчёт повторений (9 раз = выучено)
- [ ] Расписание повторений (spaced repetition)

---

## Ресурсы

- **Методология:** `best_practice.md`
- **Агенты:** `agents.json`
- **Telegram API:** python-telegram-bot.readthedocs.io
- **OpenAI:** platform.openai.com/docs

---

*Удачи! 🎉*
