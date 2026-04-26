#!/usr/bin/env python3
"""
Local QA fixes — no API needed.
1. Fix category: detect noun/verb/adj/etc from Greek morphology
2. Normalize register & frequency
3. Fix collocations separator (, → ;)
"""
import csv
import re

CSV_PATH = "data/enriched/unified_vocabulary_enriched.csv"

VALID_CATEGORIES = {'noun','verb','adjective','adverb','phrase','expression','conjunction','preposition','pronoun','participle','prefix','suffix','interjection'}

# Greek articles → noun
ARTICLES = {'ο', 'η', 'το', 'οι', 'τα', 'ένας', 'μια', 'μία', 'ένα'}

# Verb endings
VERB_ENDINGS = (
    'ω', 'ώ', 'ομαι', 'ούμαι', 'άμαι', 'ιέμαι', 'είμαι',
    'ώνω', 'ίζω', 'εύω', 'αίνω', 'άζω', 'ύνω',
)

# Adjective endings (masc/fem/neut patterns)
ADJ_PATTERNS = [
    r'-[ηήοό]ς?\s*-[ηή]\s*-[οό]',   # -ος -η -ο / -ός -ή -ό
    r'-[ηή]\s*-[οό]$',
]

# Adverb endings
ADVERB_ENDINGS = ('ως', 'ά', '-ως')

# Conjunctions
CONJUNCTIONS = {
    'και', 'αλλά', 'ή', 'ούτε', 'μήτε', 'είτε', 'ωστόσο', 'επομένως',
    'συνεπώς', 'δηλαδή', 'ενώ', 'αν', 'εάν', 'όταν', 'επειδή', 'αφού',
    'μολονότι', 'παρόλο', 'παρότι', 'ώστε', 'μόλις', 'πριν', 'καθώς',
    'ωσάν', 'σαν', 'διότι', 'μήπως', 'λοιπόν', 'άρα', 'τουλάχιστον',
}

# Prepositions
PREPOSITIONS = {
    'σε', 'από', 'με', 'για', 'προς', 'κατά', 'μετά', 'χωρίς',
    'μέχρι', 'μεταξύ', 'εντός', 'εκτός', 'λόγω', 'πλην', 'παρά',
    'ανά', 'υπέρ', 'αντί', 'περί', 'δίχως', 'ένεκα', 'εξαιτίας',
}

# Pronouns
PRONOUNS = {
    'εγώ', 'εσύ', 'αυτός', 'αυτή', 'αυτό', 'εμείς', 'εσείς', 'αυτοί',
    'κάποιος', 'κανείς', 'κανένας', 'τίποτα', 'τίποτε', 'κάτι', 'όλοι',
    'πολύς', 'λίγος', 'αρκετός',
}

INTERJECTIONS = {
    'μπράβο', 'μακάρι', 'ευτυχώς', 'δυστυχώς', 'ήμαρτον',
}


def detect_category(greek):
    """Detect grammatical category from Greek word/phrase morphology."""
    g = greek.strip()
    words = g.split()

    if not words:
        return ''

    # Multi-word → likely phrase/expression
    if len(words) >= 3:
        # Check if starts with article → noun phrase
        if words[0].lower() in ARTICLES:
            return 'phrase'
        # Check if first word looks like a verb
        w0 = words[0].lower()
        for end in VERB_ENDINGS:
            if w0.endswith(end):
                return 'phrase'
        return 'expression'

    # Two words
    if len(words) == 2:
        w0 = words[0].lower()
        w1 = words[1].lower()

        # article + noun
        if w0 in ARTICLES:
            return 'noun'

        # adj patterns like "δημόσιος υπάλληλος"
        # noun + noun or adj + noun → phrase
        if '/' in g:
            return 'phrase'  # e.g. "τρομοκράτης / τρομοκρατία"

        return 'phrase'

    # Single word
    word = words[0]
    wl = word.lower()

    # Check fixed sets
    if wl in CONJUNCTIONS:
        return 'conjunction'
    if wl in PREPOSITIONS:
        return 'preposition'
    if wl in PRONOUNS:
        return 'pronoun'
    if wl in INTERJECTIONS:
        return 'interjection'

    # Adjective pattern: ends with -ος/-ής/-ύς and has dash variants
    if re.search(r'-[ηήοό]ς?\s+-[ηή]\s+-[οό]', g):
        return 'adjective'
    # Like "βολετός -ή -ό"
    if re.search(r'[οό]ς\s+-[ηή]\s+-[οό]', g):
        return 'adjective'

    # Verb: ends in common verb suffixes
    for end in VERB_ENDINGS:
        if wl.endswith(end) and len(wl) > len(end) + 1:
            return 'verb'

    # Participle: -μένος/-μένη/-μένο, -ών/-ούσα
    if wl.endswith(('μένος', 'μένη', 'μένο', 'μένα')):
        return 'participle'

    # Adjective: -ος/-ης/-ικός/-ινός/-αίος/-ώδης etc.
    adj_suffixes = ('ικός', 'ικός', 'ινός', 'αίος', 'ώδης', 'ωτός', 'ιμος',
                    'ερός', 'ηρός', 'ικά', 'τικός', 'λογικός', 'σιμος',
                    'ικόs', 'ύς', 'ής')
    for suf in adj_suffixes:
        if wl.endswith(suf):
            return 'adjective'

    # Adverb: -ως, -ά (but careful)
    if wl.endswith('ως') and len(wl) > 3:
        return 'adverb'

    # Noun: most remaining single Greek words
    # Common noun endings
    noun_suffixes = ('ση', 'ξη', 'ψη', 'ία', 'εία', 'ότητα', 'σύνη',
                     'ισμός', 'ιστής', 'ίστρια', 'ας', 'ης', 'ος',
                     'ήρας', 'ητας', 'ιον', 'μα', 'ημα', 'ιμο', 'ούρα',
                     'αλο', 'έας', 'ιά', 'ιό', 'εύς', 'ώνας', 'ίδα',
                     'ούλα', 'ούδι', 'άκι', 'ίτσα', 'ι', 'ο', 'α', 'η')
    for suf in noun_suffixes:
        if wl.endswith(suf) and len(wl) > len(suf) + 1:
            return 'noun'

    return 'noun'  # default for single Greek word


# Register normalization
REGISTER_MAP = {
    'scientific': 'academic',
    'archaic': 'formal',
    'literary': 'formal',
    'colloquial': 'informal',
    'spoken': 'informal',
    'technical': 'academic',
}

# Frequency normalization
FREQ_MAP = {
    'very low': 'low',
    'rare': 'low',
    'uncommon': 'low',
    'common': 'high',
    'very high': 'high',
    'moderate': 'medium',
}


def main():
    with open(CSV_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    stats = {'category_fixed': 0, 'register_fixed': 0, 'freq_fixed': 0, 'colloc_fixed': 0}

    for row in rows:
        if row['greek'].startswith('---'):
            continue

        # 1. Fix category
        cat = row.get('category', '').strip().lower()
        if cat not in VALID_CATEGORIES:
            new_cat = detect_category(row['greek'])
            if new_cat:
                row['category'] = new_cat
                stats['category_fixed'] += 1

        # 2. Normalize register
        reg = row.get('register', '').strip().lower()
        if reg in REGISTER_MAP:
            row['register'] = REGISTER_MAP[reg]
            stats['register_fixed'] += 1

        # 3. Normalize frequency
        freq = row.get('frequency', '').strip().lower()
        if freq in FREQ_MAP:
            row['frequency'] = FREQ_MAP[freq]
            stats['freq_fixed'] += 1

        # 4. Fix collocations separator
        coll = row.get('collocations', '').strip()
        if coll and ';' not in coll and ',' in coll and len(coll.split(',')) > 2:
            row['collocations'] = coll.replace(', ', '; ').replace(',', '; ')
            stats['colloc_fixed'] += 1

    # Save
    with open(CSV_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"=== QA Fixes Applied ===")
    print(f"  category fixed:     {stats['category_fixed']}")
    print(f"  register fixed:     {stats['register_fixed']}")
    print(f"  frequency fixed:    {stats['freq_fixed']}")
    print(f"  collocations fixed: {stats['colloc_fixed']}")

    # Verify
    with open(CSV_PATH, encoding="utf-8") as f:
        rows2 = [r for r in csv.DictReader(f) if not r.get('greek','').startswith('---')]

    valid_cat = sum(1 for r in rows2 if r.get('category','').strip().lower() in VALID_CATEGORIES)
    valid_reg = sum(1 for r in rows2 if r.get('register','').strip().lower() in {'academic','journalistic','neutral','formal','informal'})
    valid_freq = sum(1 for r in rows2 if r.get('frequency','').strip().lower() in {'high','medium','low'})
    total = len(rows2)
    print(f"\n=== After Fix ===")
    print(f"  valid category:  {valid_cat}/{total} ({valid_cat/total*100:.1f}%)")
    print(f"  valid register:  {valid_reg}/{total} ({valid_reg/total*100:.1f}%)")
    print(f"  valid frequency: {valid_freq}/{total} ({valid_freq/total*100:.1f}%)")


if __name__ == "__main__":
    main()
