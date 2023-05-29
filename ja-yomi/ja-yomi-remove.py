from typing import Generator
import pywikibot
import regex as re


JA_YOMI_TRACKING_PAGE = "tracking/ja-pron/yomi"
REMOVE_YOMI_PATTERN = re.compile(r"({{ja-pron(?:\|[^\|]+?=[^\|]+?|\|[^\|]+)*?)\|(?:y|yomi)=(?:o|on|go|goon|ko|kan|kanon|so|soon|to|toon|ky|kanyo|kanyoon|k|kun|j|ju|y|yu|i|irr|irreg|irregular)((?:\|[^\|]+?=[^\|]+?|\|[^\|]+)*}})")
JA_PRON_PATTERN = re.compile(r"{{ja-pron(?:\|[^\|]+?=[^\|]+?|\|[^\|]+)*}}")


def get_yomi_pages() -> Generator[pywikibot.Page, None, None]:
    SITE = pywikibot.Site("en", "wiktionary")
    TEMPLATE_NAMESPACE = SITE.namespaces.TEMPLATE
    MAIN_NAMESPACE = SITE.namespaces.MAIN
    return pywikibot.Page(SITE, JA_YOMI_TRACKING_PAGE, ns=TEMPLATE_NAMESPACE).getReferences(only_template_inclusion=True, namespaces=[MAIN_NAMESPACE])


# The way the pattern works is by forming two capture groups, one on either side of the regex matching for the yomi
# parameter, e.g. ({{ja-pron)  |yomi=k  (|おんせい}})
# (the yomi is separated here for demonstration purposes, otherwise it is contiguous with the other parameters.)
# The two bracketed text portions you see then substitute the original template, in effect replacing it
# with all of its contents, minus the original yomi (or y) argument.
def remove_yomi_from_page(page: pywikibot.Page) -> None:
    """
    Given a page on en.wiktionary, it removes any occurrences of `|y=` or `|yomi=`
    from the source within {{ja-pron}} templates.
    """
    text = page.text
    new_text = REMOVE_YOMI_PATTERN.sub(r"\1\2", text)
    page.text = new_text


def template_argument_counts_accord(previous_text: str, current_text: str) -> bool:
    """
    Gets the previous and current renditions of the wikitext, 
    ensuring that the number of template arguments for each occurrence of {{ja-pron}}
    is exactly 1 less in the current (new) text than it is in the old text.
    If this does not hold true, returns `False`, else `True`.
    Of course, this is because the new text should not have `y=` or `yomi=` in it,
    so the number of arguments should be exactly one less once this has been removed.
    """
    for previous_pron, current_pron in zip(JA_PRON_PATTERN.finditer(previous_text), JA_PRON_PATTERN.finditer(current_text)):
        prev_pr_text = previous_pron.group(0)
        curr_pr_text = current_pron.group(0)
        previous_arg_count = prev_pr_text.count("|")
        current_arg_count = curr_pr_text.count("|")
        if current_arg_count != previous_arg_count - 1:
            print(previous_arg_count, current_arg_count)
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
        print(f"Removing yomi from {page.title()}")
        remove_yomi_from_page(page)
        assert template_argument_counts_accord(original_text, page.text)
        page.save("Removed deprecated yomi/y parameters from {{ja-pron}} (automated task)", minor=True)


if __name__ == "__main__":
    main()
