"""
CSV vocabulary loader and session word selection logic.
Session priority: REVIEW (due words in 9-rep cycle) → UNSEEN (new words).
"""
import csv
import os
import random

VOCAB_PATH = os.path.join(
    os.path.dirname(__file__), "data", "enriched", "unified_vocabulary_enriched.csv"
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
        for row in reader:
            if row.get("greek", "").startswith("---"):
                continue
            row["_index"] = len(rows)
            rows.append(row)

    _vocabulary = rows
    return _vocabulary


def get_topics(vocab=None):
    vocab = vocab or load_vocabulary()
    return sorted({r["topic"] for r in vocab if r.get("topic")})


def get_word_indices_by_topic(topic="all", vocab=None):
    vocab = vocab or load_vocabulary()
    if topic == "all":
        return [r["_index"] for r in vocab]
    return [r["_index"] for r in vocab if r.get("topic") == topic]


def get_session_words(db_conn, user_id, topic="all", count=15):
    """Build a session: review words first, then unseen words."""
    from database import get_review_words, get_known_and_learning

    vocab = load_vocabulary()
    topic_indices = set(get_word_indices_by_topic(topic, vocab))
    known, learning = get_known_and_learning(db_conn, user_id)
    seen = known | learning

    session = []

    # Queue 1: words in 9-rep cycle that are due for review
    review_indices = get_review_words(db_conn, user_id, limit=count)
    if topic != "all":
        review_indices = [i for i in review_indices if i in topic_indices]
    for i in review_indices:
        if len(session) >= count:
            break
        session.append(i)

    # Queue 2: unseen words (random order)
    remaining = count - len(session)
    if remaining > 0:
        unseen = [i for i in topic_indices if i not in seen]
        random.shuffle(unseen)
        session.extend(unseen[:remaining])

    return [vocab[i] for i in session]


def get_topic_counts(vocab=None):
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
