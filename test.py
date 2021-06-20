import pywikibot
import mwparserfromhell
import wikitextparser
import os

numbers = {
    "singular": "s",
    "plural": "p",
}

forms = {
    "indefinite": "indef",
    "definite": "def",
    "definite<br>(subject form)": "sbjv",
    "definite<br>(object form)": "objv",
    "vocative form": "voc",
    "count form": "count"
}


# Connect to Wiktionary (according to user profile)
site = pywikibot.Site()

"""Returns a list of dictionaries; each dictionary looks like this:
{ "lemma": <term>
  "forms": {
      <form 1>: [("indef", "s"), ("voc", "s")
      etc.    
  }
}
Each dictionary is able to be used to generate an entire set of noun forms.
The reason there are multiple dictionaries in the list is because there can be 
multiple noun forms per page, each of which *can* have different declensions.
If there is only one noun header on a page, it is not necessary to include multiple etymologies on the derived form page."""
def get_forms(page):
    # 'result' is the list of dictionaries to be returned
    result = []
    text = page.expand_text() # Provides fully-expanded wikitext of a page, i.e. shows the full table markup instead of {{bg-ndecl}}

    document = mwparserfromhell.parse(text)
    bulgarian = document.get_sections(matches=r"Bulgarian")[0] # Find the section that contains the Bulgarian entry
    nouns = bulgarian.get_sections(matches=r"Noun( \d+)*") # Locate any noun sections
    for n in nouns:
        all_forms = {"lemma": "", "forms": {}} # Each 'noun' has a list of forms in its declension, which we will be populating as a dictionary
        declension = n.get_sections(matches=r"Declension") # Finds declension header
        if declension == []: continue
        else: declension = declension[0] # If there is no declension for a noun form, skip, else set 'declension' to the first element in the result
        nav_frame = mwparserfromhell.parse(declension).nodes[2] # Selects the wikitable itself
        table = wikitextparser.parse(str(nav_frame)).tables[0].data() # Converts into 2D list
        columns = len(table[0]) # Always equals 3: the blank tile, plus the singular and plural
        rows = len(table) # Differs between masculine and non-masculine nouns; also depends on vocative presence

        # Removes wiki formatting, leaving only the text contents of the cell
        get_tags = lambda item: [i for i in mwparserfromhell.parse(mwparserfromhell.parse(item)).nodes] # Lists all tags in a given cell
        stripper = lambda tags: [mwparserfromhell.parse(t).strip_code() for t in [t for t in tags if type(t) == mwparserfromhell.nodes.tag.Tag] if not ' class="tr Latn"' in t.attributes and t.tag == "span"]
        lemma = stripper(get_tags(table[1][1]))[0]
        all_forms["lemma"] = lemma
        for i in range(1, columns):
            column = table[0][i]
            for j in range(1, rows):
                row = table[j][0]
                tags = get_tags(table[j][i])
                values = stripper(tags)
                        
                for v in values:
                    # Converts the table's "singular", "plural", "vocative form", etc., labels into "s", "p", "v", etc. 
                    form = forms[row]
                    number = numbers[column]
                    # Count form is a bit different, as the parameters are not "form|number" but the literal, "count|form".
                    if row == "count form":
                        form, number = "count", "form"
                    if v not in all_forms["forms"]:
                        all_forms["forms"][v] = [(form, number)]
                    else:
                        all_forms["forms"][v].append((form, number))
        # This check is useful for masculine terms, as the above code would profile certain noun forms as being both
        # 'definite (subject form) plural' and 'definite (object form) plural', even though those forms are the same in Bulgarian.
        # Hence, this snippet is run to ensure the two get merged into simply 'definite plural'.
        for key in all_forms["forms"]:
            if all_forms["forms"][key] == [("sbjv", "p"), ("objv", "p")]:
                all_forms["forms"][key] = [("def", "p")]
        result.append(all_forms)
    return result

"""Used to generate pages from a list of dictionaries corresponding to the derived forms from declension tables.
Iterates over all forms and generates new pages for them if no page exists with a Bulgarian entry.
"""
def generate_derivatives(form_list):

    pages_to_create = dict()
    for dic in form_list:
        for key in dic["forms"]:
            stripped = key.replace("́", "")
            if stripped not in pages_to_create:
                pages_to_create[stripped] = {
                    "associations": [
                        {
                            "mapping": [
                                dic["lemma"],
                                key
                            ],
                            "forms": dic["forms"][key]

                        }
                    ]
                }
            else:
                pages_to_create[stripped]["associations"].append(
                    {
                            "mapping": [
                                dic["lemma"],
                                key
                            ],
                            "forms": dic["forms"][key]

                        }
                )

    for title in pages_to_create:
        print(f"Creating page {title}.")
        derivative_page = pywikibot.Page(site, title)
        page_content = mwparserfromhell.parse(derivative_page.text)
        entry = ""
        
        # Check whether the bot can feasibly/permissibly edit the page. If not, quit.
        # if bool(page_content.get_sections(matches=r"Bulgarian")):
        #     print(f"NOTE: page {title} already contains existing Bulgarian entry, exiting")
        #     continue
        if not derivative_page.botMayEdit:
            print(f"ERROR: page {title} disallows bot editing, exiting")
            continue
        
        # We are clear to edit once these checks have been ascertained. That there is no Bulgarian header means
        # we are also safe to generate the entries now: we are guaranteed not to waste any processing time,
        # as it is certain that the content to be generated will find a place on the page (so long as there is no existing
        # Bulgarin entry, as we have hereby discovered.)
        # A few scenarios now exist:
        # 1. For a given title, it corresponds to only one of the original etymologies. Check out 'кукла':
        # The form 'кукло' is a vocative singular, but only applies to the first type.
        # → In this case, we need to create a page with only one Pronunciation, no Etymology header, and a
        # reference to the given lemma.
        # 
        # 2. For a given title, it corresponds to multiple etymologies. The same page 'кукла' also has multiple
        # forms that are shared by all 3 declension tables in that entry, for example the definite singular 'куклата'.
        # → In this case, we need to create a page containing separate Etymology headers for each form.
        # We should also check all of the dictionaries for their spelling of the title, as if all of the forms have the
        # exact same spelling (including acute symbols for accentuation), the prounciation header can be relegated to the
        # top as an L3 header, rather than repeating the same IPA template underneath each etymology (which can be the same.)
        
        def generate_definition(formlist, lemma):
            definition = "# {{inflection of|bg|" + lemma + "||"        
            for i, variant in enumerate(formlist):
                form, number = variant
                definition += form + "|" + number
                if i < len(formlist)-1:
                    definition += "|;|"
            definition += "}}"
            return definition

        # Case 1: only one association
        if len(pages_to_create[title]["associations"]) == 1:
            lemma = pages_to_create[title]["associations"][0]["mapping"][0]
            declined_form = pages_to_create[title]["associations"][0]["mapping"][1]
            forms = pages_to_create[title]["associations"][0]["forms"]

            definition = generate_definition(forms, lemma)
            entry = "==Bulgarian==\n\n===Pronunciation===\n* {{bg-IPA|" + declined_form + "}}\n\n===Noun===\n{{head|bg|noun form|head=" + declined_form + "}}\n\n" + definition + "\n"
        
        # Case 2: multiple associations
        else:
            entry = "==Bulgarian==\n\n"
            uniform_pronunciation = True # Assume each form has the same pronunciation
            previous = ""
            for a in pages_to_create[title]["associations"]:
                # If the spelling of the current term differs from the previous, we have different pronunciations
                if a["mapping"][1] != previous and previous != "":
                    uniform_pronunciation = False
                    break
                # At each iteration, set the 'previous' variable equal to the
                previous = a["mapping"][1]
            if uniform_pronunciation:
                entry += "===Pronunciation===\n* {{bg-IPA|" + previous + "}}\n\n"
            
            for i, a in enumerate(pages_to_create[title]["associations"]):
                entry += "===Etymology "  + str(i+1) + "===\n\n" 
                lemma = a["mapping"][0]
                declined_form = a["mapping"][1]
                forms = a["forms"]
                definition = generate_definition(forms, lemma)
                if not uniform_pronunciation:
                    entry += "====Pronunciation====\n* {{bg-IPA|" + declined_form + "}}\n\n"
                entry += "====Noun===="
                entry += "\n{{head|bg|noun form|head=" + declined_form + "}}\n\n" + definition + "\n\n"
            if entry.endswith("\n\n"):
                entry = entry[:-1]
        
        # The page we are trying to create either exists, or does not.
        # 3. The page exists already.
        # This means that someone has already entered content into the page. So long as the page even vaguely conforms
        # to the requirements of a page on this wiki, it will have some number of L2 language headers.
        # → In this case, we need to find the first language header that comes after Bulgarian, and then place the Bulgarian
        # entry after the language header that precedes it (or at the beginning of the page, if no language precedes the
        # existing language header). Furthermore, there may not be any language header that comes after Bulgarian, e.g.
        # the only entry is for some other language that comes before Bulgarian, e.g. Belarusian.
        # Should this occur, the Bulgarian can simply be placed at the end of the page.
        # 
        # 4. The page does not exist yet.
        # This is the by-far simpler case, as it means I can simply paste the desired contents into the page and save it.
        # → In this case, all that we need to do is set the page's content equal to the generated entry and smash that
        # save request. Not too bad in this case.

        save_message = "" # Edit summary

        # Case 3: the page already exists.
        if derivative_page.exists():
            found, index  = "", -1
            for i, section in enumerate(page_content.get_sections(levels=[2])):
                t = section.nodes[0].title
                if t > "Bulgarian":
                    found = section
                    index = i
                    break

            # Some considerations here: if there is now a heading preceding the heading that was found,
            # the Bulgarian entry must go after it. Else (i.e. i will be 0), the Bulgarian can be placed
            # at the beginning of the page. We must be aware that sometimes, the top of the page contains the {{also}}
            # template, and in fact, can contain any number of bizarre templates theoretically.
            # However, this can be accounted for by placing the entry right before the first heading ("==").
            # If i remains -1, that means there is no heading that should follow ==Bulgarian===; consequently,
            # the Bulgarian can be placed at the end of the page straight away.

            if i == -1:
                derivative_page.text = derivative_page.text + "\n----\n\n" + entry
            elif i == 0:
                first_lang = derivative_page.text.find("==")
                derivative_page.text = derivative_page.text[0:first_lang] + entry + "\n----\n\n" + derivative_page.text[first_lang:]
            else:
                # The Bulgarian entry lies somewhere between two other entries
                preceding = page_content.get_sections(levels=[2])[i-1].nodes[0].title
                stringed = str(page_content)
                split_location = stringed.find("----", stringed.find(str(preceding))) + 5
                derivative_page.text = stringed[:split_location] + "\n" + entry + "\n----\n\n" + stringed[split_location:]
            save_message = f"Updated page {title} with content: {derivative_page.text}"
        
        # Case 4: the page does not exist.
        else:
            derivative_page.text = entry
            save_message = f"Created derived form of {lemma}" 
        
        derivative_page.save(save_message)
        if os.path.exists(os.path.expanduser(f"~/Documents/Programming/Wiktionary/Bot/output/")):
            with open(os.path.expanduser(f"~/Documents/Programming/Wiktionary/Bot/output/{title}.txt"), mode="w", encoding="utf-8") as output:
                output.write(derivative_page.text)

# Just a little alias
def analyze_and_generate(page):
    generate_derivatives(get_forms(page))

if __name__ == "__main__":
    bg_nouns = pywikibot.Category(site, "Category:Bulgarian_nouns")
    n_editing = 10
    for p in bg_nouns.articles(total=n_editing):
        analyze_and_generate(p)
