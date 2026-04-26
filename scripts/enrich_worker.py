#!/usr/bin/env python3
"""
Parallel enrichment worker. Processes a slice of unenriched words.
Usage: python3 enrich_worker.py <worker_id> <start_idx> <end_idx>
  - worker_id: 0-based worker number (for output file naming)
  - start_idx: start index in the unenriched list (inclusive)
  - end_idx: end index in the unenriched list (exclusive)
Writes results to data/enriched/enrich_part_{worker_id}.json
"""
import csv
import json
import os
import sys
import time
import anthropic

CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "enriched", "unified_vocabulary_enriched.csv")
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "enriched")
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

BATCH_SIZE = 10
client = anthropic.Anthropic(api_key=API_KEY, timeout=300.0, max_retries=3)


def load_unenriched():
    with open(CSV_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    unenriched = []
    for i, r in enumerate(rows):
        if r.get("greek", "").startswith("---"):
            continue
        if not r.get("example1", "").strip() or not r.get("category", "").strip():
            unenriched.append((i, r))
    return unenriched


def enrich_batch(words_batch):
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
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        text = text.strip()

    return json.loads(text)


def main():
    worker_id = int(sys.argv[1])
    start_idx = int(sys.argv[2])
    end_idx = int(sys.argv[3])

    unenriched = load_unenriched()
    my_slice = unenriched[start_idx:end_idx]
    total = len(my_slice)
    print(f"[Worker {worker_id}] Processing words {start_idx}-{end_idx} ({total} words)")

    results = []  # list of {csv_row_index, enrichment_data}
    out_file = os.path.join(OUT_DIR, f"enrich_part_{worker_id}.json")

    done = 0
    for batch_start in range(0, total, BATCH_SIZE):
        batch = my_slice[batch_start:batch_start + BATCH_SIZE]
        batch_words = [w for _, w in batch]
        batch_indices = [i for i, _ in batch]

        print(f"[Worker {worker_id}] Batch {batch_start // BATCH_SIZE + 1}: {done + 1}-{done + len(batch)} of {total}")

        try:
            enrichments = enrich_batch(batch_words)

            if len(enrichments) != len(batch):
                print(f"  WARNING: expected {len(batch)}, got {len(enrichments)}")
                enrichments = enrichments[:len(batch)]

            for j, enrichment in enumerate(enrichments):
                results.append({
                    "csv_row_index": batch_indices[j],
                    "data": enrichment,
                })

            done += len(batch)
            print(f"[Worker {worker_id}] Done: {done}/{total}")

            # Save progress after each batch
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=1)

        except json.JSONDecodeError as e:
            print(f"[Worker {worker_id}] JSON ERROR: {e} — skipping batch")
            continue
        except Exception as e:
            print(f"[Worker {worker_id}] ERROR: {e} — saving and stopping")
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=1)
            return

        if batch_start + BATCH_SIZE < total:
            time.sleep(3)

    print(f"[Worker {worker_id}] FINISHED! {done} words enriched.")


if __name__ == "__main__":
    main()
