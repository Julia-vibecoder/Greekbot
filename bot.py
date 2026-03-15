"""
Greek Vocabulary Telegram Bot.
Brezhestovsky method: 9 repetitions over 23 days.
Words organized and shown by topic.
"""
import logging
import os

from dotenv import load_dotenv
from telegram import (
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from database import (
    get_stats,
    get_topic_stats,
    get_user_settings,
    increment_session,
    init_db,
    record_review,
    reset_progress,
    set_topic,
)
from vocab import get_session_words, get_topics, get_topic_counts, load_vocabulary

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB = init_db()

TOPIC_LABELS = {
    "politics": ("🏛", "Πολιτική"),
    "society": ("👥", "Κοινωνία"),
    "economy": ("💰", "Οικονομία"),
    "technology": ("💻", "Τεχνολογία"),
    "environment": ("🌿", "Περιβάλλον"),
    "education": ("🎓", "Εκπαίδευση"),
    "culture": ("🎭", "Πολιτισμός"),
    "philosophy": ("🤔", "Φιλοσοφία"),
    "psychology": ("🧠", "Ψυχολογία"),
    "media": ("📺", "ΜΜΕ"),
    "international_relations": ("🌍", "Διεθνείς σχέσεις"),
    "law": ("⚖️", "Δίκαιο"),
    "health": ("🏥", "Υγεία"),
    "daily_life": ("🏠", "Καθημερινότητα"),
}

# ── Card rendering ──────────────────────────────────────────────


def render_question(word, index, total, topic_label=""):
    greek = word["greek"]
    rep = word.get("_rep", 0)
    rep_info = f"  🔄 {rep}/9" if rep else "  🆕"

    header = f"<b>{topic_label}</b>\n" if topic_label else ""
    text = (
        f"{header}"
        f"[{index + 1}/{total}]{rep_info}\n\n"
        f"🇬🇷  <b>{greek}</b>\n\n"
        f"<i>Вспомни значение...</i>"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("👀 Показать ответ", callback_data="show_answer")],
        [InlineKeyboardButton("⏭ Пропустить", callback_data="skip")],
    ])
    return text, keyboard


def render_answer(word, index, total):
    greek = word["greek"]
    russian = word.get("russian", "")
    english = word.get("english", "")

    lines = [f"[{index + 1}/{total}]\n"]
    lines.append(f"🇬🇷  <b>{greek}</b>")

    if russian:
        lines.append(f"🇷🇺  {russian}")
    if english:
        lines.append(f"🇬🇧  {english}")
    lines.append("")

    # Root & family
    root = word.get("root", "")
    root_family = word.get("root_family", "")
    if root:
        lines.append(f"🌱 <b>Корень:</b> {root}")
        if root_family:
            lines.append(f"    {root_family}")
        lines.append("")

    # Verb & adjective partners
    verb_p = word.get("verb_partner", "")
    adj_p = word.get("adjective_partner", "")
    if verb_p or adj_p:
        lines.append("🤝 <b>Сочетания:</b>")
        if verb_p:
            lines.append(f"  🔹 {verb_p}")
        if adj_p:
            lines.append(f"  🔸 {adj_p}")
        lines.append("")

    # Example 1
    ex1 = word.get("example1", "")
    ex1_en = word.get("example1_en", "")
    if ex1:
        lines.append("📝 <b>Прочитай вслух:</b>")
        lines.append(f"<i>{ex1}</i>")
        if ex1_en:
            lines.append(f"({ex1_en})")
        lines.append("")

    # Example 2
    ex2 = word.get("example2", "")
    ex2_en = word.get("example2_en", "")
    if ex2:
        lines.append("🔄 <b>Ещё пример:</b>")
        lines.append(f"<i>{ex2}</i>")
        if ex2_en:
            lines.append(f"({ex2_en})")
        lines.append("")

    # Example 3
    ex3 = word.get("example3", "")
    ex3_en = word.get("example3_en", "")
    if ex3:
        lines.append("📖 <b>Третий пример:</b>")
        lines.append(f"<i>{ex3}</i>")
        if ex3_en:
            lines.append(f"({ex3_en})")
        lines.append("")

    # Collocations
    collocs = word.get("collocations", "")
    if collocs:
        parts = [c.strip() for c in collocs.split(";") if c.strip()][:3]
        if parts:
            lines.append("🔗 <b>Коллокации:</b>")
            for c in parts:
                lines.append(f"  • {c}")
            lines.append("")

    # Synonyms / Antonyms
    syn = word.get("synonyms", "")
    ant = word.get("antonyms", "")
    if syn:
        lines.append(f"≈ <b>Синонимы:</b> {syn}")
    if ant:
        lines.append(f"↔ <b>Антонимы:</b> {ant}")
    if syn or ant:
        lines.append("")

    # Mini dialogue
    dialogue = word.get("mini_dialogue", "")
    if dialogue:
        lines.append("💬 <b>Диалог:</b>")
        lines.append(f"<i>{dialogue}</i>")
        lines.append("")

    # Original example & category
    example = word.get("example", "")
    if example:
        lines.append(f"📌 <b>Пример:</b> <i>{example}</i>")
    category = word.get("category", "")
    if category:
        lines.append(f"📂 <b>Категория:</b> {category}")

    # Meta info
    meta_parts = []
    level = word.get("level", "")
    if level:
        meta_parts.append(f"📊 {level}")
    register = word.get("register", "")
    if register:
        meta_parts.append(f"📋 {register}")
    frequency = word.get("frequency", "")
    if frequency:
        meta_parts.append(f"⚡ {frequency}")
    source = word.get("source", "")
    if source:
        meta_parts.append(f"📖 {source}")
    if meta_parts:
        lines.append("")
        lines.append(" · ".join(meta_parts))

    notes = word.get("notes", "")
    if notes:
        lines.append(f"💡 {notes}")

    text = "\n".join(lines)
    if len(text) > 4000:
        text = text[:3990] + "\n..."

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Прочёл вслух!", callback_data="read_aloud")],
    ])
    return text, keyboard


def render_topic_menu(user_id):
    """Main menu with topics, word counts, and user progress."""
    vocab = load_vocabulary()
    topic_counts = get_topic_counts(vocab)
    topic_progress = get_topic_stats(DB, user_id, vocab)

    settings = get_user_settings(DB, user_id)
    half = settings["day_counter"] % 2
    half_label = "A" if half == 0 else "B"
    session_num = settings["total_sessions"] + 1

    lines = [
        "📖 <b>Темы</b>\n",
        f"Половина <b>{half_label}</b> · Сессия #{session_num}\n",
    ]

    buttons = []
    for topic in sorted(topic_counts.keys()):
        emoji, label = TOPIC_LABELS.get(topic, ("📌", topic))
        total = topic_counts[topic]
        seen = topic_progress.get(topic, {}).get("seen", 0)
        learned = topic_progress.get(topic, {}).get("learned", 0)
        due = topic_progress.get(topic, {}).get("due", 0)

        # Progress bar
        pct = int(seen / total * 100) if total else 0
        bar = "▓" * (pct // 10) + "░" * (10 - pct // 10)

        status = ""
        if due > 0:
            status = f" 🔔{due}"

        lines.append(f"{emoji} <b>{label}</b>: {seen}/{total} {bar}{status}")

        btn_text = f"{emoji} {label} ({total})"
        if due > 0:
            btn_text += f" 🔔{due}"
        buttons.append(
            InlineKeyboardButton(btn_text, callback_data=f"topic:{topic}")
        )

    # Build keyboard: 2 buttons per row
    keyboard_rows = []
    for i in range(0, len(buttons), 2):
        keyboard_rows.append(buttons[i : i + 2])

    # Add "All topics" at the bottom
    keyboard_rows.append(
        [InlineKeyboardButton("📚 Все темы (случайно)", callback_data="topic:all")]
    )

    text = "\n".join(lines)
    return text, InlineKeyboardMarkup(keyboard_rows)


def render_session_summary(stats, session_count, topic):
    emoji, label = TOPIC_LABELS.get(topic, ("📌", topic))
    lines = [
        f"📊 <b>Сессия завершена!</b> {emoji} {label}\n",
        f"✅ Слов в сессии: {session_count}",
        f"📚 Всего изучено: {stats['total_seen']}",
        f"🎓 Выучено (9/9): {stats['learned']}",
        f"🔄 В процессе: {stats['in_progress']}",
        f"📅 На повторение сегодня: {stats['due_today']}",
        f"\n🏆 Всего сессий: {stats['total_sessions']}",
    ]

    by_rep = stats.get("by_repetition", {})
    if by_rep:
        lines.append("\n<b>Прогресс:</b>")
        for rep in range(1, 10):
            count = by_rep.get(rep, 0)
            if count > 0:
                bar = "█" * min(count // 5, 20)
                lines.append(f"  {rep}/9: {bar} {count}")

    lines.append("\n/learn — выбрать тему")
    return "\n".join(lines)


# ── Handlers ────────────────────────────────────────────────────


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    get_user_settings(DB, update.effective_user.id)
    vocab = load_vocabulary()

    text = (
        "🇬🇷 <b>Greek Vocabulary Bot</b>\n\n"
        f"📚 {len(vocab)} слов · 14 тем · Γ2 + B2\n\n"
        "<b>Метод Брежестовского:</b>\n"
        "• 9 повторений за 23 дня\n"
        "• Каждую сессию — новая половина слов\n"
        "• Читай вслух каждое слово!\n\n"
        "<i>Запоминание = Контекст × Повторения × Вслух</i>\n\n"
        "/learn — выбрать тему и начать\n"
        "/stats — прогресс\n"
        "/reset — сбросить"
    )
    await update.message.reply_text(text, parse_mode="HTML")


async def learn_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show topic menu."""
    user_id = update.effective_user.id
    text, keyboard = render_topic_menu(user_id)
    await update.message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")


async def topic_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User selected a topic — build session and show first card."""
    query = update.callback_query
    await query.answer()

    topic = query.data.split(":", 1)[1]
    user_id = update.effective_user.id

    set_topic(DB, user_id, topic)
    words = get_session_words(DB, user_id, topic=topic, count=15)

    if not words:
        emoji, label = TOPIC_LABELS.get(topic, ("📌", topic))
        await query.edit_message_text(
            f"🎉 {emoji} <b>{label}</b> — все слова уже на повторении!\n\n"
            "/learn — выбрать другую тему",
            parse_mode="HTML",
        )
        return

    # Get repetition info for each word
    for w in words:
        row = DB.execute(
            "SELECT repetition FROM user_progress WHERE user_id = ? AND word_index = ?",
            (user_id, w["_index"]),
        ).fetchone()
        w["_rep"] = row["repetition"] if row and row["repetition"] > 0 else 0

    context.user_data["session_words"] = words
    context.user_data["current_index"] = 0
    context.user_data["session_topic"] = topic

    emoji, label = TOPIC_LABELS.get(topic, ("📌", topic))
    topic_label = f"{emoji} {label}"

    text, keyboard = render_question(words[0], 0, len(words), topic_label)
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")


async def show_answer_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    words = context.user_data.get("session_words", [])
    idx = context.user_data.get("current_index", 0)

    if not words or idx >= len(words):
        await query.edit_message_text("Сессия завершена. /learn для новой.")
        return

    text, keyboard = render_answer(words[idx], idx, len(words))
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")


async def read_aloud_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("✅")

    words = context.user_data.get("session_words", [])
    idx = context.user_data.get("current_index", 0)
    user_id = update.effective_user.id
    topic = context.user_data.get("session_topic", "all")

    if not words or idx >= len(words):
        return

    record_review(DB, user_id, words[idx]["_index"])

    next_idx = idx + 1
    context.user_data["current_index"] = next_idx

    if next_idx >= len(words):
        increment_session(DB, user_id)
        stats = get_stats(DB, user_id)
        summary = render_session_summary(stats, len(words), topic)
        await query.edit_message_text(summary, parse_mode="HTML")
        return

    emoji, label = TOPIC_LABELS.get(topic, ("📌", topic))
    topic_label = f"{emoji} {label}"

    text, keyboard = render_question(words[next_idx], next_idx, len(words), topic_label)
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")


async def skip_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Skip current word without recording review."""
    query = update.callback_query
    await query.answer("⏭")

    words = context.user_data.get("session_words", [])
    idx = context.user_data.get("current_index", 0)
    user_id = update.effective_user.id
    topic = context.user_data.get("session_topic", "all")

    next_idx = idx + 1
    context.user_data["current_index"] = next_idx

    if not words or next_idx >= len(words):
        increment_session(DB, user_id)
        stats = get_stats(DB, user_id)
        summary = render_session_summary(stats, len(words), topic)
        await query.edit_message_text(summary, parse_mode="HTML")
        return

    emoji, label = TOPIC_LABELS.get(topic, ("📌", topic))
    topic_label = f"{emoji} {label}"

    text, keyboard = render_question(words[next_idx], next_idx, len(words), topic_label)
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")


async def stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    stats = get_stats(DB, user_id)
    vocab = load_vocabulary()
    topic_counts = get_topic_counts(vocab)
    topic_progress = get_topic_stats(DB, user_id, vocab)

    lines = [
        "📊 <b>Твой прогресс</b>\n",
        f"📚 Словарь: {len(vocab)} слов",
        f"👁 Изучено: {stats['total_seen']}",
        f"🎓 Выучено (9/9): {stats['learned']}",
        f"🔄 В процессе: {stats['in_progress']}",
        f"📅 На повтор сегодня: {stats['due_today']}",
        f"🏆 Сессий: {stats['total_sessions']}",
        "",
        "<b>По темам:</b>",
    ]

    for topic in sorted(topic_counts.keys()):
        emoji, label = TOPIC_LABELS.get(topic, ("📌", topic))
        total = topic_counts[topic]
        seen = topic_progress.get(topic, {}).get("seen", 0)
        learned = topic_progress.get(topic, {}).get("learned", 0)
        if seen > 0:
            lines.append(f"  {emoji} {label}: {seen}/{total} (🎓{learned})")

    remaining = len(vocab) - stats["total_seen"]
    if remaining > 0:
        lines.append(f"\n⏳ Осталось: {remaining} слов")

    lines.append("\n/learn — начать сессию")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def reset_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("❌ Да, сбросить", callback_data="reset_confirm"),
            InlineKeyboardButton("↩️ Отмена", callback_data="reset_cancel"),
        ]
    ])
    await update.message.reply_text(
        "⚠️ <b>Сбросить весь прогресс?</b>\nВсе повторения будут удалены.",
        reply_markup=keyboard,
        parse_mode="HTML",
    )


async def reset_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    reset_progress(DB, update.effective_user.id)
    await query.edit_message_text("✅ Прогресс сброшен. /learn — начать заново.")


async def reset_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("↩️ Отменено.")


async def post_init(app: Application):
    """Set bot commands menu."""
    await app.bot.set_my_commands([
        BotCommand("learn", "📖 Выбрать тему и учить"),
        BotCommand("stats", "📊 Мой прогресс"),
        BotCommand("reset", "🗑 Сбросить прогресс"),
    ])


# ── Main ────────────────────────────────────────────────────────


def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("Set TELEGRAM_BOT_TOKEN in .env")

    vocab = load_vocabulary()
    logger.info(f"Loaded {len(vocab)} words, {len(get_topics(vocab))} topics")

    app = Application.builder().token(token).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("learn", learn_handler))
    app.add_handler(CommandHandler("stats", stats_handler))
    app.add_handler(CommandHandler("reset", reset_handler))

    app.add_handler(CallbackQueryHandler(topic_callback, pattern=r"^topic:"))
    app.add_handler(CallbackQueryHandler(show_answer_callback, pattern=r"^show_answer$"))
    app.add_handler(CallbackQueryHandler(read_aloud_callback, pattern=r"^read_aloud$"))
    app.add_handler(CallbackQueryHandler(skip_callback, pattern=r"^skip$"))
    app.add_handler(CallbackQueryHandler(reset_confirm_callback, pattern=r"^reset_confirm$"))
    app.add_handler(CallbackQueryHandler(reset_cancel_callback, pattern=r"^reset_cancel$"))

    logger.info("Bot started!")
    app.run_polling()


if __name__ == "__main__":
    main()
