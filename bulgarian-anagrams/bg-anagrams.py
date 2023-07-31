import sys
import pywikibot
import mwparserfromhell
import regex as re
from collections import Counter, defaultdict

# From User:JeffDoozan's bot AutoDooz
CAT_TEMPLATES = [ "c", "C", "cat", "top", "topic", "topics", "categorize", "catlangname", "catlangcode", "cln", "zh-cat",
        "eo F", "eo [1-9]OA", "eo-categoryTOC", "eo BRO", "eo GCSE", "Universala Vortaro" ]
RE_CAT_TEMPLATES = r"\{\{\s*(" + "|".join(CAT_TEMPLATES) + r")\s*[|}][^{}]*\}*"
RE_CATEGORIES = r"\[\[\s*[cC]at(egory)?\s*:[^\]]*\]\]"
RE_MATCH_CATEGORIES = re.compile(fr"({RE_CAT_TEMPLATES}|{RE_CATEGORIES})")
SITE = pywikibot.Site("en", "wiktionary")

def get_alphagram(word: str) -> str:
    return "".join(sorted(word.strip()))

def has_bulgarian(page: pywikibot.Page) -> bool:
    return bool(mwparserfromhell.parse(page.text).get_sections([2], "Bulgarian"))

with open("words.txt") as f:
    wordlist: list[str] = f.readlines()

anagrams = defaultdict(set)

for word in wordlist:
    anagrams[get_alphagram(word)].add(word.strip())

anagrams = {letter_count: anas for letter_count, anas in anagrams.items() if len(anas) > 1} # Only keep words with multiple anagrams

def generate_anagrams_section(anagrams: set[str]) -> str:
    return "\n\n===Anagrams===\n* " + generate_anagrams_template(anagrams, get_alphagram(anagrams.copy().pop())) + "\n\n"

def generate_anagrams_template(anagrams: set[str], alphagram: str) -> str:
    return "{{" + f"anagrams|bg|a={alphagram}|" + "|".join(anagrams) + "}}"

def add_anagrams(contents: str, anagrams_to_add: set[str], alphagram):
    parsed = mwparserfromhell.parse(contents)
    bulgarian_section: mwparserfromhell.wikicode.Wikicode = parsed.get_sections([2], "Bulgarian")[0]
    anagrams_section: mwparserfromhell.wikicode.Wikicode = bulgarian_section.get_sections([3], "Anagrams")
    if anagrams_section:
        anagrams_section = anagrams_section[0]
        anagrams_templates = anagrams_section.filter(forcetype=mwparserfromhell.wikicode.Template)
        anagrams_templates = [t for t in anagrams_templates if t.name == "anagrams"]
        if len(anagrams_templates) == 0:
            return contents
    
        existing = set()
        anagrams_template = anagrams_templates[0]
        i = 2
        while anagrams_template.has(i):
            existing.add(str(anagrams_template.get(i)))
            i += 1

        if existing == anagrams_to_add:
            return contents
        
        anagrams_to_add = anagrams_to_add.union(existing)

        anagrams_section.nodes[anagrams_section.index(anagrams_template)] = generate_anagrams_template(anagrams_to_add, alphagram)
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

    return str(parsed)

def update_page(title: str, counted: list[tuple[str, int]]) -> bool:
    """Update a page with its anagrams. Returns whether changes were made."""
    page = pywikibot.Page(SITE, title)
    
    if has_bulgarian(page):
        anagrams_to_add = anagrams[counted] - {title}
        new_content = add_anagrams(page.text, anagrams_to_add, counted)
        new_content = re.sub("\n{3,}", "\n\n", new_content)

        if new_content == page.text:
            print(f"Did nothing on page {title} as there are already anagrams present", file=sys.stderr)
            return False
        else:
            page.text = new_content
            plural_s = "s" if len(anagrams_to_add) > 1 else ""
            page.save(f"Added anagram{plural_s} ({', '.join(anagrams_to_add)}) to Bulgarian section", minor=False)
            return True
    else:
        print(f"Skipping page {title}, as it does not exist or has no Bulgarian content", file=sys.stderr)
    
    return False

def main():
    try:
        LIMIT = int(pywikibot.argvu[1])
    except:
        LIMIT = -1

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