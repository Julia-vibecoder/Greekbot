"""
SQLite persistence for user progress and spaced repetition scheduling.
Brezhestovsky method: 9 repetitions over 23 days.
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
        "UPDATE user_settings SET day_counter = day_counter + 1, "
        "total_sessions = total_sessions + 1 WHERE user_id = ?",
        (user_id,),
    )
    conn.commit()


def get_current_half(conn, user_id):
    settings = get_user_settings(conn, user_id)
    return settings["day_counter"] % 2


def assign_halves(conn, user_id, word_indices):
    """Assign alternating halves (0/1) to words not yet in user_progress."""
    existing = set()
    for row in conn.execute(
        "SELECT word_index FROM user_progress WHERE user_id = ?", (user_id,)
    ):
        existing.add(row["word_index"])

    new_indices = [i for i in word_indices if i not in existing]
    if not new_indices:
        return

    rows = []
    for i, idx in enumerate(new_indices):
        half = i % 2
        rows.append((user_id, idx, 0, None, None, half))

    conn.executemany(
        "INSERT OR IGNORE INTO user_progress "
        "(user_id, word_index, repetition, next_review, last_reviewed, half) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()


def get_review_words(conn, user_id, today=None, limit=15):
    """Words due for review (next_review <= today, repetition < 9)."""
    if today is None:
        today = date.today().isoformat()
    rows = conn.execute(
        "SELECT word_index FROM user_progress "
        "WHERE user_id = ? AND next_review <= ? AND repetition < 9 "
        "ORDER BY next_review ASC LIMIT ?",
        (user_id, today, limit),
    ).fetchall()
    return [r["word_index"] for r in rows]


def get_new_words(conn, user_id, half, word_indices, limit=15):
    """Unseen words for the given half."""
    seen = set()
    for row in conn.execute(
        "SELECT word_index FROM user_progress "
        "WHERE user_id = ? AND next_review IS NOT NULL",
        (user_id,),
    ):
        seen.add(row["word_index"])

    results = []
    for idx in word_indices:
        if idx in seen:
            continue
        row = conn.execute(
            "SELECT half FROM user_progress WHERE user_id = ? AND word_index = ?",
            (user_id, idx),
        ).fetchone()
        if row and row["half"] == half:
            results.append(idx)
            if len(results) >= limit:
                break
    return results


def record_review(conn, user_id, word_index):
    """Record that user read the word aloud. Advance repetition."""
    today = date.today()
    today_str = today.isoformat()

    row = conn.execute(
        "SELECT repetition FROM user_progress "
        "WHERE user_id = ? AND word_index = ?",
        (user_id, word_index),
    ).fetchone()

    if row is None:
        rep = 0
    else:
        rep = row["repetition"]

    new_rep = min(rep + 1, 9)

    if new_rep < 9:
        interval = INTERVALS[new_rep]
        next_review = (today + timedelta(days=interval)).isoformat()
    else:
        # Learned — review in 30 days
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
    """User progress statistics."""
    settings = get_user_settings(conn, user_id)

    rows = conn.execute(
        "SELECT repetition, COUNT(*) as cnt FROM user_progress "
        "WHERE user_id = ? AND next_review IS NOT NULL "
        "GROUP BY repetition ORDER BY repetition",
        (user_id,),
    ).fetchall()

    by_rep = {r["repetition"]: r["cnt"] for r in rows}
    total_seen = sum(by_rep.values())
    learned = by_rep.get(9, 0)

    today = date.today().isoformat()
    due_today = conn.execute(
        "SELECT COUNT(*) as cnt FROM user_progress "
        "WHERE user_id = ? AND next_review <= ? AND repetition < 9",
        (user_id, today),
    ).fetchone()["cnt"]

    return {
        "total_seen": total_seen,
        "learned": learned,
        "in_progress": total_seen - learned,
        "due_today": due_today,
        "total_sessions": settings["total_sessions"],
        "by_repetition": by_rep,
    }


def get_topic_stats(conn, user_id, vocab):
    """Per-topic progress: {topic: {seen, learned, due}}."""
    from datetime import date as _date

    today = _date.today().isoformat()

    rows = conn.execute(
        "SELECT word_index, repetition, next_review FROM user_progress "
        "WHERE user_id = ? AND next_review IS NOT NULL",
        (user_id,),
    ).fetchall()

    # Build word_index → topic map
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
            stats[topic] = {"seen": 0, "learned": 0, "due": 0}
        stats[topic]["seen"] += 1
        if r["repetition"] >= 9:
            stats[topic]["learned"] += 1
        if r["next_review"] <= today and r["repetition"] < 9:
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
