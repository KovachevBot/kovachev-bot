import traceback
from typing import Iterator
import kovachevbot
import mwparserfromhell
import sys
import pywikibot
import regex as re


ROMAJI_TRANSLITERATION_PATTERN = re.compile(r"\(\w+?\)")
MULTIPLE_SPACE_PATTERN = re.compile(r" {2,}")
UNEXPECTED_JA_READINGS_SYNTAX_PATTERN = re.compile(r"[^\u3040-\u309F\u30A0-\u30FF\-.,<\s]")


def wikicode_is_safe(param: mwparserfromhell.wikicode.Wikicode) -> bool:
    # Considered "safe" if it contains only text and maybe plain wikilinks
    return all(type(node) in (mwparserfromhell.nodes.text.Text, mwparserfromhell.wikicode.Wikilink) for node in param.nodes)

def fix_reading_str(reading_str: str) -> str:
    all_readings = [each.strip() for each in reading_str.split(",")]
    all_readings = [MULTIPLE_SPACE_PATTERN.sub(" ", ROMAJI_TRANSLITERATION_PATTERN.sub("", kovachevbot.links_to_plaintext(each))).strip() for each in all_readings]
    return ", ".join(all_readings)
    # return ROMAJI_TRANSLITERATION_PATTERN.sub("", kovachevbot.links_to_plaintext(reading_str))

def fix_page(page: pywikibot.Page):
    kanji = page.title()
    parsed = mwparserfromhell.parse(page.text)
    japanese_section_search = parsed.get_sections([2], "Japanese")
    if len(japanese_section_search) == 0:
        print("Skipping page", kanji, "as it has no Japanese section", file=sys.stderr)
    
    japanese_section: mwparserfromhell.wikicode.Wikicode = japanese_section_search[0]

    ja_readingses: list[mwparserfromhell.wikicode.Template] = japanese_section.filter(forcetype=mwparserfromhell.wikicode.Template, matches="ja-readings")

    for ja_reading_template in ja_readingses:
        if str(ja_reading_template.name).strip() != "ja-readings":
            print("Mistakenly captured template", ja_reading_template.name, file=sys.stderr)
            continue

        params_on_newlines = ja_reading_template.name == "ja-readings\n"
        params_to_remove = list()
        for param in ja_reading_template.params:
            param: mwparserfromhell.nodes.extras.Parameter
            # Places where a manual transliteration has distinguished a syllable boundary, e.g.
            # utsukushii instead of utsukushī, are too complicated, and I opt to fix these by hand.
            # Hence we just keep track of them by making a persistent file.
            if "ii" in param.value or "aa" in param.value or "ee" in param.value or "oo" in param.value or "uu" in param.value:
                print("Warning: potential transliteration variance due to doubled vowel", file=sys.stderr)
                with open(f"READINGS_EXCEPTION_{kanji}", "w") as f:
                    f.write(str(param.value))

            # Can't delete params while iterating, so we need to store them to delete later
            if param.value == "":  # Delete parameters that are supplied but not populated, e.g. "|nanori="
                params_to_remove.append(param)
            else:
                if not wikicode_is_safe(param.value):
                    print("CRITICAL WARNING! NON-TEXT ELEMENT DETECTED", kanji, file=sys.stderr)
                    with open(f"READINGS_EXCEPTION_{kanji}", "w") as f:
                        f.write(str(param.value))
                        continue

                fixed = fix_reading_str(str(param.value)) + ("\n" if params_on_newlines else "")

                # If there are non-textual elements, e.g. comments, blah blah, then the parameter cannot be trusted at all
                # Ensure only the expected family of symbols (kana, comma, <, full stop, hyphen) are present

                if UNEXPECTED_JA_READINGS_SYNTAX_PATTERN.match(fixed):
                    print("CRITICAL WARNING! INVALID SYNTAX DETECTED", kanji, file=sys.stderr)
                    with open(f"READINGS_EXCEPTION_{kanji}", "w") as f:
                        f.write(fixed)
                        continue

                param.value = fixed

        for param in params_to_remove:
            ja_reading_template.remove(param)

    page.text = str(parsed)

def main():
    with open("ja-readings-to-fix.txt") as f:
        kanji_to_fix = f.read()

    pages = (kovachevbot.wikt_page(kanji) for kanji in kanji_to_fix)
    checked_pages_iter: Iterator[pywikibot.Page]  = kovachevbot.iterate_safe(pages)
    try:
        for i, page in enumerate(checked_pages_iter):
            fix_page(page)
            page.save("Remove redundant ja-readings markup (manual transliterations; manual links; empty params)")
    except:
        i -= 1
        if i < 0: i = 0
        traceback.print_exc()
    finally:
        kanji_to_fix = kanji_to_fix[max(i+1, 0):]
        with open("ja-readings-to-fix.txt", mode="w") as f:
            kanji_to_fix = f.write(kanji_to_fix)

if __name__ == "__main__":
    main()