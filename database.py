"""
SQLite persistence for user progress and spaced repetition.
Words marked "Новое слово" enter a 9-repetition cycle (Brezhestovsky method).
Words marked "Помню" are skipped.
"""
import sqlite3
from datetime import date, timedelta

# Day 1, 3, 5, 7, 9, 11, 14, 18, 23
INTERVALS = [0, 2, 2, 2, 2, 2, 3, 4, 5]


def init_db(db_path="greek_vocab.db"):
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS user_progress (
            user_id       INTEGER NOT NULL,
            word_index    INTEGER NOT NULL,
            repetition    INTEGER DEFAULT 0,
            next_review   TEXT,
            last_reviewed TEXT,
            half          INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, word_index)
        );

        CREATE TABLE IF NOT EXISTS user_settings (
            user_id        INTEGER PRIMARY KEY,
            current_topic  TEXT DEFAULT 'all',
            day_counter    INTEGER DEFAULT 0,
            total_sessions INTEGER DEFAULT 0,
            created_at     TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_review
            ON user_progress(user_id, next_review);
        CREATE INDEX IF NOT EXISTS idx_rep
            ON user_progress(user_id, repetition);
    """)
    conn.commit()
    return conn


def get_user_settings(conn, user_id):
    row = conn.execute(
        "SELECT * FROM user_settings WHERE user_id = ?", (user_id,)
    ).fetchone()
    if row:
        return dict(row)
    today = date.today().isoformat()
    conn.execute(
        "INSERT INTO user_settings (user_id, created_at) VALUES (?, ?)",
        (user_id, today),
    )
    conn.commit()
    return {
        "user_id": user_id,
        "current_topic": "all",
        "day_counter": 0,
        "total_sessions": 0,
        "created_at": today,
    }


def set_topic(conn, user_id, topic):
    get_user_settings(conn, user_id)
    conn.execute(
        "UPDATE user_settings SET current_topic = ? WHERE user_id = ?",
        (topic, user_id),
    )
    conn.commit()


def increment_session(conn, user_id):
    get_user_settings(conn, user_id)
    conn.execute(
        "UPDATE user_settings SET total_sessions = total_sessions + 1 "
        "WHERE user_id = ?",
        (user_id,),
    )
    conn.commit()


def get_review_words(conn, user_id, today=None, limit=15):
    """Words due for review (next_review <= today, repetition 1..8)."""
    if today is None:
        today = date.today().isoformat()
    rows = conn.execute(
        "SELECT word_index FROM user_progress "
        "WHERE user_id = ? AND next_review <= ? "
        "AND repetition >= 1 AND repetition < 9 "
        "ORDER BY next_review ASC LIMIT ?",
        (user_id, today, limit),
    ).fetchall()
    return [r["word_index"] for r in rows]


def get_known_and_learning(conn, user_id):
    """Return sets of word indices that user has already seen."""
    rows = conn.execute(
        "SELECT word_index, repetition FROM user_progress "
        "WHERE user_id = ? AND next_review IS NOT NULL",
        (user_id,),
    ).fetchall()
    known = set()      # marked "помню" (rep=0 with next_review set) or learned (rep=9)
    learning = set()   # in 9-rep cycle (rep 1..8)
    for r in rows:
        if r["repetition"] >= 1 and r["repetition"] < 9:
            learning.add(r["word_index"])
        else:
            known.add(r["word_index"])
    return known, learning


def mark_known(conn, user_id, word_index):
    """User pressed 'Помню' — mark word as known, skip it in future."""
    today_str = date.today().isoformat()
    conn.execute(
        "INSERT INTO user_progress (user_id, word_index, repetition, next_review, last_reviewed, half) "
        "VALUES (?, ?, 0, ?, ?, 0) "
        "ON CONFLICT(user_id, word_index) DO UPDATE SET "
        "last_reviewed = ?",
        (user_id, word_index, today_str, today_str, today_str),
    )
    conn.commit()


def mark_new_word(conn, user_id, word_index):
    """User pressed 'Новое слово' — start 9-repetition cycle."""
    today = date.today()
    today_str = today.isoformat()
    next_review = (today + timedelta(days=INTERVALS[1])).isoformat()
    conn.execute(
        "INSERT INTO user_progress (user_id, word_index, repetition, next_review, last_reviewed, half) "
        "VALUES (?, ?, 1, ?, ?, 0) "
        "ON CONFLICT(user_id, word_index) DO UPDATE SET "
        "repetition = 1, next_review = ?, last_reviewed = ?",
        (user_id, word_index, next_review, today_str, next_review, today_str),
    )
    conn.commit()


def record_review(conn, user_id, word_index):
    """Advance repetition for a word in the 9-rep cycle."""
    today = date.today()
    today_str = today.isoformat()

    row = conn.execute(
        "SELECT repetition FROM user_progress "
        "WHERE user_id = ? AND word_index = ?",
        (user_id, word_index),
    ).fetchone()

    rep = row["repetition"] if row else 0
    new_rep = min(rep + 1, 9)

    if new_rep < 9:
        interval = INTERVALS[new_rep]
        next_review = (today + timedelta(days=interval)).isoformat()
    else:
        next_review = (today + timedelta(days=30)).isoformat()

    conn.execute(
        "INSERT INTO user_progress (user_id, word_index, repetition, next_review, last_reviewed, half) "
        "VALUES (?, ?, ?, ?, ?, 0) "
        "ON CONFLICT(user_id, word_index) DO UPDATE SET "
        "repetition = ?, next_review = ?, last_reviewed = ?",
        (user_id, word_index, new_rep, next_review, today_str,
         new_rep, next_review, today_str),
    )
    conn.commit()
    return new_rep


def get_stats(conn, user_id):
    settings = get_user_settings(conn, user_id)
    today = date.today().isoformat()

    rows = conn.execute(
        "SELECT repetition, COUNT(*) as cnt FROM user_progress "
        "WHERE user_id = ? AND next_review IS NOT NULL "
        "GROUP BY repetition ORDER BY repetition",
        (user_id,),
    ).fetchall()

    by_rep = {r["repetition"]: r["cnt"] for r in rows}
    total_seen = sum(by_rep.values())
    known = by_rep.get(0, 0)
    learned = by_rep.get(9, 0)
    in_cycle = total_seen - known - learned

    due_today = conn.execute(
        "SELECT COUNT(*) as cnt FROM user_progress "
        "WHERE user_id = ? AND next_review <= ? "
        "AND repetition >= 1 AND repetition < 9",
        (user_id, today),
    ).fetchone()["cnt"]

    return {
        "total_seen": total_seen,
        "known": known,
        "learned": learned,
        "in_cycle": in_cycle,
        "due_today": due_today,
        "total_sessions": settings["total_sessions"],
        "by_repetition": by_rep,
    }


def get_topic_stats(conn, user_id, vocab):
    from datetime import date as _date
    today = _date.today().isoformat()

    rows = conn.execute(
        "SELECT word_index, repetition, next_review FROM user_progress "
        "WHERE user_id = ? AND next_review IS NOT NULL",
        (user_id,),
    ).fetchall()

    idx_topic = {}
    for w in vocab:
        t = w.get("topic", "")
        if t:
            idx_topic[w["_index"]] = t

    stats = {}
    for r in rows:
        topic = idx_topic.get(r["word_index"], "")
        if not topic:
            continue
        if topic not in stats:
            stats[topic] = {"seen": 0, "learned": 0, "due": 0, "known": 0}
        stats[topic]["seen"] += 1
        if r["repetition"] == 0:
            stats[topic]["known"] += 1
        elif r["repetition"] >= 9:
            stats[topic]["learned"] += 1
        if r["next_review"] and r["next_review"] <= today and 1 <= r["repetition"] < 9:
            stats[topic]["due"] += 1

    return stats


def reset_progress(conn, user_id):
    conn.execute("DELETE FROM user_progress WHERE user_id = ?", (user_id,))
    conn.execute(
        "UPDATE user_settings SET day_counter = 0, total_sessions = 0 "
        "WHERE user_id = ?",
        (user_id,),
    )
    conn.commit()
