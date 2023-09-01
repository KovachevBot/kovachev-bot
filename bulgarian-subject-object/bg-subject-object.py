import kovachevbot
import pywikibot
import mwparserfromhell
import sys

def fix_inflection(template: mwparserfromhell.wikicode.Template):
    for param in template.params:
        param: mwparserfromhell.nodes.extras.Parameter
        if param.value == "sbjv":
            param.value = "sbj"
        elif param.value == "objv":
            param.value = "obj"

def main() -> None:
    with open("words-to-edit.txt") as f:
        words_to_fix = f.read().splitlines()
    
    for page in kovachevbot.iterate_safe((kovachevbot.wikt_page(word) for word in words_to_fix)):
        page: pywikibot.Page
        title = page.title()
        parsed = mwparserfromhell.parse(page.text)
        try:
            bulgarian_section: mwparserfromhell.wikicode.Wikicode = parsed.get_sections([2], "Bulgarian")[0]
        except IndexError:
            print(f"Error: page {title} has no Bulgarian content", file=sys.stderr)
        
        for inflection_template in bulgarian_section.filter(forcetype=mwparserfromhell.wikicode.Template, matches="{{inflection of|bg|.*?}}"):
            inflection_template: mwparserfromhell.wikicode.Template
            fix_inflection(inflection_template)

        page.text = str(parsed)
        page.save("Convert sbjv/objv into sbj/obj in Bulgarian inflections")

if __name__ == "__main__":
    main()