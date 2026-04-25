"""
Greek Vocabulary Telegram Bot.
Words shown by topic. User marks each as "Помню" or "Новое слово".
New words enter a 9-repetition spaced cycle and appear more often.
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
    check_achievements,
    get_stats,
    get_topic_stats,
    get_user_settings,
    increment_session,
    init_db,
    mark_known,
    mark_new_word,
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
    "society": ("👥", "Κοινωνία"),
    "health": ("🏥", "Υγεία"),
    "culture": ("🎭", "Πολιτισμός"),
    "economy": ("💰", "Οικονομία"),
    "science": ("🔬", "Επιστήμη"),
    "politics": ("🏛", "Πολιτική"),
    "history": ("📜", "Ιστορία"),
    "education": ("🎓", "Εκπαίδευση"),
    "law": ("⚖️", "Δίκαιο"),
    "environment": ("🌿", "Περιβάλλον"),
}

# ── Card rendering ──────────────────────────────────────────────


def render_question(word, index, total, topic_label=""):
    """Show greek word, user tries to recall meaning."""
    greek = word["greek"]
    rep = word.get("_rep", 0)

    if rep >= 1:
        rep_info = f"  🔄 {rep}/9"
    else:
        rep_info = ""

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
    """Show answer with 'Помню' / 'Новое слово' buttons."""
    greek = word["greek"]
    russian = word.get("russian", "")
    english = word.get("english", "")
    rep = word.get("_rep", 0)

    lines = [f"[{index + 1}/{total}]\n"]
    lines.append(f"🇬🇷  <b>{greek}</b>")
    if russian:
        lines.append(f"🇷🇺  {russian}")
    if english:
        lines.append(f"🇬🇧  {english}")
    lines.append("")

    ex1 = word.get("example1", "")
    ex1_en = word.get("example1_en", "")
    if ex1:
        lines.append("📝 <b>Прочитай вслух:</b>")
        lines.append(f"<i>{ex1}</i>")
        if ex1_en:
            lines.append(f"({ex1_en})")
        lines.append("")

    root = word.get("root", "")
    if root:
        root_family = word.get("root_family", "")
        lines.append(f"🌱 <b>Корень:</b> {root}")
        if root_family:
            lines.append(f"    {root_family}")

    text = "\n".join(lines)

    if rep >= 1:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Помню", callback_data="know")],
            [InlineKeyboardButton("📖 Подробнее", callback_data="show_details")],
        ])
    else:
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Помню", callback_data="know"),
                InlineKeyboardButton("🆕 Новое слово", callback_data="new_word"),
            ],
            [InlineKeyboardButton("📖 Подробнее", callback_data="show_details")],
        ])
    return text, keyboard


def render_answer_full(word, index, total):
    """Full card with all fields."""
    greek = word["greek"]
    russian = word.get("russian", "")
    english = word.get("english", "")
    rep = word.get("_rep", 0)

    lines = [f"[{index + 1}/{total}]\n"]
    lines.append(f"🇬🇷  <b>{greek}</b>")
    if russian:
        lines.append(f"🇷🇺  {russian}")
    if english:
        lines.append(f"🇬🇧  {english}")
    lines.append("")

    root = word.get("root", "")
    root_family = word.get("root_family", "")
    if root:
        lines.append(f"🌱 <b>Корень:</b> {root}")
        if root_family:
            lines.append(f"    {root_family}")
        lines.append("")

    verb_p = word.get("verb_partner", "")
    adj_p = word.get("adjective_partner", "")
    if verb_p or adj_p:
        lines.append("🤝 <b>Сочетания:</b>")
        if verb_p:
            lines.append(f"  🔹 {verb_p}")
        if adj_p:
            lines.append(f"  🔸 {adj_p}")
        lines.append("")

    for i, (label, key, key_en) in enumerate([
        ("📝 Прочитай вслух:", "example1", "example1_en"),
        ("🔄 Ещё пример:", "example2", "example2_en"),
        ("📖 Третий пример:", "example3", "example3_en"),
    ]):
        ex = word.get(key, "")
        ex_en = word.get(key_en, "")
        if ex:
            lines.append(f"<b>{label}</b>")
            lines.append(f"<i>{ex}</i>")
            if ex_en:
                lines.append(f"({ex_en})")
            lines.append("")

    collocs = word.get("collocations", "")
    if collocs:
        parts = [c.strip() for c in collocs.split(";") if c.strip()][:3]
        if parts:
            lines.append("🔗 <b>Коллокации:</b>")
            for c in parts:
                lines.append(f"  • {c}")
            lines.append("")

    syn = word.get("synonyms", "")
    ant = word.get("antonyms", "")
    if syn:
        lines.append(f"≈ <b>Синонимы:</b> {syn}")
    if ant:
        lines.append(f"↔ <b>Антонимы:</b> {ant}")
    if syn or ant:
        lines.append("")

    dialogue = word.get("mini_dialogue", "")
    if dialogue:
        lines.append("💬 <b>Диалог:</b>")
        lines.append(f"<i>{dialogue}</i>")
        lines.append("")

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
    if meta_parts:
        lines.append(" · ".join(meta_parts))

    text = "\n".join(lines)
    if len(text) > 4000:
        text = text[:3990] + "\n..."

    if rep >= 1:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Помню", callback_data="know")],
        ])
    else:
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Помню", callback_data="know"),
                InlineKeyboardButton("🆕 Новое слово", callback_data="new_word"),
            ],
        ])
    return text, keyboard


def render_topic_menu(user_id):
    """Main menu with topics, word counts, and user progress."""
    vocab = load_vocabulary()
    topic_counts = get_topic_counts(vocab)
    topic_progress = get_topic_stats(DB, user_id, vocab)

    settings = get_user_settings(DB, user_id)
    session_num = settings["total_sessions"] + 1

    lines = [
        "📖 <b>Темы</b>\n",
        f"Сессия #{session_num}\n",
    ]

    buttons = []
    for topic in sorted(topic_counts.keys(), key=lambda t: -topic_counts[t]):
        emoji, label = TOPIC_LABELS.get(topic, ("📌", topic))
        total = topic_counts[topic]
        tp = topic_progress.get(topic, {})
        seen = tp.get("seen", 0)
        learned = tp.get("learned", 0)
        known = tp.get("known", 0)
        due = tp.get("due", 0)

        pct = int(seen / total * 100) if total else 0

        status = ""
        if due > 0:
            status = f"  🔔 {due} на повтор"

        if seen == 0:
            progress = ""
        else:
            progress = f" · {pct}%"

        lines.append(f"{emoji} <b>{label}</b>  {seen}/{total}{progress}{status}")

        btn_text = f"{emoji} {label} ({total})"
        if due > 0:
            btn_text += f" 🔔{due}"
        buttons.append(
            InlineKeyboardButton(btn_text, callback_data=f"topic:{topic}")
        )

    keyboard_rows = []
    for i in range(0, len(buttons), 2):
        keyboard_rows.append(buttons[i : i + 2])

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
        f"👁 Всего просмотрено: {stats['total_seen']}",
        f"✅ Помню: {stats['known']}",
        f"🆕 В цикле повторений: {stats['in_cycle']}",
        f"🎓 Выучено (9/9): {stats['learned']}",
        f"📅 На повторение сегодня: {stats['due_today']}",
        f"\n🏆 Всего сессий: {stats['total_sessions']}",
    ]

    lines.append("\n/learn — выбрать тему")
    return "\n".join(lines)


# ── Handlers ────────────────────────────────────────────────────


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    get_user_settings(DB, update.effective_user.id)
    vocab = load_vocabulary()

    text = (
        "🇬🇷 <b>Greek Vocabulary Bot</b>\n\n"
        f"📚 {len(vocab)} слов · {len(get_topics(vocab))} тем · Γ2 + B2\n\n"
        "<b>Как это работает:</b>\n"
        "• Видишь слово → вспоминаешь значение\n"
        "• <b>Помню</b> — знаешь слово, идём дальше\n"
        "• <b>Новое слово</b> — не знаешь, слово попадает в цикл 9 повторений\n"
        "• Новые слова будут появляться чаще!\n\n"
        "/learn — выбрать тему и начать\n"
        "/stats — прогресс\n"
        "/reset — сбросить"
    )
    await update.message.reply_text(text, parse_mode="HTML")


async def learn_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text, keyboard = render_topic_menu(user_id)
    await update.message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")


async def topic_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    topic = query.data.split(":", 1)[1]
    user_id = update.effective_user.id

    set_topic(DB, user_id, topic)
    words = get_session_words(DB, user_id, topic=topic, count=15)

    if not words:
        emoji, label = TOPIC_LABELS.get(topic, ("📌", topic))
        await query.edit_message_text(
            f"🎉 {emoji} <b>{label}</b> — все слова просмотрены!\n\n"
            "/learn — выбрать другую тему",
            parse_mode="HTML",
        )
        return

    # Get repetition info
    for w in words:
        row = DB.execute(
            "SELECT repetition FROM user_progress WHERE user_id = ? AND word_index = ?",
            (user_id, w["_index"]),
        ).fetchone()
        w["_rep"] = row["repetition"] if row and row["repetition"] >= 1 else 0

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

    try:
        text, keyboard = render_answer(words[idx], idx, len(words))
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error showing answer for word {idx}: {e}")
        text, keyboard = render_answer(words[idx], idx, len(words))
        await query.edit_message_text(text, reply_markup=keyboard)


async def show_details_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    words = context.user_data.get("session_words", [])
    idx = context.user_data.get("current_index", 0)

    if not words or idx >= len(words):
        return

    text, keyboard = render_answer_full(words[idx], idx, len(words))
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")


def render_achievements(achievements):
    """Render achievement notifications."""
    lines = []
    for a in achievements:
        if a == "mastered_word":
            lines.append("🏅 <b>Слово выучено!</b> 9/9 повторений!")
        elif isinstance(a, tuple):
            kind, val = a
            if kind == "topic_complete":
                emoji, label = TOPIC_LABELS.get(val, ("📌", val))
                lines.append(f"🏆 <b>Тема пройдена!</b> {emoji} {label} — все слова просмотрены!")
            elif kind == "topic_mastered":
                emoji, label = TOPIC_LABELS.get(val, ("📌", val))
                lines.append(f"👑 <b>Тема покорена!</b> {emoji} {label} — все слова выучены на 9/9!")
            elif kind == "milestone":
                labels = {
                    100: "💯 <b>Первая сотня!</b> 100 слов просмотрено!",
                    500: "🔥 <b>500 слов!</b> Ты на верном пути!",
                    1000: "⭐ <b>1000 слов!</b> Серьёзный уровень!",
                    2000: "🌟 <b>2000 слов!</b> Половина словаря!",
                    3000: "💎 <b>3000 слов!</b> Ты почти у цели!",
                    4000: "🚀 <b>4000 слов!</b> Финишная прямая!",
                    4630: "🎊 <b>ВСЕ 4630 СЛОВ!</b> Словарь пройден полностью!",
                }
                lines.append(labels.get(val, f"🎯 <b>{val} слов просмотрено!</b>"))
    return "\n".join(lines)


async def know_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User pressed 'Помню'."""
    query = update.callback_query
    await query.answer("✅")

    words = context.user_data.get("session_words", [])
    idx = context.user_data.get("current_index", 0)
    user_id = update.effective_user.id
    topic = context.user_data.get("session_topic", "all")

    if not words or idx >= len(words):
        return

    word = words[idx]
    if word.get("_rep", 0) >= 1:
        record_review(DB, user_id, word["_index"])
    else:
        mark_known(DB, user_id, word["_index"])

    vocab = load_vocabulary()
    achs = check_achievements(DB, user_id, word["_index"], vocab, get_topic_counts(vocab))
    if achs:
        context.user_data.setdefault("pending_achievements", []).extend(achs)

    await _advance_session(query, context, words, idx, topic)


async def new_word_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User pressed 'Новое слово' — start 9-rep cycle."""
    query = update.callback_query
    await query.answer("🆕")

    words = context.user_data.get("session_words", [])
    idx = context.user_data.get("current_index", 0)
    user_id = update.effective_user.id
    topic = context.user_data.get("session_topic", "all")

    if not words or idx >= len(words):
        return

    mark_new_word(DB, user_id, words[idx]["_index"])

    vocab = load_vocabulary()
    achs = check_achievements(DB, user_id, words[idx]["_index"], vocab, get_topic_counts(vocab))
    if achs:
        context.user_data.setdefault("pending_achievements", []).extend(achs)

    await _advance_session(query, context, words, idx, topic)


async def _advance_session(query, context, words, idx, topic):
    user_id = query.from_user.id
    next_idx = idx + 1
    context.user_data["current_index"] = next_idx

    try:
        if next_idx >= len(words):
            increment_session(DB, user_id)
            stats = get_stats(DB, user_id)
            summary = render_session_summary(stats, len(words), topic)

            achs = context.user_data.pop("pending_achievements", [])
            if achs:
                summary += "\n\n" + render_achievements(achs)

            await query.edit_message_text(summary, parse_mode="HTML")
            return

        emoji, label = TOPIC_LABELS.get(topic, ("📌", topic))
        topic_label = f"{emoji} {label}"

        text, keyboard = render_question(words[next_idx], next_idx, len(words), topic_label)
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error advancing session at word {next_idx}: {e}")
        # Skip broken card, try next
        context.user_data["current_index"] = next_idx
        await _advance_session(query, context, words, next_idx, topic)


async def skip_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("⏭")

    words = context.user_data.get("session_words", [])
    idx = context.user_data.get("current_index", 0)
    topic = context.user_data.get("session_topic", "all")

    await _advance_session(query, context, words, idx, topic)


async def stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    stats = get_stats(DB, user_id)
    vocab = load_vocabulary()
    topic_counts = get_topic_counts(vocab)
    topic_progress = get_topic_stats(DB, user_id, vocab)

    lines = [
        "📊 <b>Твой прогресс</b>\n",
        f"📚 Словарь: {len(vocab)} слов",
        f"👁 Просмотрено: {stats['total_seen']}",
        f"✅ Помню: {stats['known']}",
        f"🆕 В цикле повторений: {stats['in_cycle']}",
        f"🎓 Выучено (9/9): {stats['learned']}",
        f"📅 На повтор сегодня: {stats['due_today']}",
        f"🏆 Сессий: {stats['total_sessions']}",
        "",
        "<b>По темам:</b>",
    ]

    for topic in sorted(topic_counts.keys()):
        emoji, label = TOPIC_LABELS.get(topic, ("📌", topic))
        total = topic_counts[topic]
        tp = topic_progress.get(topic, {})
        seen = tp.get("seen", 0)
        learned = tp.get("learned", 0)
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
    app.add_handler(CallbackQueryHandler(show_details_callback, pattern=r"^show_details$"))
    app.add_handler(CallbackQueryHandler(know_callback, pattern=r"^know$"))
    app.add_handler(CallbackQueryHandler(new_word_callback, pattern=r"^new_word$"))
    app.add_handler(CallbackQueryHandler(skip_callback, pattern=r"^skip$"))
    app.add_handler(CallbackQueryHandler(reset_confirm_callback, pattern=r"^reset_confirm$"))
    app.add_handler(CallbackQueryHandler(reset_cancel_callback, pattern=r"^reset_cancel$"))

    logger.info("Bot started!")
    app.run_polling()


if __name__ == "__main__":
    main()
