import kovachevbot
import pywikibot
import mwparserfromhell
import json
import sys

with open("verbal_nouns.json") as f:
    VERBAL_NOUNS = json.load(f)

GRAVE = chr(0x300)
ACUTE = chr(0x301)

# Consume an iterator. For doing side effects using a generator expression in one line.
def do(iter):
    for _ in iter: pass

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
    is_indef = has_inflection(indef)
    is_singular = has_inflection(singular)

    if "vnoun" in template.params or "verbal noun" in template.params:
        if is_indef and is_singular:
            do(remove_positional_by_value(i) for i in indef)
            do(remove_positional_by_value(s) for s in singular)
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
    