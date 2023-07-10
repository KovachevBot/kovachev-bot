import regex as re
from os.path import expanduser

DJR_DATA_FILE = expanduser("~/Downloads/（三省堂）スーパー大辞林［3.0］/term_bank_1.json") # Replace with your path to the DJR JSON data
ACCENT_LIST_REGEX = re.compile(r"(?:\[\d{1,2}\])+")

class ItemNotFoundError(ValueError):
    """Error when looking up an item in Daijirin; the item was not found."""

class NoAccentError(ValueError):
    """Error when trying to find the accent of a term: the entry defines no accent. No accent exists in the data."""


# NOTICE: requires 3GB+ RAM at runtime.
# Be cautious if your system does not currently have sufficient available memory.
with open(DJR_DATA_FILE) as f:
    DAIJIRIN = eval(f.read())

def is_kana(s: str) -> bool:
    HIRAGANA_START = '\u3040'
    HIRAGANA_END = '\u309f'
    KATAKANA_START = '\u30a0'
    KATAKANA_END = '\u30ff'
    return all((HIRAGANA_START <= char <= HIRAGANA_END) or (KATAKANA_START <= char <= KATAKANA_END) for char in s)

def validate_headword_and_kana(main_headword: str = None, kana: str = None) -> tuple[str, str]:
    """
    If the kana parameter is not specified for a term containing non-kana characters (i.e. kanji), raises an error;
    if the `main_headword` parameter is not specified, but `kana` is, then the term is kana-only, and so `main_headword`
    is updated to match the `kana` parameter's value. Returns the 2-tuple containing post-processed (`main_headword`, `kana`). 
    """
    if kana is not None and main_headword is None:
        main_headword = kana
    elif kana is None:
        raise ValueError("Must specify kana parameter")

    return main_headword, kana

def are_duplicate_kanas(list_of_kana_readings: list[str]) -> bool:
    """Illustrative input:
        `headword`=人, `list_of_kana_readings`=["ひと", "にん", "じん"]
        This will return `False` because there is no term where there are two identical kanas
    """
    # Sets contain unique items only, so if there are duplicates, the set will have fewer elements than the list.
    # If there're no duplicates, then, we expect their lengths to be the same.
    return len(set(list_of_kana_readings)) < len(list_of_kana_readings)

def find_entry(*, main_headword: str = None, kana: str = None) -> list:
    """
    Finds the record in the dictionary data file corresponding to the input `main_headword` (usually kanji)
    and `kana` (if the term is kana-only, only `kana` needs to be specified; otherwise, both need to be specified.)
    If nothing is found, raises an error.
    """
    main_headword, kana = validate_headword_and_kana(main_headword, kana)

    def entry_matches(entry: list) -> bool:
        if is_kana(main_headword):
            return entry[0] == main_headword
        return entry[0] == main_headword and entry[1] == kana

    for item in DAIJIRIN:
        if entry_matches(item):
            return item

    # If nothing is found, return empty list
    return []

def get_body(entry: list) -> str:
    # Although the 5th element of an entry in our format is a list,
    # every single entry in the dictionary only has 1 item in that list, which
    # is the body of the entry (the definition, pitch accent information are both in there.).
    return entry[5][0]

def get_accent_from_body(entry_body: str) -> tuple[bool, str]:
    """
    From an entry body, returns both whether there is a pitch accent defined, and the string representing
    all the possible pitch accents in a row (e.g. [1][0], [4][3], etc.)
    """
    match = ACCENT_LIST_REGEX.search(entry_body)
    return bool(match), match.group(0) if bool(match) else ""

def process_djr_accents(acc_str: str) -> list[str]:
    """Return list of accents from a string like [1][0]."""
    accs = []
    current = ""
    for char in acc_str:
        if char == "[":
            pass
        elif char == "]":
            accs.append(current)
            current = ""
        else:
            current += char
    return accs

def get_accent(*, main_headword: str = None, kana: str = None) -> list[str]:
    """
    Return a list of possible accents for a headword-kana combination. Must pass parameters as keywords to avoid confusion.
    If there is no accent available, raises a `NoAccentError`.
    """
    main_headword, kana = validate_headword_and_kana(main_headword, kana)
    entry = find_entry(main_headword=main_headword, kana=kana)
    if entry == []: return []
    entry_body = get_body(entry)
    has_accent, accents_raw = get_accent_from_body(entry_body)
    if has_accent:
        possible_accents = process_djr_accents(accents_raw)
        return possible_accents
    else:
        raise NoAccentError(f"Term {main_headword}({kana}) has no accent in Daijirin.")
