import os
import subprocess
import sys
import pyperclip
import pywikibot
import mwparserfromhell
import unicodedata
import regex as re
import random
from collections import defaultdict

# From User:JeffDoozan's bot AutoDooz
CAT_TEMPLATES = [ "c", "C", "cat", "top", "topic", "topics", "categorize", "catlangname", "catlangcode", "cln", "zh-cat",
        "eo F", "eo [1-9]OA", "eo-categoryTOC", "eo BRO", "eo GCSE", "Universala Vortaro" ]
RE_CAT_TEMPLATES = r"\{\{\s*(" + "|".join(CAT_TEMPLATES) + r")\s*[|}][^{}]*\}*"
RE_CATEGORIES = r"\[\[\s*[cC]at(egory)?\s*:[^\]]*\]\]"
RE_MATCH_CATEGORIES = re.compile(fr"({RE_CAT_TEMPLATES}|{RE_CATEGORIES})")
SITE = pywikibot.Site("en", "wiktionary")
BACKUP_PATH = "en-anagrams-backup"
DIACRITICS = f"{chr(0x0300)}-{chr(0x036F)}"
PUNCTUATION = r"’'()\[\]{}<>:,‒–—―…!.«»\-‐?‘’“”;/⁄␠·&@*\\•^¤¢$€£¥₩₪†‡°¡¿¬#№%‰‱¶′§~¨_|¦⁂☞∴‽※" + f"{chr(0x2000)}-{chr(0x206F)}"
REDUNDANT_CHARS = f"[{DIACRITICS}{PUNCTUATION} ]"

CONVERSIONS = {
    "æ": "ae",
    "œ": "oe",
    "ı": "i",
}

def create_diff(old_text: str, current_page: pywikibot.Page) -> None:
    """
    Copy the contents of the page to local storage for backup in case there is a problem
    with the script later; this will allow the error to be automatically corrected at that time.
    """
    os.makedirs(BACKUP_PATH, exist_ok=True)
    with open("temp1", mode="w", encoding="utf-8") as f:
        f.write(old_text)

    with open("temp2", mode="w", encoding="utf-8") as f:
        f.write(current_page.text)

    diff = subprocess.getoutput("diff -u temp2 temp1") # Get differences between new revision and previous
    diff = diff + "\n" # patch will complain if we don't end the file with a newline

    with open(os.path.join(BACKUP_PATH, current_page.title()), mode="w", encoding="utf-8") as f:
        f.write(diff)

def normalise(word: str) -> str:
    """Normalises the word.
    Using the following method:
        - Remove all whitespace at the start and end.
        - Decompose all characters to their simplest, e.g. é becomes e + ACUTE
        - Convert to lowercase (casefold)
        - Remove all irrelevant elements (punctuation, diacritics).
    """
    word = word.casefold()

    for source_char, replacement in CONVERSIONS.items():
        word = word.replace(source_char, replacement)

    word = re.sub(REDUNDANT_CHARS, "", unicodedata.normalize("NFKD", word.strip()).casefold())
    return word

def get_alphagram(word: str) -> str:
    return "".join(sorted(normalise(word)))

# Calculate all anagrams from the file of words
print("Preparing anagrams from the dataset...")
with open("en_wordlist.txt") as f:
    wordlist: list[str] = f.readlines()

anagrams = defaultdict(set)

for word in wordlist:
    anagrams[get_alphagram(word)].add(word.strip())

anagrams = {letter_count: anas for letter_count, anas in anagrams.items() if len(anas) > 1} # Only keep words with multiple anagrams

# ---------------------------------------------

def count_anagrams():
    return sum(len(anagram_list) for anagram_list in anagrams.values())

def get_anagrams(word: str, alphagram: str) -> set[str]:
    return anagrams[alphagram] - {word} - {ana for ana in anagrams[alphagram] if normalise(ana) == normalise(word)}

def generate_anagrams_section(anagrams: set[str]) -> str:
    return "\n\n===Anagrams===\n* " + generate_anagrams_template(anagrams, get_alphagram(anagrams.copy().pop())) + "\n\n"

def generate_anagrams_template(anagrams: set[str], alphagram: str) -> str:
    return "{{" + f"anagrams|en|a={alphagram}|" + "|".join(anagrams) + "}}"

def get_see_also_contents(parsed: mwparserfromhell.wikicode.Wikicode) -> set[str]:
    for template in parsed.filter(forcetype=mwparserfromhell.wikicode.Template):
        template: mwparserfromhell.wikicode.Template

        if template.name == "also":
            return set(str(param) for param in template.params)

    return set()

def add_anagrams(contents: str, anagrams_to_add: set[str], alphagram):
    parsed = mwparserfromhell.parse(contents)

    anagrams_to_add.difference_update(get_see_also_contents(parsed))

    if len(anagrams_to_add) == 0:
        return contents, set()
    
    anagrams_added = anagrams_to_add.copy()

    english_section: mwparserfromhell.wikicode.Wikicode = parsed.get_sections([2], "English")[0]
    anagrams_section: mwparserfromhell.wikicode.Wikicode = english_section.get_sections([3], "Anagrams")
    if anagrams_section:
        anagrams_section = anagrams_section[0]
        anagrams_templates = anagrams_section.filter(forcetype=mwparserfromhell.wikicode.Template)
        anagrams_templates = [t for t in anagrams_templates if t.name == "anagrams"]
        if len(anagrams_templates) == 0:
            return contents, set()
    
        existing = set()
        anagrams_template = anagrams_templates[0]
        i = 2
        while anagrams_template.has(i):
            existing.add(str(anagrams_template.get(i)))
            i += 1

        if existing.union(anagrams_to_add) == existing:  # If there are no new anagrams present
            return contents, set()
        
        anagrams_to_add = anagrams_to_add.union(existing)

        anagrams_section.nodes[anagrams_section.index(anagrams_template)] = generate_anagrams_template(anagrams_to_add, alphagram)
        
        anagrams_added = anagrams_to_add.difference(existing)

    else:
        index = len(english_section.nodes)-1
        keep_going = True
        while index > 0 and keep_going:
            node_str_form = str(english_section.nodes[index])
            if not (node_str_form.isspace() or RE_MATCH_CATEGORIES.match(node_str_form)):
                keep_going = False
                index += 1  # Insert just after the content that isn't a whitespace/category
            else:
                index -= 1

        while index < len(english_section.nodes) and (node_str_form := str(english_section.nodes[index]).isspace()):
            index += 1

        english_section.insert(index, generate_anagrams_section(anagrams_to_add))

    return str(parsed), anagrams_added

def update_page(title: str, alphagram: str) -> bool:
    """Update a page with its anagrams. Returns whether changes were made."""
    page = pywikibot.Page(SITE, title)

    create_diff(page.text, page)
    
    anagrams_to_add = get_anagrams(title, alphagram)
    new_content, added_anagrams = add_anagrams(page.text, anagrams_to_add, alphagram)
    new_content = re.sub("\n{3,}", "\n\n", new_content)

    if new_content == page.text:
        print(f"Did nothing on page {title} as there are already anagrams present", file=sys.stderr)
        return False
    else:
        page.text = new_content
        plural_s = "s" if len(added_anagrams) > 1 else ""
        exist_other_sections = len(mwparserfromhell.parse(page.text).get_sections([2])) > 1
        page.save(f"Added anagram{plural_s} ({', '.join(added_anagrams)}){' to English section' if exist_other_sections else ''}", minor=False)
        return True

def main():
    try:
        LIMIT = int(pywikibot.argvu[1])
    except:
        LIMIT = -1

    print("Preparing to iterate over", len(anagrams), "alphragrams", f"({count_anagrams()} anagrams)")
    for anagram_list in anagrams.values():
        if random.randint(1, 1000) == 50:
            print(anagram_list)

    edit_count = 0  # Updated for every individual page
    iterations = 0  # Updated for every set of anagrams
    for alphagram, anas in anagrams.items():

        if iterations % 5 == 0: # Every fifth set of anagrams, consider whether to halt
            halt_page = pywikibot.Page(SITE, "User:KovachevBot/halt")
            if "halt" in halt_page.text.casefold():
                print(f"ERROR: BOT WAS MANUALLY HALTED BY {halt_page.userName()}", file=sys.stderr)
                return

        for anagram in anas:
            if edit_count == LIMIT:
                return

            edit_count += int(update_page(anagram, alphagram))  # If a change was made, increase the edit count

        iterations += 1

if __name__ == "__main__":
    main()