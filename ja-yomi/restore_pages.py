import os
import subprocess
import pywikibot


BACKUP_PATH = "ja-yomi-backup"
SITE = pywikibot.Site("en", "wiktionary")


def restore_page(page: pywikibot.Page):
    diff_file = os.path.join(BACKUP_PATH, page.title())
    current_text = page.text
    with open("temp", mode="w", encoding="utf-8") as f:
        f.write(current_text)

    subprocess.run(["patch", "temp", "-u", diff_file]) # Restores previous page text before my bot's edit
    with open("temp", encoding="utf-8") as f:
        restored_contents = f.read()
        return restored_contents


def restore_pages(page_list: list[str]):
    """
    For a list of page names, gets the Wiktionary pages for them and attempts to
    restore their contents.
    """
    for page_name in page_list:
        print(f"Restoring page {page_name}...")
        page = pywikibot.Page(SITE, page_name)
        try:
            print(restore_page(page))
            page.text = restore_page(page)
            page.save("Revert previous attempt to remove yomi parameters due to ill behaviour")
        except FileNotFoundError:
            print(f"No local patch was found for {page_name}; either the page was never edited, or no patch was correctly saved.")
        except Exception as e:
            print("Unknown error occurred:", e)
            raise SystemExit(1)

def main():
    pages_to_restore_file = input("Please enter a file that contains pages to revert: ")
    if not os.path.exists(pages_to_restore_file):
        print("File does not exist")
        raise SystemExit(1)

    with open(pages_to_restore_file) as f:
        restore_pages(f.read().splitlines()) # Done instead of f.readlines() because this removes line-ends


if __name__ == "__main__":
    main()
