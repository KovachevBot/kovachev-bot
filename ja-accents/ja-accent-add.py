import pywikibot
import mwparserfromhell
from typing import Generator
from daijirin import are_duplicate_kanas, is_kana, get_accent


SITE = pywikibot.Site("en", "wiktionary")
NO_ACC_TRACKING_PAGE = "tracking/ja-pron/no accent"
BLACKLIST = "blacklist.txt"

class JapaneseSectionNotFound(ValueError):
    """The entry had no Japanese section."""

def get_japanese_section(parsed_text: mwparserfromhell.wikicode.Wikicode):
    try:
        return parsed_text.get_sections([2], "Japanese")[0]
    except:
        raise JapaneseSectionNotFound()

def get_kana_from_pron(ja_pron: mwparserfromhell.wikicode.Template, page_title: str) -> str:
    # If entry is all kana, no kana will be provided in the {{ja-pron}}, so infer from title
    if ja_pron.has("1"):
        kana = str(ja_pron.get("1"))
    else: 
        if not is_kana(page_title):
            raise ValueError(f"ERROR, improperly formatted template on page {page_title}: pron template did not have kana despite non-kana title.")
        kana = page_title
    return kana

def there_are_duplicate_readings(ja_prons: list[mwparserfromhell.wikicode.Template], title: str) -> bool:
    return are_duplicate_kanas([get_kana_from_pron(pron, page_title=title) for pron in ja_prons])

def update_page(title: str):
    page = pywikibot.Page(SITE, title)
    parsed = mwparserfromhell.parse(page.text)
    japanese_section = get_japanese_section(parsed)
    ja_prons = [template for template in japanese_section.filter(forcetype=mwparserfromhell.wikicode.Template) if template.name == "ja-pron"]

    if len(ja_prons) == 0:
        raise ValueError(f"ERROR, no ja-pron on the page {title} to begin with, doing nothing.")
    
    if there_are_duplicate_readings(ja_prons, title):
        raise ValueError(f"ERROR, there are multiple indistinguishable terms on this page {title} with the same reading")

    for template in ja_prons:
        template: mwparserfromhell.wikicode.Template

        kana = get_kana_from_pron(template, title)

        possible_pitches = get_accent(main_headword=title, kana=kana)

        for i, accent in enumerate(possible_pitches):
            acc_param = f"acc{i+1 if i > 0 else ''}"
            acc_ref_param = f"{acc_param}_ref"
        
            if template.has(acc_param) or template.has(acc_ref_param):
                break
                # print("ERROR, template already has accent information")
                # return SuccessCode.FAILURE
        
            template.add(acc_param, accent)
            template.add(acc_ref_param, "DJR")

    if "===References===" not in japanese_section:
        japanese_section.append("\n\n===References===\n<references />\n\n")

    page.text = str(parsed)
    while "\n\n\n" in page.text:
        print("deez")
        page.text = page.text.replace("\n\n\n", "\n\n")

    print(str(mwparserfromhell.parse(page.text).get_sections([2], "Japanese")[0]), "Is this text acceptable? (y/n)", sep="\n")

    valid = False
    while not valid:
        answer = input()
        if answer == "y" or answer == "n":
            valid = True

    if answer == "y":
        page.save("Added accents to page", minor=False)

def get_accentless_pages() -> Generator[pywikibot.Page, None, None]:
    TEMPLATE_NAMESPACE = SITE.namespaces.TEMPLATE
    MAIN_NAMESPACE = SITE.namespaces.MAIN
    return pywikibot.Page(SITE, NO_ACC_TRACKING_PAGE, ns=TEMPLATE_NAMESPACE).getReferences(only_template_inclusion=True, namespaces=[MAIN_NAMESPACE])

def iterate_pages():
    for page in get_accentless_pages():
        try:
            update_page(page)
        except Exception as e:
            print(f"Unable to update {page.title()} due to error: {e}")

def main():
    try:
        with open(BLACKLIST) as f:
            blacklist = set(map(str.strip, f.readlines()))
    except FileNotFoundError:
        blacklist = set()
    
    # update_page("碧玉")
    # update_page("パイプカット")

    try:
        iterate_pages()
    except:
        with open(BLACKLIST, mode="w") as f:
            f.writelines(blacklist)

if __name__ == "__main__":
    main()