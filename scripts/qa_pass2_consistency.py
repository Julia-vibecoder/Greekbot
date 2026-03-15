#!/usr/bin/env python3
"""
QA Pass 2 — Consistency normalization.
Normalizes topic, register, frequency, and source fields across the entire CSV.
"""
import csv
import re

INPUT = "data/enriched/notion_part6_qa1.csv"
OUTPUT = "data/enriched/notion_part6_final.csv"

# === TOPIC MAPPING ===
VALID_TOPICS = {
    "politics", "society", "economy", "technology", "environment",
    "education", "culture", "philosophy", "psychology", "media",
    "international_relations", "law", "health", "daily_life"
}

TOPIC_MAP = {
    # Greek
    "πολιτική": "politics", "κοινωνία": "society", "οικονομία": "economy",
    "τεχνολογία": "technology", "περιβάλλον": "environment",
    "εκπαίδευση": "education", "πολιτισμός": "culture",
    "φιλοσοφία": "philosophy", "ψυχολογία": "psychology",
    "μέσα ενημέρωσης": "media", "δίκαιο": "law", "υγεία": "health",
    "καθημερινότητα": "daily_life", "καθημερινή ζωή": "daily_life",
    # English variants
    "daily life": "daily_life", "daily_life": "daily_life",
    "general": "society", "general use": "society",
    "work": "economy", "economics": "economy",
    "crime": "law", "military": "politics",
    "science": "education", "linguistics": "education",
    "emotions": "psychology", "emotion": "psychology",
    "relationships": "psychology", "interpersonal": "psychology",
    "mental_health": "psychology", "character & personality": "psychology",
    "cognition": "psychology", "decision_making": "psychology",
    "rhetoric": "philosophy", "argumentation": "philosophy",
    "academic_discourse": "education", "grammar": "education",
    "communication": "media", "social commentary": "media",
    "conflict": "politics", "security": "politics",
    "demographics": "society", "family": "society",
    "literature": "culture", "arts": "culture", "arts & culture": "culture",
    "history": "culture", "geography": "environment",
    "disaster": "environment", "current affairs": "media",
    "travel": "culture", "polysemy": "education",
    "everyday_expression": "daily_life", "everyday communication": "daily_life",
    "sports": "health", "hairstyle & appearance": "daily_life",
    "clothing & fashion": "daily_life", "fashion & footwear": "daily_life",
}

def normalize_topic(val):
    val = val.strip().lower()
    if val in VALID_TOPICS:
        return val
    if val in TOPIC_MAP:
        return TOPIC_MAP[val]
    # Try matching compound topics
    for key, mapped in TOPIC_MAP.items():
        if key in val:
            return mapped
    # Greek compound
    for key, mapped in {
        "πολιτικ": "politics", "κοινων": "society", "οικονομ": "economy",
        "τεχνολογ": "technology", "περιβάλλ": "environment",
        "εκπαίδ": "education", "πολιτισμ": "culture", "φιλοσοφ": "philosophy",
        "ψυχολογ": "psychology", "δίκαι": "law", "νομικ": "law", "νόμ": "law",
        "υγεί": "health", "ιατρ": "health", "αθλητ": "health",
        "καθημεριν": "daily_life", "γενικ": "society",
        "στρατ": "politics", "διπλωματ": "international_relations",
        "ναυτ": "culture", "γεωγραφ": "environment",
        "ιστορ": "culture", "λογοτεχν": "culture",
        "εργασ": "economy", "επαγγελματ": "economy",
        "μουσικ": "culture", "θρησκ": "culture", "θεολογ": "philosophy",
        "γραμματικ": "education", "γλωσσ": "education",
        "ρητορικ": "philosophy", "επιχειρ": "economy",
        "κατασκευ": "technology", "αρχιτεκτον": "culture",
        "παιδαγωγ": "education", "συναισθ": "psychology",
        "media": "media", "politic": "politics", "societ": "society",
        "econom": "economy", "technolog": "technology",
        "environ": "environment", "educat": "education",
        "cultur": "culture", "philosoph": "philosophy",
        "psycholog": "psychology", "law": "law", "health": "health",
        "emotion": "psychology", "sport": "health",
        "fashion": "daily_life", "cloth": "daily_life",
        "hair": "daily_life", "food": "daily_life",
        "reason": "philosophy", "argument": "philosophy",
        "international": "international_relations",
        "diplomat": "international_relations",
        "conflict": "politics", "security": "politics",
        "militar": "politics", "war": "politics",
        "travel": "culture", "touris": "culture",
        "literature": "culture", "arts": "culture",
        "science": "education", "linguist": "education",
        "grammar": "education", "cogni": "psychology",
        "communi": "media", "journal": "media",
    }.items():
        if key in val:
            return mapped
    return "society"  # safe default

# === REGISTER MAPPING ===
VALID_REGISTERS = {"academic", "journalistic", "neutral", "formal", "informal"}

REGISTER_MAP = {
    "ακαδημαϊκό": "academic", "ακαδημαϊκός": "academic",
    "δημοσιογραφικό": "journalistic", "δημοσιογραφικός": "journalistic",
    "ουδέτερο": "neutral", "ουδέτερος": "neutral",
    "επίσημο": "formal", "επίσημος": "formal",
    "ανεπίσημο": "informal", "ανεπίσημος": "informal",
    "colloquial": "informal", "spoken": "informal",
}

def normalize_register(val):
    val = val.strip().lower()
    if val in VALID_REGISTERS:
        return val
    if val in REGISTER_MAP:
        return REGISTER_MAP[val]
    for key, mapped in {
        "ακαδημ": "academic", "δημοσιογρ": "journalistic",
        "ουδέτ": "neutral", "επίσημ": "formal",
        "ανεπίσημ": "informal", "academ": "academic",
        "journal": "journalistic", "neutr": "neutral",
        "formal": "formal", "informal": "informal",
        "colloqui": "informal", "spoken": "informal",
    }.items():
        if key in val:
            return mapped
    return "neutral"

# === FREQUENCY MAPPING ===
VALID_FREQS = {"high", "medium", "low"}

FREQ_MAP = {
    "υψηλή": "high", "υψηλός": "high", "υψηλ": "high",
    "μεσαία": "medium", "μεσαίος": "medium", "μέτρια": "medium", "μέτρι": "medium",
    "χαμηλή": "low", "χαμηλός": "low", "χαμηλ": "low",
}

def normalize_frequency(val):
    val = val.strip().lower()
    if val in VALID_FREQS:
        return val
    if val in FREQ_MAP:
        return FREQ_MAP[val]
    for key, mapped in FREQ_MAP.items():
        if key in val:
            return mapped
    return "medium"

# === SOURCE MAPPING ===
def normalize_source(val):
    val = val.strip()
    v = val.lower()

    if "καθημεριν" in v:
        return "Καθημερινή"
    if "βήμα" in v or "βημα" in v:
        return "Το Βήμα"
    if v == "ερτ" or "ερτ" in v.split():
        return "ΕΡΤ"
    if "τα νέα" in v or "τα νεα" in v:
        return "Τα Νέα"
    if "σκαϊ" in v or "σκαι" in v or "skai" in v:
        return "ΣΚΑΪ"
    if "ναυτεμπορ" in v:
        return "Ναυτεμπορική"
    if "εφημερίδα" in v and "συντακτ" in v:
        return "Εφημερίδα Συντακτών"
    if "documento" in v:
        return "Documento"
    if "lifo" in v:
        return "Lifo"
    if "in.gr" in v:
        return "in.gr"

    # Normalize corpus/academic/etc
    if "academic" in v or "ακαδημ" in v or "επιστημ" in v:
        return "Academic article"
    if "oral" in v or "spoken" in v or "προφορικ" in v:
        return "Corpus"
    if "literary" in v or "λογοτεχν" in v or "literature" in v:
        return "Literature"
    if "corpus" in v or "γενικ" in v or "general" in v:
        return "Corpus"
    if "journal" in v or "news" in v or "δημοσιογρ" in v or "ειδησ" in v:
        return "Καθημερινή"
    if "καθημεριν" in v:
        return "Corpus"
    if "νομικ" in v or "legal" in v or "δικαστ" in v:
        return "Academic article"
    if "ιατρικ" in v or "medical" in v:
        return "Academic article"
    if "φιλοσοφ" in v or "philosoph" in v:
        return "Academic article"
    if "ψυχολογ" in v or "psycholog" in v:
        return "Academic article"
    if "κοινωνιολογ" in v or "sociol" in v:
        return "Academic article"
    if "ιστορικ" in v or "histor" in v:
        return "Academic article"
    if "παιδαγωγ" in v or "pedagog" in v or "εκπαιδευτ" in v:
        return "Academic article"
    if "πολιτικ" in v or "politic" in v or "κοινοβουλ" in v or "parliament" in v:
        return "Corpus"
    if "αθλητικ" in v or "sport" in v:
        return "Corpus"
    if "τεχνικ" in v or "techni" in v:
        return "Corpus"
    if "διοικ" in v or "admin" in v:
        return "Corpus"
    if "θεσμ" in v or "θεολογ" in v or "religio" in v:
        return "Academic article"
    if "proverb" in v or "παροιμ" in v:
        return "Corpus"
    if "λαϊκ" in v or "λαογραφ" in v or "folklore" in v:
        return "Corpus"
    if "οικονομ" in v or "financ" in v or "business" in v or "marketing" in v:
        return "Corpus"
    if "ναυτ" in v or "γεωγραφ" in v or "τουρ" in v:
        return "Corpus"
    if "μουσικ" in v or "music" in v or "theatre" in v or "θέατρ" in v:
        return "Corpus"
    if "coach" in v or "management" in v:
        return "Corpus"
    if "energy" in v or "environ" in v:
        return "Academic article"
    if "digital" in v or "media stud" in v or "media lit" in v:
        return "Academic article"

    return val  # keep as-is if can't map

COLUMNS = [
    "greek", "russian", "english", "example", "category",
    "root", "root_family", "verb_partner", "adjective_partner",
    "collocations", "example1", "example1_en", "example2", "example2_en",
    "example3", "example3_en", "synonyms", "antonyms", "mini_dialogue",
    "topic", "register", "frequency", "source", "notes"
]

def main():
    with open(INPUT, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    stats = {"topic": 0, "register": 0, "frequency": 0, "source": 0}

    for row in rows:
        if row["greek"].startswith("---"):
            continue

        # Normalize topic
        old = row["topic"]
        row["topic"] = normalize_topic(old)
        if row["topic"] != old.strip():
            stats["topic"] += 1

        # Normalize register
        old = row["register"]
        row["register"] = normalize_register(old)
        if row["register"] != old.strip():
            stats["register"] += 1

        # Normalize frequency
        old = row["frequency"]
        row["frequency"] = normalize_frequency(old)
        if row["frequency"] != old.strip():
            stats["frequency"] += 1

        # Normalize source
        old = row["source"]
        row["source"] = normalize_source(old)
        if row["source"] != old.strip():
            stats["source"] += 1

    import os
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in COLUMNS})

    data_rows = [r for r in rows if not r["greek"].startswith("---")]
    print(f"Normalized {stats['topic']} topics, {stats['register']} registers, "
          f"{stats['frequency']} frequencies, {stats['source']} sources")
    print(f"Output: {OUTPUT} ({len(data_rows)} data rows)")

if __name__ == "__main__":
    main()
