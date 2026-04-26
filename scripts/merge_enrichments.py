#!/usr/bin/env python3
"""Merge enrich_part_*.json files back into the CSV."""
import csv
import json
import glob
import os

CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "enriched", "unified_vocabulary_enriched.csv")
PARTS_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "enriched")

ENRICH_FIELDS = [
    "category", "root_family",
    "verb_partner", "adjective_partner", "collocations",
    "example1", "example1_en", "example2", "example2_en",
    "example3", "example3_en", "mini_dialogue", "notes",
]


def main():
    # Load CSV
    with open(CSV_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    # Load all parts
    part_files = sorted(glob.glob(os.path.join(PARTS_DIR, "enrich_part_*.json")))
    print(f"Found {len(part_files)} part files")

    total_applied = 0
    for pf in part_files:
        with open(pf, encoding="utf-8") as f:
            parts = json.load(f)
        applied = 0
        for entry in parts:
            idx = entry["csv_row_index"]
            data = entry["data"]
            for field in ENRICH_FIELDS:
                if rows[idx].get(field, "").strip():
                    continue
                val = data.get(field, "")
                if val:
                    rows[idx][field] = val
                    applied += 1
        print(f"  {os.path.basename(pf)}: {len(parts)} words, {applied} fields applied")
        total_applied += applied

    # Save CSV
    with open(CSV_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nTotal: {total_applied} fields applied. CSV saved.")


if __name__ == "__main__":
    main()
