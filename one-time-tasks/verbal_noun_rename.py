import kovachevbot
import pywikibot
import mwparserfromhell
import json
import sys

with open("verbal_nouns.json") as f:
    VERBAL_NOUNS = json.load(f)

GRAVE = chr(0x300)
ACUTE = chr(0x301)

def get_verbal_nouns(verb: str) -> str:
    return VERBAL_NOUNS[verb]

def fix_infl_template(template: mwparserfromhell.nodes.Template):
    def has_inflection(synonyms: list[str]) -> bool:
        return any(s in template.params for s in synonyms)

    def remove_positional_by_value(val):
        try:
            val = [p for p in template.params if p == val][0]
            template.remove(val)
        except:
            pass

    indef = ["indefinite", "indef", "indf", "indefinite state"]
    singular = ["singular", "s", "sg"]
    definite = ["definite", "def", "defn", "definite state"]
    plural = ["plural", "p", "pl"]
    is_indef = has_inflection(indef)
    is_singular = has_inflection(singular)
    is_def = has_inflection(definite)
    is_plural = has_inflection(plural)

    if "vnoun" in template.params or "verbal noun" in template.params:
        if is_indef and is_singular or not is_def and not is_plural:  # s|indef|vnoun or |vnoun by itself
            for _ in range(len(template.params)-2):
                del template.params[2] # Keep only the language code and the original verb form
            template.name = "verbal noun of"
        else:
            verb = str(template.get(2)).replace(GRAVE, "").replace(ACUTE, "")
            try:
                verbal_noun_list = get_verbal_nouns(verb)
                if len(verbal_noun_list) > 1:
                    raise ValueError()
                remove_positional_by_value("vnoun")
                remove_positional_by_value("verbal noun")
                template.params[1] = verbal_noun_list[0]
            except KeyError:
                print(f"Verb {verb} has no verbal noun defined in the lookup table", file=sys.stderr)
            except ValueError:
                print(f"Verb {verb} has more than one possible verbal noun: {verbal_noun_list}", file=sys.stderr)

def main():
    with open("verbal_noun_list.json") as f:
        ENTRIES = json.load(f)

    for page in kovachevbot.iterate_safe(kovachevbot.pages_from_titles(ENTRIES)):
        page: pywikibot.Page
        parsed = mwparserfromhell.parse(page.text)

        bulgarian = parsed.get_sections([2], "Bulgarian")[0]
        for template in bulgarian.filter_templates():
            template: mwparserfromhell.nodes.Template

            if template.name == "infl of" or template.name == "inflection of":
                fix_infl_template(template)
        
        out = str(parsed)
        if out != page.text:
            page.text = out
            page.save("Update verbal noun forms' {{infl of}} to point to the verbal noun / use {{verbal noun of}}")

if __name__ == "__main__":
    main()