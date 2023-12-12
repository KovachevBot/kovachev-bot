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
        template.remove([p for p in template.params if p == val][0])

    is_indef = has_inflection(["indefinite", "indef", "indf", "indefinite state"])
    is_singular = has_inflection(["singular", "s", "sg"])

    if "vnoun" in template.params:
        if is_indef and is_singular:
            remove_positional_by_value("vnoun")
        else:
            verb = str(template.get(2)).replace(GRAVE, "").replace(ACUTE, "")
            try:
                verbal_noun_list = get_verbal_nouns(verb)
                if len(verbal_noun_list) > 1:
                    raise ValueError()
                remove_positional_by_value("vnoun")
                template.params[1] = verbal_noun_list[0]
            except KeyError:
                print(f"Verb {verb} has no verbal noun defined in the lookup table", file=sys.stderr)
            except ValueError:
                print(f"Verb {verb} has more than one possible verbal noun: {verbal_noun_list}", file=sys.stderr)

for page in kovachevbot.iterate_safe(kovachevbot.iterate_category("Bulgarian non-lemma forms")):
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
        page.save("Update verbal noun forms' {{infl of}} to point to the verbal noun / turn 'indefinite singular verbal noun' to 'verbal noun'")
    