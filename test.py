import pywikibot
import mwparserfromhell
import wikitextparser

PAGENAME = "къща"
#PAGENAME = "кукла"


site = pywikibot.Site()
page = pywikibot.Page(site, PAGENAME)
print(f"FETCHED: {PAGENAME}")
def get_forms(page):
    result = []
    text = page.expand_text()

    document = mwparserfromhell.parse(text)
    bulgarian = document.get_sections(matches=r"Bulgarian")[0] # Find the section that contains the Bulgarian entry
    nouns = bulgarian.get_sections(matches=r"Noun( \d+)*") # Locate any noun sections
    # document.get_sections()
    for n in nouns:

        all_forms = {"lemma": "", "forms": {}} # Each 'noun' has a list of forms in its declension, which we will be populating as a dictionary
        declension = n.get_sections(matches=r"Declension")
        if declension == []: continue 
        else: declension = declension[0]
        nav_frame = mwparserfromhell.parse(declension).nodes[2]
        table = wikitextparser.parse(str(nav_frame)).tables[0].data()
        columns = len(table[0]) # Always equals 3: the blank tile, plus the singular and plural
        rows = len(table) # Differs between masculine and non-masculine nouns; also depends on vocative presence

        # Removes wiki formatting, leaving only the text contents of the cell
        #cyrillic = lambda text: not bool(re.search('[A-ЌЎЏѐ-ќў-嶲]', text))
        #stripper = lambda item: [i.strip_code() for i in mwparserfromhell.parse(mwparserfromhell.parse(item)).nodes if cyrillic(i.strip_code())]
        get_tags = lambda item: [i for i in mwparserfromhell.parse(mwparserfromhell.parse(item)).nodes]
        stripper = lambda tags: [mwparserfromhell.parse(t).strip_code() for t in [t for t in tags if type(t) == mwparserfromhell.nodes.tag.Tag] if not ' class="tr Latn"' in t.attributes and t.tag == "span"]
        lemma = stripper(get_tags(table[1][1]))[0]
        all_forms["lemma"] = lemma
        for i in range(1, columns):
            column = table[0][i]
            for j in range(1, rows):
                row = table[j][0]
                tags = get_tags(table[j][i])
                
                #print(tags)
                values = (stripper(tags))
                        
                numbers = {
                    "singular": "s",
                    "plural": "p",
                }

                forms = {
                    "indefinite": "indef",
                    "definite": "def",
                    "definite<br>(subject form)": "sbjv",
                    "definite<br>(object form)": "objv",
                    "vocative form": "voc"
                }
                for v in values:
                    form = forms[row]
                    number = numbers[column]
                    if v not in all_forms["forms"]:
                        all_forms["forms"][v] = [(form, number)]
                    else:
                        all_forms["forms"][v].append((form, number))

                #print(f"{number}, {form}: {value}")
        for key in all_forms["forms"]:
            if all_forms["forms"][key] == [("sbjv", "p"), ("objv", "p")]:
                all_forms["forms"][key] = [("def", "p")]
            #print(all_forms[key])

            
        result.append(all_forms)
    return result

def generate_derivatives(form_list):
    forms = {dictionary["lemma"] for dictionary in form_list}
    if len(forms) < len(form_list):
        print("Multiple conflicting senses for this term exist with identical stresses, exiting")
        return
    for dic in form_list:
        strip_acute = lambda text: text.replace("́", "")
        lemma = dic["lemma"]
        for key in dic["forms"]:
            title = strip_acute(key)
            derivative_page = pywikibot.Page(site, title)
            content = mwparserfromhell.parse(derivative_page.text)
            if bool(content.get_sections(matches=r"Bulgarian")):
                print(f"ERROR: page {title} already contains existing Bulgarian entry, exiting")
                continue
            if not derivative_page.botMayEdit:
                print(f"ERROR: page {title} disallows bot editing, exiting")
            assert "==Bulgarian==" not in content
            if derivative_page.exists():
                pass
            else:
                print(f"Page {title} does not exist, creating derived form...")
                definition = "# {{inflection of|bg|" + lemma + "||"        
                for i, variant in enumerate(dic["forms"][key]):
                    form, number = variant
                    definition += form + "|" + number
                    if i < len(dic["forms"][key])-1:
                        definition += "|;|"
                definition += "}}"
                entry = "==Bulgarian==\n\n===Pronunciation===\n* {{bg-IPA|" + key + "}}\n\n===Noun===\n{{head|bg|noun form|head=" + key + "}}\n\n" + definition + "\n"
                derivative_page.text = entry
                derivative_page.save(f"Created derived form of {lemma}")
                print(f"Created page {title} with content: {entry}")
generate_derivatives(get_forms(page))