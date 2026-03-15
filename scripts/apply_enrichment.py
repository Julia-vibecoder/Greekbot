"""
Apply enrichment data to the glossary CSV.
Each enrich_full_batchN.py defines a dict ENRICHMENTS where:
  key = greek word
  value = dict with new column values

This script adds new columns to the CSV and fills them from ENRICHMENTS.
"""
import csv
import importlib.util
import sys
import os

CSV_PATH = "data/raw/notion_part6_glossary.csv"
OUTPUT_PATH = "data/enriched/notion_part6_enriched.csv"

NEW_COLUMNS = [
    "root", "root_family", "verb_partner", "adjective_partner",
    "collocations", "example1", "example1_en", "example2", "example2_en",
    "example3", "example3_en", "synonyms", "antonyms", "mini_dialogue",
    "topic", "register", "frequency", "source", "notes"
]

def load_enrichments(batch_files):
    """Load all ENRICHMENTS dicts from batch files."""
    all_enrichments = {}
    for path in batch_files:
        spec = importlib.util.spec_from_file_location("batch", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "ENRICHMENTS"):
            all_enrichments.update(mod.ENRICHMENTS)
            print(f"  Loaded {len(mod.ENRICHMENTS)} entries from {os.path.basename(path)}")
    return all_enrichments

def main():
    # Find all enrich_full_batch*.py files
    script_dir = os.path.dirname(os.path.abspath(__file__))
    batch_files = sorted([
        os.path.join(script_dir, f)
        for f in os.listdir(script_dir)
        if f.startswith("enrich_full_batch") and f.endswith(".py")
    ])

    if not batch_files:
        print("No enrich_full_batch*.py files found!")
        return

    print(f"Found {len(batch_files)} batch files:")
    enrichments = load_enrichments(batch_files)
    print(f"\nTotal enrichments loaded: {len(enrichments)}")

    # Read existing CSV
    rows = []
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        old_fieldnames = reader.fieldnames
        for row in reader:
            rows.append(row)

    # New fieldnames = old + new columns
    fieldnames = list(old_fieldnames) + [c for c in NEW_COLUMNS if c not in old_fieldnames]

    # Apply enrichments
    updated = 0
    for row in rows:
        gr = row.get("greek", "").strip()
        if gr != "---" and gr in enrichments:
            for col in NEW_COLUMNS:
                row[col] = enrichments[gr].get(col, "")
            updated += 1
        else:
            # Ensure new columns exist with empty values
            for col in NEW_COLUMNS:
                if col not in row:
                    row[col] = ""

    # Write enriched CSV
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nEnriched {updated}/{len([r for r in rows if r.get('greek','').strip() != '---'])} entries")
    print(f"Output: {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
