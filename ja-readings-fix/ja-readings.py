import traceback
from typing import Iterator
import kovachevbot
import mwparserfromhell
import sys
import pywikibot
import regex as re

ROMAJI_TRANSLITERATION_PATTERN = re.compile(r"\(\w+?\)")

def fix_reading_str(reading_str: str) -> str:
    all_readings = [each.strip() for each in reading_str.split(",")]
    all_readings = [kovachevbot.links_to_plaintext(ROMAJI_TRANSLITERATION_PATTERN.sub("", each)).strip() for each in all_readings]
    return ", ".join(all_readings)

def fix_page(page: pywikibot.Page):
    kanji = page.title()
    parsed = mwparserfromhell.parse(page.text)
    japanese_section_search = parsed.get_sections([2], "Japanese")
    if len(japanese_section_search) == 0:
        print("Skipping page", kanji, "as it has no Japanese section", file=sys.stderr)
    
    japanese_section: mwparserfromhell.wikicode.Wikicode = japanese_section_search[0]

    ja_readingses: list[mwparserfromhell.wikicode.Template] = japanese_section.filter(forcetype=mwparserfromhell.wikicode.Template, matches="ja-readings")

    for ja_reading_template in ja_readingses:
        params_to_remove = list()
        for param in ja_reading_template.params:
            param: mwparserfromhell.nodes.extras.Parameter

            # Can't delete params while iterating, so we need to store them to delete later
            if param.value == "":  # Delete parameters that are supplied but not populated, e.g. "|nanori="
                params_to_remove.append(param)
            else:
                param.value = fix_reading_str(str(param.value))
        
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
            print(page.title())
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