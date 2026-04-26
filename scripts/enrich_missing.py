#!/usr/bin/env python3
"""
Enrich words missing examples/collocations/dialogues via Claude API.
Processes in batches of 30, writes progress after each batch.
"""
import csv
import json
import os
import time
import anthropic

CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "enriched", "unified_vocabulary_enriched.csv")
API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

ENRICH_FIELDS = [
    "category", "root_family",
    "verb_partner", "adjective_partner", "collocations",
    "example1", "example1_en", "example2", "example2_en",
    "example3", "example3_en", "mini_dialogue", "notes",
]

SYSTEM_PROMPT = """You are a Greek language expert enriching Γ2/C2 vocabulary entries.

For each word, generate ONLY a JSON object with these fields:
- category: grammatical category — one of: noun, verb, adjective, adverb, phrase, expression, conjunction, preposition, pronoun
- root_family: 2-4 cognate words sharing the same root, separated by "; " (e.g. "δίκαιος; δικαιοσύνη; δικαστήριο")
- verb_partner: typical verb + word collocation (e.g. "ασκώ πίεση")
- adjective_partner: typical adjective + word collocation (e.g. "έντονη πίεση")
- collocations: 3 natural fixed expressions separated by "; "
- example1: Greek sentence 8-15 words, using the word, journalistic/academic style
- example1_en: natural English translation
- example2: different context Greek sentence
- example2_en: English translation
- example3: third context Greek sentence
- example3_en: English translation
- mini_dialogue: format "A: ... B: ..." — short 2-line dialogue using the word
- notes: 1 brief usage tip or register note in Russian (e.g. "Часто в юридических текстах" or "Разговорный вариант — ...")

Rules:
- Modern standard Greek, academic/journalistic register
- Examples must be distinct contexts
- All fields CSV-safe (no stray commas, use ; for lists)
- If the entry is a phrase/expression, use it naturally in examples
- For verbs, show different tenses/forms in examples
- Return ONLY valid JSON array, no markdown, no explanation"""

BATCH_SIZE = 20
client = anthropic.Anthropic(api_key=API_KEY, timeout=120.0)


def load_csv():
    with open(CSV_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)
    return fieldnames, rows


def save_csv(fieldnames, rows):
    with open(CSV_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def needs_enrichment(row):
    # Missing examples (main block ~1860) OR missing category
    return not row.get("example1", "").strip() or not row.get("category", "").strip()


def enrich_batch(words_batch):
    """Send batch to Claude API, return list of enrichment dicts."""
    word_list = []
    for w in words_batch:
        word_list.append({
            "greek": w["greek"],
            "russian": w.get("russian", ""),
            "english": w.get("english", ""),
            "topic": w.get("topic", ""),
            "root": w.get("root", ""),
        })

    prompt = f"""Enrich these {len(word_list)} Greek words. Return a JSON array with {len(word_list)} objects, one per word, in the same order.

Words:
{json.dumps(word_list, ensure_ascii=False, indent=1)}

Return ONLY a valid JSON array."""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=16000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text.strip()
    # Clean markdown wrapper if present
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        text = text.strip()

    return json.loads(text)


def main():
    fieldnames, rows = load_csv()

    # Find indices needing enrichment
    to_enrich = [(i, rows[i]) for i in range(len(rows)) if needs_enrichment(rows[i])]
    total = len(to_enrich)
    print(f"Words needing enrichment: {total}")

    if total == 0:
        print("All words already enriched!")
        return

    done = 0
    for batch_start in range(0, total, BATCH_SIZE):
        batch = to_enrich[batch_start:batch_start + BATCH_SIZE]
        batch_words = [w for _, w in batch]
        batch_indices = [i for i, _ in batch]

        print(f"\nBatch {batch_start // BATCH_SIZE + 1}: words {done + 1}-{done + len(batch)} of {total}")

        try:
            enrichments = enrich_batch(batch_words)

            if len(enrichments) != len(batch):
                print(f"  WARNING: expected {len(batch)} results, got {len(enrichments)}")
                enrichments = enrichments[:len(batch)]

            for j, enrichment in enumerate(enrichments):
                idx = batch_indices[j]
                for field in ENRICH_FIELDS:
                    # Only fill empty fields — don't overwrite existing data
                    if rows[idx].get(field, "").strip():
                        continue
                    val = enrichment.get(field, "")
                    if val:
                        rows[idx][field] = val

            done += len(batch)
            print(f"  Enriched {len(enrichments)} words. Total done: {done}/{total}")

            # Save after each batch
            save_csv(fieldnames, rows)
            print(f"  Saved to CSV.")

        except json.JSONDecodeError as e:
            print(f"  ERROR parsing JSON: {e}")
            print(f"  Skipping batch, will retry on next run.")
            continue
        except Exception as e:
            print(f"  ERROR: {e}")
            print(f"  Saving progress and stopping.")
            save_csv(fieldnames, rows)
            return

        # Rate limiting
        if batch_start + BATCH_SIZE < total:
            time.sleep(2)

    print(f"\nDone! Enriched {done} words total.")


if __name__ == "__main__":
    main()
