"""
CSV vocabulary loader and session word selection logic.
Three-queue system: REVIEW → NEW → LEARNED.
"""
import csv
import os

VOCAB_PATH = os.path.join(
    os.path.dirname(__file__), "data", "enriched", "unified_vocabulary.csv"
)

_vocabulary = None


def load_vocabulary(path=None):
    global _vocabulary
    if _vocabulary is not None:
        return _vocabulary

    path = path or VOCAB_PATH
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = []
        for i, row in enumerate(reader):
            if row.get("greek", "").startswith("---"):
                continue
            row["_index"] = len(rows)
            rows.append(row)

    _vocabulary = rows
    return _vocabulary


def get_topics(vocab=None):
    vocab = vocab or load_vocabulary()
    topics = sorted({r["topic"] for r in vocab if r.get("topic")})
    return topics


def get_word_indices_by_topic(topic="all", vocab=None):
    vocab = vocab or load_vocabulary()
    if topic == "all":
        return [r["_index"] for r in vocab]
    return [r["_index"] for r in vocab if r.get("topic") == topic]


def get_session_words(db_conn, user_id, topic="all", count=15):
    """Build a session of up to `count` words using three-queue priority."""
    from database import (
        get_current_half,
        get_review_words,
        get_new_words,
        assign_halves,
    )

    vocab = load_vocabulary()
    word_indices = get_word_indices_by_topic(topic, vocab)

    # Ensure halves are assigned
    assign_halves(db_conn, user_id, word_indices)

    session = []

    # Queue 1: REVIEW — words due for repetition
    review_indices = get_review_words(db_conn, user_id, limit=count)
    # Filter to current topic if not "all"
    if topic != "all":
        topic_set = set(word_indices)
        review_indices = [i for i in review_indices if i in topic_set]
    session.extend(review_indices[:count])

    # Queue 2: NEW — unseen words for current half
    remaining = count - len(session)
    if remaining > 0:
        half = get_current_half(db_conn, user_id)
        new_indices = get_new_words(
            db_conn, user_id, half, word_indices, limit=remaining
        )
        session.extend(new_indices)

    # Build word dicts
    return [vocab[i] for i in session]


def get_topic_counts(vocab=None):
    """Return {topic: word_count} for all topics."""
    vocab = vocab or load_vocabulary()
    counts = {}
    for row in vocab:
        topic = row.get("topic", "")
        if topic:
            counts[topic] = counts.get(topic, 0) + 1
    return counts


def get_word_by_index(index):
    vocab = load_vocabulary()
    if 0 <= index < len(vocab):
        return vocab[index]
    return None
