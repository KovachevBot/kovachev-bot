from typing import Generator
import pywikibot
import os
import subprocess
import mwparserfromhell
from mwparserfromhell.wikicode import Template
from restore_pages import BACKUP_PATH


JA_YOMI_TRACKING_PAGE = "tracking/ja-pron/yomi"

def get_yomi_pages() -> Generator[pywikibot.Page, None, None]:
    SITE = pywikibot.Site("en", "wiktionary")
    TEMPLATE_NAMESPACE = SITE.namespaces.TEMPLATE
    MAIN_NAMESPACE = SITE.namespaces.MAIN
    return pywikibot.Page(SITE, JA_YOMI_TRACKING_PAGE, ns=TEMPLATE_NAMESPACE).getReferences(only_template_inclusion=True, namespaces=[MAIN_NAMESPACE])


# Use mwparserfromhell to filter all the templates, select the ja-pron ones, and remove any "y" or "yomi"
# arguments they might have.
def remove_yomi_from_page(page: pywikibot.Page) -> None:
    """
    Given a page on en.wiktionary, it removes any occurrences of `|y=` or `|yomi=`
    from the source within {{ja-pron}} templates.
    """
    text = page.text
    parsed = mwparserfromhell.parse(text)
    for template in parsed.ifilter(forcetype=Template, recursive=False):
        template: Template
        if template.name != "ja-pron":
            continue

        if template.has("y"):
            template.remove("y")
        if template.has("yomi"):
            template.remove("yomi")

    new_text = str(parsed)
    return new_text

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

def template_argument_counts_accord(previous_text: str, current_text: str) -> bool:
    """
    Gets the previous and current renditions of the wikitext, 
    ensuring that the number of template arguments for each occurrence of {{ja-pron}}
    is exactly 1 less in the current (new) text than it is in the old text.
    If this does not hold true, returns `False`, else `True`.
    Of course, this is because the new text should not have `y=` or `yomi=` in it,
    so the number of arguments should be exactly one less once this has been removed.
    """
    for previous_pron, current_pron in zip(mwparserfromhell.parse(previous_text).filter(forcetype=Template, recursive=False), mwparserfromhell.parse(current_text).filter(forcetype=Template, recursive=False)):
        previous_pron: Template
        current_pron: Template
        
        if previous_pron.name != "ja-pron" or current_pron.name != "ja-pron":
            continue

        if len(current_pron.params) != len(previous_pron.params) - 1:
            return False

    return True

def main():
    # Get the maximum number of edits to make from the user (e.g. `pwb ja-yomi-remove 100`);
    # if not found then set to unlimited (-1)
    try:
        LIMIT = int(pywikibot.argvu[1])
    except:
        LIMIT = -1

    for edit_count, page in enumerate(get_yomi_pages()):
        if edit_count == LIMIT:
            return

        original_text = page.text
        print(f"Removing yomi from {page.title()}...")
        page.text = remove_yomi_from_page(page)
        print(f"Backing up {page.title()}...")
        create_diff(original_text, page)
        assert template_argument_counts_accord(original_text, page.text)
        page.save("Removed deprecated yomi/y parameters from {{ja-pron}} (automated task)", minor=True, botflag=True)


if __name__ == "__main__":
    main()
