import os
import subprocess
import pywikibot
import tkinter
import sys
import itertools
import mwparserfromhell
import regex as re
from typing import Generator, Iterator


WIKTIONARY = pywikibot.Site("en", "wiktionary")
TEMPLATE_NAMESPACE = WIKTIONARY.namespaces.TEMPLATE
MAIN_NAMESPACE = WIKTIONARY.namespaces.MAIN
COMMONS = pywikibot.Site("commons", "commons")
LINK_PATTERN = re.compile(r"\[\[(.+?)(?:\|(.+?))?\]\]")


def wikt_page(title: str) -> pywikibot.Page:
    return pywikibot.Page(WIKTIONARY, title)

def save_gui(page: pywikibot.Page, default_edit_summary: str = "") -> bool:
    """Returns whether the edit was successfully completed through the save button or not."""
    window = tkinter.Tk()
    window.title(f"Editing page {page.title()}")
    window.geometry("800x600")
    window.config(bg="#000000")
    
    page_text_label = tkinter.Label(master=window, text="Page contents")
    page_text_box = tkinter.Text(master=window)
    page_text_box.place(x=0, y=0)
    page_text_box.pack(fill="x", expand=False, padx=20, pady=0)
    page_text_box.insert("1.0", page.text)

    edit_summary_label = tkinter.Label(window, text="Edit summary")
    edit_summar_var = tkinter.StringVar()
    edit_summar_var.set(default_edit_summary)
    edit_summary_box = tkinter.Entry(window, textvariable=edit_summar_var, width=60)
    edit_summary_label.place(x=20, y=500)
    edit_summary_box.place(x=20, y=525)

    success = False

    def save_content():
        page.text = page_text_box.get("1.0", "end")
        edit_summary = edit_summar_var.get()
        window.destroy()
        page.save(edit_summary, minor=False)
        nonlocal success
        success = True

    button = tkinter.Button(window, text="Save", command=save_content)
    button.place(x=400, y=550)

    window.mainloop()
    return success

# save_gui(pywikibot.Page(WIKTIONARY, "User:Kiril kovachev/Sandbox"))

def convert_link_to_plaintext(link: mwparserfromhell.wikicode.Wikilink) -> str:
    if link.text is not None:
        if link.text == "": return link.title
        else: return link.text
    else:
        return link.title

def links_to_plaintext(text: str) -> str:
    parsed: mwparserfromhell.wikicode.Wikicode = mwparserfromhell.parse(text)
    links = parsed.filter(forcetype=mwparserfromhell.wikicode.Wikilink)
    for link in links:
        plain = convert_link_to_plaintext(link)
        parsed.replace(link, plain)

    return str(parsed)

ABORT_CHECK_INTERVAL = 5
HALT_PAGE = wikt_page("User:KovachevBot/halt")  # Do not edit, please!

def iterate_with_abort_check(iterator: Iterator, interval: int = ABORT_CHECK_INTERVAL, halt_page = HALT_PAGE):
    """
    Run over an iterator, checking at every interval of 5 (or other specified value)
    whether the bot has been ordered to stop. The failsafe site is defined as User:KovachevBot/halt by default.
    """
    for edit_count, value in enumerate(iterator):
        # Check halt page
        if edit_count % interval == 0:
            if "halt" in halt_page.text.casefold():
                print(f"ERROR: BOT WAS MANUALLY HALTED BY {halt_page.userName()}", file=sys.stderr)
                return
        yield value

def iterate_entries(iterator: Iterator, max_edits: int = None):
    """Iterate at most `max_edits` entries of an iterator (of pages), or unlimited.
    If no `max_edits` is provided as an arg, try to get the value from the command-line arguments.
    If it still isn't found, default to running indefinitely.
    If it is provided, but it's not a valid integer, it will default to unlimited again.
    In the unlimited case, this effectively means this iterator will run until the original one is exhausted.
    """
    if max_edits is None:
        try:
            edit_iter = range(int(pywikibot.argvu[1]))
        except:
            edit_iter = itertools.count()
    else:
        try:
            edit_iter = range(int(max_edits))
        except ValueError:
            edit_iter = itertools.count()

    for _, value in zip(edit_iter, iterator):
        yield value

def iterate_safe(iterator: Iterator, max_entries: int = None, abort_check_interval: int = ABORT_CHECK_INTERVAL, halt_page: pywikibot.Page = HALT_PAGE):
    """Iterate safely over an iterator of pages, checking every `abort_check_interval` for whether to halt
    the bot based on a user's manual request (by editing the `halt_page` to contain the word 'halt'),
    yielding at most `max_entries`.
    """
    return iterate_entries(iterate_with_abort_check(iterator, abort_check_interval, halt_page), max_entries)

def iterate_tracking(tracking_page: str) -> Generator[pywikibot.Page, None, None]:
    """
    Iterate over pages in a tracking category on Wiktionary (linked to within Template:tracking/(page_name_here)).
    `tracking_page` should be the name of the tracking category: e.g. if you want to iterate
    over `Template:tracking/ja-pron/yomi`, you would enter `ja-pron/yomi`.
    Returns only entries in the main entry namespace.
    """
    return pywikibot.Page(WIKTIONARY, f"tracking/{tracking_page}", ns=TEMPLATE_NAMESPACE).getReferences(only_template_inclusion=True, namespaces=[MAIN_NAMESPACE])

def iterate_category(category_name: str) -> Generator[pywikibot.Page, None, None]:
    """Iterate pages in a category on Wiktionary.
    The `category_name` should be the name without the Category: namespace, e.g.
    `category_name="Bulgarian lemmas"`.
    """
    return pywikibot.Category(WIKTIONARY, category_name).articles(namespaces=[MAIN_NAMESPACE])

def backup_page(old_text: str, new_page: pywikibot.Page, backup_path: str, file_name: str = None) -> None:
    """
    Copy the contents of the page to local storage for backup in case there is a problem
    with the script later; this will allow the error to be automatically corrected at that time.
    """

    file_name = file_name or new_page.title()
    os.makedirs(backup_path, exist_ok=True)
    
    with open("temp1", mode="w", encoding="utf-8") as f:
        f.write(old_text)

    with open("temp2", mode="w", encoding="utf-8") as f:
        f.write(new_page.text)

    diff = subprocess.getoutput("diff -u temp2 temp1") # Get differences between new revision and previous
    diff = diff + "\n" # patch will complain if we don't end the file with a newline

    with open(os.path.join(backup_path, new_page.title()), mode="w", encoding="utf-8") as f:
        f.write(diff)

def add_l2(parsed: mwparserfromhell.wikicode.Wikicode, l2_section: mwparserfromhell.wikicode.Wikicode) -> None:
    parsed = mwparserfromhell.parse(parsed)
    l2_section = mwparserfromhell.parse(l2_section)

    l2_title = l2_section.nodes[0].title

    if l2_title in [section.nodes[0].title for section in parsed.get_sections([2])]:
        return

    new = mwparserfromhell.parse("")

    l2_sections = parsed.get_sections([2])
    l2_sections.append(l2_section)

    l2_sections.sort(key=lambda section: section.nodes[0].title)

    for section in l2_sections:
        section.append("\n\n")
        new.append(section)

    parsed.nodes = new.nodes

    while "\n\n\n" in parsed:
        parsed.replace("\n\n\n", "\n\n")