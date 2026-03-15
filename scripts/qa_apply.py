#!/usr/bin/env python3
"""
QA Apply script — merges QA batch corrections back into the enriched CSV.

Each qa_batch_*.py file defines a QA_CORRECTIONS dict:
  { "greek_word": { "field": "new_value", ... }, ... }

Only fields present in the correction are overwritten; others are preserved.
"""
import csv
import glob
import importlib.util
import os

CSV_PATH = "data/enriched/notion_part6_enriched.csv"
OUTPUT_PATH = "data/enriched/notion_part6_qa1.csv"

COLUMNS = [
    "greek", "russian", "english", "example", "category",
    "root", "root_family", "verb_partner", "adjective_partner",
    "collocations", "example1", "example1_en", "example2", "example2_en",
    "example3", "example3_en", "synonyms", "antonyms", "mini_dialogue",
    "topic", "register", "frequency", "source", "notes"
]

def load_corrections():
    all_corrections = {}
    files = sorted(glob.glob("scripts/qa_batch_*.py"))
    for fp in files:
        mod_name = os.path.basename(fp).replace(".py", "")
        spec = importlib.util.spec_from_file_location(mod_name, fp)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        corrections = getattr(mod, "QA_CORRECTIONS", {})
        print(f"  Loaded {len(corrections)} corrections from {os.path.basename(fp)}")
        all_corrections.update(corrections)
    return all_corrections

def main():
    corrections = load_corrections()
    print(f"\nTotal corrections loaded: {len(corrections)}")

    with open(CSV_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    corrected_count = 0
    for row in rows:
        greek = row["greek"].strip()
        if greek in corrections:
            for field, value in corrections[greek].items():
                if field in row:
                    row[field] = value
            corrected_count += 1

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in COLUMNS})

    print(f"\nCorrected {corrected_count}/{len([r for r in rows if not r['greek'].startswith('---')])} entries")
    print(f"Output: {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
