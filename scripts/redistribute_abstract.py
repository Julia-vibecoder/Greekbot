#!/usr/bin/env python3
"""
Redistribute entries from "Абстрактные понятия" into more specific themes
using expanded keyword matching. Keeps cognate groups together.
"""

import csv
import io
import sys
from collections import defaultdict

CSV_PATH = "/Users/jshestova/Desktop/Greek-bot-workshop/data/raw/notion_part6_glossary.csv"

# ─── Keyword rules per theme ───────────────────────────────────────────────────
THEME_KEYWORDS = {
    "Политика и общество": {
        "ru": ["власть", "государств", "правительств", "полити", "демократ", "парламент",
               "партия", "выбор", "голосов", "гражданск", "конституц", "закон", "реформ",
               "революци", "протест", "оппозици", "режим", "диктат", "тирани", "общество",
               "социальн", "населен", "народ", "нац", "патриот", "либерал", "консерват",
               "идеолог", "пропаганд", "цензур", "санкци", "дипломат", "геополитик",
               "суверенитет", "федерац", "монарх", "республик", "правлен", "управлен",
               "автоном", "независимост", "колон", "империал", "угнетен", "освобожден",
               "преобладать", "доминир", "влияни", "мобилиз", "стратег", "систем",
               "кризис", "конфликт", "напряжен", "эскалац", "обострен", "сплочённост",
               "легитим", "рационал", "коллектив"],
        "en": ["politic", "govern", "democra", "parliament", "party", "elect", "vote",
               "citizen", "constitution", "law", "reform", "revolution", "protest",
               "opposition", "regime", "dictator", "tyrant", "society", "social", "nation",
               "patriot", "liberal", "conservative", "ideology", "propaganda", "censor",
               "sanction", "diplomat", "geopolitic", "sovereign", "federal", "monarch",
               "republic", "rule", "administr", "autonom", "independen", "colon", "imperial",
               "oppress", "liberat", "prevail", "dominat", "mobiliz", "strateg", "system",
               "crisis", "conflict", "tension", "escalat", "cohesion", "legitim", "rational",
               "collective"],
    },
    "Право и закон": {
        "ru": ["суд", "прав", "закон", "преступ", "наказан", "полиц", "арест", "задержан",
               "обвин", "приговор", "адвокат", "нарушен", "конфиск", "шантаж", "кража",
               "взлом", "улик", "свидетел", "жертв", "виновн", "невиновн", "запрет",
               "штраф", "тюрьм", "ограничен", "запрещ"],
        "en": ["court", "law", "legal", "crime", "punish", "police", "arrest", "detain",
               "accus", "sentenc", "lawyer", "violat", "confiscat", "blackmail", "theft",
               "burglar", "evidence", "witness", "victim", "guilty", "innocent", "prohibit",
               "fine", "prison", "restrict", "forbid"],
    },
    "Экономика и финансы": {
        "ru": ["деньг", "финанс", "банк", "экономик", "торговл", "инвестиц", "акци",
               "рынок", "валют", "бюджет", "налог", "долг", "кредит", "прибыл", "убыт",
               "оплат", "стоимост", "расход", "доход", "вклад", "зарплат", "депозит",
               "предоплат", "компенсац", "обеспечива"],
        "en": ["money", "financ", "bank", "econom", "trade", "invest", "stock", "market",
               "currency", "budget", "tax", "debt", "credit", "profit", "loss", "payment",
               "cost", "expens", "income", "deposit", "salary", "compensat", "ensure",
               "guarantee"],
    },
    "Работа и карьера": {
        "ru": ["работ", "карьер", "профессион", "должност", "компани", "фирм", "руковод",
               "директор", "начальник", "подчинён", "зарплат", "увольнен", "наём",
               "собеседован", "резюме", "повышен", "коллег", "офис", "бизнес", "предприят",
               "администр", "управлен", "менеджер", "сотрудник", "персонал", "квалифиц",
               "оценива", "обратная связь", "выполнен"],
        "en": ["work", "career", "profession", "job", "position", "company", "firm", "manag",
               "director", "boss", "subordin", "salary", "dismiss", "hire", "interview",
               "resume", "promot", "colleague", "office", "business", "enterprise", "administr",
               "employ", "staff", "qualif", "evaluat", "feedback", "execut", "perform"],
    },
    "Образование": {
        "ru": ["образован", "школ", "универсиет", "учеб", "экзамен", "студент", "учител",
               "преподаватель", "урок", "курс", "диплом", "степен", "знани", "обучен",
               "грамот", "исследован"],
        "en": ["educat", "school", "universit", "study", "exam", "student", "teach",
               "professor", "lesson", "course", "diploma", "degree", "knowledge", "learn",
               "literat", "research"],
    },
    "Медицина и здоровье": {
        "ru": ["болезн", "здоров", "лечен", "врач", "больниц", "лекарств", "симптом",
               "диагноз", "операци", "терап", "пациент", "медиц", "заболеван", "вирус",
               "инфекци", "имунитет", "боль", "ран", "травм", "психоз", "расстройств",
               "зависим", "суицид", "самоубийств"],
        "en": ["disease", "health", "treat", "doctor", "hospital", "medic", "symptom",
               "diagnos", "surgery", "therap", "patient", "illness", "virus", "infect",
               "immun", "pain", "wound", "injur", "psychos", "disorder", "addict", "suicid"],
    },
    "Психология и эмоции": {
        "ru": ["чувств", "эмоци", "настроен", "счасть", "грусть", "радост", "страх",
               "тревог", "гнев", "любов", "ненавист", "разочарован", "удивлен", "стыд",
               "вин", "сочувстви", "сопережива", "доверие", "подозрен", "ревност", "зависть",
               "гордост", "одиночеств", "скук", "усталост", "раздраж", "обид", "стресс",
               "депресс", "утешен", "печал", "восторг", "волнен", "беспокойств", "смущен",
               "неловк", "наив", "разочаров", "впечатлен", "мурашк", "шок", "паник",
               "истощ", "напряг", "растерян"],
        "en": ["feel", "emotion", "mood", "happy", "sad", "joy", "fear", "anxiety", "anger",
               "love", "hate", "disappoint", "surpris", "shame", "guilt", "sympathy",
               "empathy", "trust", "suspicion", "jealous", "envy", "pride", "loneli", "bore",
               "tired", "irritat", "offend", "stress", "depress", "consol", "sorrow",
               "delight", "excit", "worry", "embarrass", "naive", "impress", "chill",
               "shock", "panic", "exhaust", "tense", "confus"],
    },
    "Семья и отношения": {
        "ru": ["семь", "брак", "свадьб", "развод", "родител", "ребён", "дет", "сын",
               "дочь", "муж", "жен", "супруг", "пар", "отношен", "рождени", "усыновлен",
               "опек", "поколени", "наследник", "несовершеннолетн", "совершеннолетн",
               "партнёр", "сожител"],
        "en": ["family", "marriage", "wedding", "divorce", "parent", "child", "son",
               "daughter", "husband", "wife", "spouse", "couple", "relationship", "birth",
               "adopt", "guardian", "generation", "heir", "minor", "adult", "partner", "cohabit"],
    },
    "Быт и повседневность": {
        "ru": ["дом", "кухн", "уборк", "стирк", "готов", "магазин", "покупк", "расписан",
               "привычк", "распоряд", "повседневн", "бытов", "мебел", "посуд", "техник",
               "ремонт", "перееж", "перестанов", "порядок", "чист", "грязн", "ключ",
               "замок", "дверь", "окно", "этаж", "комнат", "квартир", "сосед", "жиль", "аренд"],
        "en": ["home", "house", "kitchen", "clean", "wash", "cook", "shop", "buy", "schedul",
               "habit", "routine", "daily", "domestic", "furniture", "dish", "repair", "move",
               "order", "tidy", "dirty", "key", "lock", "door", "window", "floor", "room",
               "apartment", "neighbor", "rent"],
    },
    "Природа и окружающая среда": {
        "ru": ["природ", "окружающ", "клим", "погод", "дожд", "солнц", "ветер", "снег",
               "дерев", "цветок", "растени", "животн", "лес", "мор", "гор", "река", "озер",
               "экологи", "загрязнен", "засух", "наводнен", "землетрясен", "извержен",
               "пожар", "ураган", "шторм", "стихийн"],
        "en": ["nature", "environment", "climat", "weather", "rain", "sun", "wind", "snow",
               "tree", "flower", "plant", "animal", "forest", "sea", "mountain", "river",
               "lake", "ecology", "pollut", "drought", "flood", "earthquake", "erupt", "fire",
               "hurricane", "storm", "natural disaster"],
    },
    "Культура и искусство": {
        "ru": ["искусств", "музык", "кино", "фильм", "театр", "литератур", "книг", "роман",
               "стих", "поэзи", "художник", "картин", "скульптур", "музей", "выставк",
               "концерт", "фестивал", "традици", "обычай", "танц", "архитектур", "наследи"],
        "en": ["art", "music", "cinem", "film", "theat", "literat", "book", "novel", "poem",
               "poetry", "painter", "paint", "sculpt", "museum", "exhibit", "concert",
               "festival", "tradition", "custom", "danc", "architect", "heritage"],
    },
    "Язык и коммуникация": {
        "ru": ["язык", "слов", "речь", "говор", "перевод", "значен", "выражен", "фраз",
               "грамматик", "предлог", "союз", "глагол", "существительн", "прилагательн",
               "синоним", "антоним", "метафор", "идиом", "произношен", "написан", "чтен",
               "текст", "формулир", "переформулир", "артикулир", "структурир", "рукопис",
               "ясност", "объяснен", "пояснен", "коммуникаци", "общен"],
        "en": ["language", "word", "speech", "speak", "translat", "meaning", "express",
               "phrase", "grammar", "preposition", "conjunction", "verb", "noun", "adjective",
               "synonym", "antonym", "metaphor", "idiom", "pronunc", "writ", "read", "text",
               "formulat", "rephras", "articulat", "structur", "manuscript", "clarity",
               "explain", "communic"],
    },
    "Религия и философия": {
        "ru": ["религи", "бог", "церков", "молитв", "вер", "свят", "грех", "душ", "дух",
               "философ", "мораль", "этик", "ценност", "добродетел", "порок", "смысл жизн",
               "судьб", "предназначен", "исповед"],
        "en": ["relig", "god", "church", "pray", "faith", "holy", "saint", "sin", "soul",
               "spirit", "philosoph", "moral", "ethic", "value", "virtue", "vice",
               "meaning of life", "fate", "destin", "confess"],
    },
    "Военное дело": {
        "ru": ["военн", "арми", "солдат", "оружи", "боевой", "война", "сражен", "атак",
               "оборон", "генерал", "офицер", "штаб", "стратеги"],
        "en": ["militar", "army", "soldier", "weapon", "combat", "war", "battle", "attack",
               "defen", "general", "officer", "headquarter", "strateg"],
    },
    "География и путешествия": {
        "ru": ["путешеств", "поездк", "туризм", "маршрут", "границ", "виз", "паспорт",
               "рейс", "самолёт", "перелёт", "континент", "страна", "остров", "полуостров",
               "мыс", "побережь"],
        "en": ["travel", "trip", "tourism", "route", "border", "visa", "passport", "flight",
               "airplane", "continent", "country", "island", "peninsula", "cape", "coast"],
    },
    "Спорт и тело": {
        "ru": ["спорт", "тренировк", "упражнен", "бег", "плаван", "мяч", "команд",
               "соревнован", "чемпионат", "марафон", "бокс", "прыж", "тел", "мышц",
               "гантел", "штанг"],
        "en": ["sport", "train", "exercis", "run", "swim", "ball", "team", "competi",
               "champion", "marathon", "box", "jump", "body", "muscl", "dumbbell", "barbell"],
    },
    "Строительство и жильё": {
        "ru": ["строительств", "здани", "дом", "фундамент", "стен", "крыш", "потолок",
               "пол", "кирпич", "бетон", "архитектур", "недвижимост", "покупк дом",
               "участок", "стоянк", "бассейн", "ремонт", "реконструкц", "реставрац",
               "перестройк", "устройств", "оборудован", "сборн"],
        "en": ["construct", "build", "house", "foundation", "wall", "roof", "ceiling",
               "floor", "brick", "concrete", "architect", "real estate", "property", "plot",
               "parking", "pool", "repair", "reconstruct", "restor", "renovate", "device",
               "equipment", "prefab"],
    },
    "Технологии": {
        "ru": ["технолог", "компьютер", "программ", "интернет", "приложен", "цифров",
               "данн", "сервер", "сайт", "устройств", "интерфейс", "пользователь", "сеть"],
        "en": ["technolog", "computer", "program", "internet", "app", "digital", "data",
               "server", "website", "device", "interface", "user", "network"],
    },
    "Еда и напитки": {
        "ru": ["еда", "пищ", "продукт", "блюд", "рецепт", "ресторан", "кафе", "повар",
               "вкус", "приправ", "мяс", "рыб", "овощ", "фрукт", "хлеб", "напиток",
               "вино", "пиво", "кофе", "чай", "гурман", "духовк", "кастрюл", "сковород",
               "утварь", "ингредиент", "желудок", "пищеварен"],
        "en": ["food", "meal", "product", "dish", "recipe", "restaurant", "cafe", "cook",
               "taste", "season", "meat", "fish", "vegetable", "fruit", "bread", "drink",
               "wine", "beer", "coffee", "tea", "gourmet", "oven", "pot", "pan", "utensil",
               "ingredient", "stomach", "gastr", "digest"],
    },
    "Одежда и внешность": {
        "ru": ["одежд", "платье", "костюм", "обувь", "туфл", "шляп", "парикмахер",
               "стрижк", "причёск", "макияж", "украшен", "мод", "стиль", "внешност",
               "красив", "элегантн", "красить", "сушить", "ткань", "ткать", "портн",
               "шить", "каблук", "чёлк"],
        "en": ["cloth", "dress", "suit", "shoe", "hat", "hairdress", "haircut", "hairstyl",
               "makeup", "jewel", "fashion", "style", "appear", "beauti", "elegant", "paint",
               "dye", "dry", "fabric", "weave", "tailor", "sew", "heel", "bangs", "fringe"],
    },
    "Морское дело": {
        "ru": ["мор", "корабль", "лодк", "парус", "яхт", "порт", "причал", "плыть",
               "навигац", "шторм", "якорь", "капитан", "матрос", "палуб"],
        "en": ["sea", "ship", "boat", "sail", "yacht", "port", "dock", "navigat", "storm",
               "anchor", "captain", "sailor", "deck"],
    },
}

# Keywords for the new theme "Действия и процессы"
# General action/process verbs that don't belong to specific domains
ACTIONS_KEYWORDS_RU = [
    "начинать", "начина", "продолжа", "заканчива", "менять", "измен", "создава",
    "создан", "уничтож", "разруш", "появля", "исчеза", "увеличива", "уменьша",
    "улучша", "ухудша", "ускоря", "замедля", "усилива", "ослабля", "расширя",
    "сужа", "углубля", "повтор", "прекраща", "возобновля", "приостанавлива",
    "восстанавлива", "преобразов", "превраща", "переход", "завершa", "завершен",
    "возникнов", "прерыва", "продолжен", "начало", "окончан", "развива",
    "формирова", "становить", "происходи", "осуществля", "реализов",
    "приводить", "вызыва", "порожда", "способствова", "содействова",
    "препятствова", "предотвраща", "избега", "устраня", "ликвидир",
    "подавля", "сдержива", "ограничива", "допуска", "обеспечива",
]
ACTIONS_KEYWORDS_EN = [
    "begin", "start", "continu", "finish", "end", "chang", "creat", "destroy",
    "appear", "disappear", "increas", "decreas", "improv", "worsen", "accelerat",
    "slow", "strengthen", "weaken", "expand", "narrow", "deepen", "repeat",
    "stop", "resum", "suspend", "restor", "transform", "convert", "transit",
    "complet", "emerg", "interrupt", "develop", "form", "becom", "occur",
    "implement", "realiz", "caus", "generat", "contribut", "facilitat",
    "prevent", "avoid", "eliminat", "suppress", "restrain", "limit", "allow",
]


def read_csv_file(path):
    """Read the CSV file and return all rows as a list of dicts."""
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    reader = csv.reader(io.StringIO(content))
    header = next(reader)
    rows = []
    for row in reader:
        # Pad short rows
        while len(row) < len(header):
            row.append("")
        rows.append(dict(zip(header, row)))
    return header, rows


def parse_themes(rows):
    """
    Parse rows into ordered list of (theme_name, [entry_rows]).
    Separator rows have greek='---' and russian=theme_name.
    """
    themes = []
    current_theme = None
    current_entries = []
    for row in rows:
        if row["greek"] == "---":
            if current_theme is not None:
                themes.append((current_theme, current_entries))
            current_theme = row["russian"]
            current_entries = []
        else:
            current_entries.append(row)
    # Last theme
    if current_theme is not None:
        themes.append((current_theme, current_entries))
    return themes


def matches_keywords(row, keywords_ru, keywords_en):
    """Check if a row matches any keyword in russian or english columns."""
    ru = row.get("russian", "").lower()
    en = row.get("english", "").lower()
    for kw in keywords_ru:
        if kw.lower() in ru:
            return True
    for kw in keywords_en:
        if kw.lower() in en:
            return True
    return False


def classify_entry(row):
    """
    Try to classify a single entry into a specific theme.
    Returns theme name or None if it should stay in Абстрактные понятия.
    """
    # Check each theme's keywords
    for theme, kws in THEME_KEYWORDS.items():
        if matches_keywords(row, kws["ru"], kws["en"]):
            return theme

    # Check "Действия и процессы"
    if matches_keywords(row, ACTIONS_KEYWORDS_RU, ACTIONS_KEYWORDS_EN):
        return "Действия и процессы"

    return None


def build_cognate_groups(entries):
    """
    Build cognate groups from consecutive entries.
    Cognate groups are sequences of entries that share root patterns.
    We group entries by looking at consecutive entries — in this CSV,
    cognates are placed next to each other.

    We use a simple heuristic: entries are in the same cognate group if they
    share a common Greek root prefix (first 4+ chars) with the previous entry.
    """
    if not entries:
        return []

    groups = []
    current_group = [entries[0]]

    for i in range(1, len(entries)):
        prev = entries[i - 1]
        curr = entries[i]
        if _are_cognates(prev, curr):
            current_group.append(curr)
        else:
            groups.append(current_group)
            current_group = [curr]
    groups.append(current_group)
    return groups


def _are_cognates(row1, row2):
    """
    Heuristic: two entries are cognates if they share a Greek root prefix.
    We look at the first word's first N characters.
    """
    g1 = _greek_root(row1["greek"])
    g2 = _greek_root(row2["greek"])

    if not g1 or not g2:
        return False

    # Check if they share at least 4 characters of root
    min_len = min(len(g1), len(g2))
    if min_len < 3:
        return False

    prefix_len = min(4, min_len)
    return g1[:prefix_len] == g2[:prefix_len]


def _greek_root(greek_text):
    """Extract the first word's lowercase form, stripping articles."""
    greek_text = greek_text.strip().lower()
    # Remove common Greek articles
    for art in ["η ", "ο ", "το ", "τα ", "οι ", "τον ", "την ", "τους ", "τις "]:
        if greek_text.startswith(art):
            greek_text = greek_text[len(art):]
            break
    # Take first word
    first_word = greek_text.split()[0] if greek_text.split() else ""
    return first_word


def classify_group(group):
    """
    Classify a cognate group. Use majority vote among entries that match a theme.
    If no entry matches, return None.
    """
    votes = defaultdict(int)
    for entry in group:
        theme = classify_entry(entry)
        if theme:
            votes[theme] += 1

    if not votes:
        return None

    # Return the theme with most votes
    return max(votes, key=votes.get)


def main():
    print("Reading CSV file...")
    header, rows = read_csv_file(CSV_PATH)

    print("Parsing themes...")
    themes = parse_themes(rows)

    # Build theme dict for easy access
    theme_dict = {name: entries for name, entries in themes}
    theme_order = [name for name, _ in themes]

    # Record before stats
    before_stats = {name: len(entries) for name, entries in themes}

    print(f"\nFound {len(themes)} themes, {sum(before_stats.values())} total entries")
    print(f"'Абстрактные понятия' has {before_stats.get('Абстрактные понятия', 0)} entries\n")

    # Get abstract entries
    abstract_entries = theme_dict.get("Абстрактные понятия", [])
    if not abstract_entries:
        print("No 'Абстрактные понятия' section found!")
        return

    # Build cognate groups from abstract entries
    groups = build_cognate_groups(abstract_entries)
    print(f"Found {len(groups)} cognate groups in 'Абстрактные понятия'\n")

    # Classify each group
    redistributed = defaultdict(list)  # theme -> [entries]
    remaining = []  # entries staying in Абстрактные понятия

    for group in groups:
        target_theme = classify_group(group)
        if target_theme:
            redistributed[target_theme].extend(group)
        else:
            remaining.extend(group)

    # Update theme_dict
    theme_dict["Абстрактные понятия"] = remaining

    # Add redistributed entries to their target themes
    for theme, entries in redistributed.items():
        if theme in theme_dict:
            theme_dict[theme].extend(entries)
        else:
            # New theme (e.g., "Действия и процессы")
            theme_dict[theme] = entries
            # Insert before "Абстрактные понятия" in theme_order
            idx = theme_order.index("Абстрактные понятия")
            theme_order.insert(idx, theme)

    # Verify no entries lost
    total_after = sum(len(entries) for entries in theme_dict.values())
    total_before = sum(before_stats.values())
    assert total_after == total_before, \
        f"Entry count mismatch! Before: {total_before}, After: {total_after}"

    # Build after stats
    after_stats = {name: len(theme_dict[name]) for name in theme_order}

    # Print statistics
    print("=" * 70)
    print(f"{'Theme':<40} {'Before':>8} {'After':>8} {'Diff':>8}")
    print("=" * 70)
    all_themes = set(list(before_stats.keys()) + list(after_stats.keys()))
    for theme in theme_order:
        b = before_stats.get(theme, 0)
        a = after_stats.get(theme, 0)
        diff = a - b
        diff_str = f"+{diff}" if diff > 0 else str(diff)
        marker = " *" if diff != 0 else ""
        print(f"{theme:<40} {b:>8} {a:>8} {diff_str:>8}{marker}")
    print("=" * 70)
    print(f"{'TOTAL':<40} {total_before:>8} {total_after:>8}")

    moved_count = sum(len(entries) for entries in redistributed.values())
    print(f"\nMoved {moved_count} entries out of 'Абстрактные понятия'")
    print(f"Remaining in 'Абстрактные понятия': {len(remaining)}")

    # Rebuild CSV
    print("\nWriting updated CSV...")
    with open(CSV_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for theme_name in theme_order:
            # Write separator row
            sep = ["---", theme_name] + [""] * (len(header) - 2)
            writer.writerow(sep)
            # Write entries
            for entry in theme_dict[theme_name]:
                writer.writerow([entry.get(col, "") for col in header])

    print("Done! CSV file updated successfully.")


if __name__ == "__main__":
    main()
