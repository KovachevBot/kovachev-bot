import os
import subprocess
import sys
import pywikibot
import mwparserfromhell
import regex as re
from collections import defaultdict

# From User:JeffDoozan's bot AutoDooz
CAT_TEMPLATES = [ "c", "C", "cat", "top", "topic", "topics", "categorize", "catlangname", "catlangcode", "cln", "zh-cat",
        "eo F", "eo [1-9]OA", "eo-categoryTOC", "eo BRO", "eo GCSE", "Universala Vortaro" ]
RE_CAT_TEMPLATES = r"\{\{\s*(" + "|".join(CAT_TEMPLATES) + r")\s*[|}][^{}]*\}*"
RE_CATEGORIES = r"\[\[\s*[cC]at(egory)?\s*:[^\]]*\]\]"
RE_MATCH_CATEGORIES = re.compile(fr"({RE_CAT_TEMPLATES}|{RE_CATEGORIES})")
SITE = pywikibot.Site("en", "wiktionary")
BACKUP_PATH = "bg-anagrams-backup"
ALPHABET = "абвгдежзийклмнопрстуфхцчшщъьюя"
NUMERIC = "0123456789"
NON_ALPHANUMERIC = f"[^{ALPHABET}{NUMERIC}]"
NOT_CREATED_LOG = "non_existent_anagrams.txt"

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
    return re.sub(NON_ALPHANUMERIC, "", re.sub("ѝ", "и", word.casefold()))
    # return re.sub("[-.;:?!‒–—]", "", re.sub("\s", "", word.casefold()))

def get_alphagram(word: str) -> str:
    return "".join(sorted(normalise(word)))

def has_bulgarian(page: pywikibot.Page) -> bool:
    return bool(mwparserfromhell.parse(page.text).get_sections([2], "Bulgarian"))


# Calculate all anagrams from the file of words
with open("words.txt") as f:
    wordlist: list[str] = f.readlines()

anagrams = defaultdict(set)

for word in wordlist:
    anagrams[get_alphagram(word)].add(word.strip())

# ---------------------------------------------

anagrams = {letter_count: anas for letter_count, anas in anagrams.items() if len(anas) > 1} # Only keep words with multiple anagrams

def count_anagrams():
    return sum(len(anagram_list) for anagram_list in anagrams.values())

def generate_anagrams_section(anagrams: set[str]) -> str:
    return "\n\n===Anagrams===\n* " + generate_anagrams_template(anagrams, get_alphagram(anagrams.copy().pop())) + "\n\n"

def generate_anagrams_template(anagrams: set[str], alphagram: str) -> str:
    return "{{" + f"anagrams|bg|a={alphagram}|" + "|".join(anagrams) + "}}"

def add_anagrams(contents: str, anagrams_to_add: set[str], alphagram):
    parsed = mwparserfromhell.parse(contents)

    anagrams_added = anagrams_to_add.copy()

    bulgarian_section: mwparserfromhell.wikicode.Wikicode = parsed.get_sections([2], "Bulgarian")[0]
    anagrams_section: mwparserfromhell.wikicode.Wikicode = bulgarian_section.get_sections([3], "Anagrams")
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
        index = len(bulgarian_section.nodes)-1
        keep_going = True
        while index > 0 and keep_going:
            node_str_form = str(bulgarian_section.nodes[index])
            if not (node_str_form.isspace() or RE_MATCH_CATEGORIES.match(node_str_form)):
                keep_going = False
                index += 1  # Insert just after the content that isn't a whitespace/category
            else:
                index -= 1

        while index < len(bulgarian_section.nodes) and (node_str_form := str(bulgarian_section.nodes[index]).isspace()):
            index += 1

        bulgarian_section.insert(index, generate_anagrams_section(anagrams_to_add))

    return str(parsed), anagrams_added

def update_page(title: str, alphagram: str, uncreated: set[str]) -> bool:
    """Update a page with its anagrams. Returns whether changes were made."""
    page = pywikibot.Page(SITE, title)

    create_diff(page.text, page)
    
    if has_bulgarian(page):
        anagrams_to_add = anagrams[alphagram] - {title}
        new_content, anagrams_added = add_anagrams(page.text, anagrams_to_add, alphagram)
        new_content = re.sub("\n{3,}", "\n\n", new_content)

        for anagram in anagrams_to_add:
            other_page = pywikibot.Page(SITE, anagram)
            if not has_bulgarian(other_page):
                uncreated.add(f"{anagram}\n")

        if new_content == page.text:
            print(f"Did nothing on page {title} as there are already anagrams present", file=sys.stderr)
            return False
        else:
            page.text = new_content
            plural_s = "s" if len(anagrams_added) > 1 else ""
            if len(anagrams_added) == 0:
                print("Nothing was added, but the content was changed! (not saved)")
                return False

            page.save(f"Added anagram{plural_s} ({', '.join(anagrams_added)}) to Bulgarian section", minor=False)
            return True
    else:
        print(f"Skipping page {title}, as it does not exist or has no Bulgarian content", file=sys.stderr)
    
    return False

def main(uncreated: set[str]):
    try:
        LIMIT = int(pywikibot.argvu[1])
    except:
        LIMIT = -1

    print("Preparing to iterate over", len(anagrams), "alphragrams", f"({count_anagrams()} anagrams)")

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

            edit_count += int(update_page(anagram, alphagram, uncreated))  # If a change was made, increase the edit count

        iterations += 1

def there_are_erroneous_anagrams(original, anagrams: set[str]) -> bool:
    for anagram in anagrams:
        if anagram == original: continue
        if normalise(anagram) == normalise(original):
            return True
    return False

def find_erroneous_anagrams():
    errors = []
    for anagram_list in anagrams.values():
        for anagram in anagram_list:
            page = pywikibot.Page(SITE, anagram)
            
            if not page.exists(): continue
            if not has_bulgarian(page): continue

            print("Traversing page", anagram + "...")

            for template in mwparserfromhell.parse(page.text).filter(forcetype=mwparserfromhell.wikicode.Template):
                template: mwparserfromhell.wikicode.Template
                if template.name != "anagrams": continue
                if not template.has_param(1): continue
                if template.get(1) != "bg": continue

                if there_are_erroneous_anagrams(anagram, template.params[2:]):
                    print("Found erroneous anagrams: ", template.params[2:])
                    errors.append(anagram)
                    break

    with open("dubious_anagrams.txt", mode="w") as f:
        f.write("\n".join(errors))

if __name__ == "__main__":
    # uncreated = set()
    # try:
    #     with open(NOT_CREATED_LOG) as f:
    #         uncreated = set(f.readlines())
    # except FileNotFoundError:
    #     with open(NOT_CREATED_LOG, "w") as f:
    #         pass
    # try:
    #     main(uncreated)
    # finally:
    #     with open(NOT_CREATED_LOG, "w") as f:
    #         f.writelines(uncreated)
    find_erroneous_anagrams()