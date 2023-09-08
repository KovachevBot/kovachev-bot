from enum import Enum
import sys
from typing import Generator, Iterable
import webbrowser
import re
import pyperclip
import pywikibot
import mwparserfromhell
import kovachevbot

SITE = pywikibot.Site("en", "wiktionary")
COMMONS = pywikibot.Site("commons", "commons")
NEED_ATTENTION = "audio_needs_attention.txt"
SEEN_ENTRIES = "audio_seen_files.txt"
HEAD_TEMPLATES = {"bg-noun", "bg-verb", "bg-adj", "head", "bg-adv", "bg-verbal noun", "bg-verbal noun form", "bg-letter", "bg-part", "bg-part form", "bg-phrase", "bg-proper noun"}


def get_audio_template_from_file_name(file_name: str) -> str:
    return f"* {{{{audio|bg|{file_name.replace('File:', '')}|Audio}}}}"

def section_name(section: mwparserfromhell.wikicode.Wikicode) -> str:
    return re.sub("=+", "", str(section.nodes[0]))

def get_section_candidate(sections) -> str:
    """
    Returns a code, which is the ordinal number of the section which is the most appropriate one
    to edit on this page. For example, if the page has only a Bulgarian section with
    1 Pronunciation and 1 Noun header, this will return 2, as 1 is the first section (Bulgarian),
    and 2 is the second section in the page, which is the Pronunciation section.
    If there are in fact multiple Bulgarian pronunciation headers, then that requires that we edit
    the whole Bulgarian section so I can figure out which is the correct place to put the audio. 
    """
    return [section_name(s) for s in sections].index("Bulgarian") + 1

def get_wikitonary_edit_url(page_name: str, sections) -> str:
    section_to_edit = get_section_candidate(sections)
    return f"https://en.wiktionary.org/w/index.php?title={page_name}&action=edit&section={section_to_edit}"

def add_pronunciation_section(bulgarian_section: mwparserfromhell.wikicode.Wikicode, term: str) -> None:
    term = kovachevbot.links_to_plaintext(term)  # Remove link syntax from term
    PRONUNCIATION_CONTENT = "\n\n===Pronunciation===\n* {{bg-IPA|" + term + "}}\n\n"

    if (e := bulgarian_section.get_sections([3], "Etymology")):
        etymology: mwparserfromhell.wikicode.Wikicode = e[0]
        etymology.append(PRONUNCIATION_CONTENT)
    elif (a := bulgarian_section.get_sections([3], "Alternative forms")):
        alternative_forms: mwparserfromhell.wikicode.Wikicode = a[0]
        alternative_forms.append(PRONUNCIATION_CONTENT)
    else:
        i = 1
        while not type(bulgarian_section.nodes[i]) is mwparserfromhell.nodes.heading.Heading:
            i += 1

        bulgarian_section.get_sections([2], "Bulgarian")[0].insert_before(bulgarian_section.nodes[i], PRONUNCIATION_CONTENT)

    while "\n\n\n" in bulgarian_section:
        bulgarian_section.replace("\n\n\n", "\n\n")

def process_header(template: mwparserfromhell.wikicode.Template) -> set[str]:
    name = str(template.name)
    
    def default_class() -> set[str]:
        s = set()
        if template.has("1"):
            s.add(str(template.get(1).value))
        
        i = 2
        while template.has((param_name := f"head{i}")):
            s.add(str(template.get(param_name).value))
            i += 1
        
        return s
    
    if name == "head":
        s = set()
        if template.has("head"):
            s.add(str(template.get("head").value))
        i = 2
        while template.has((param_name := f"head{i}")):
            s.add(str(template.get(param_name).value))
            i += 1
    else:
        s = default_class()

    return s


class PageEditStatus(Enum):
    SUCCESS = 0
    NOTHING_TO_ADD = 1
    CANNOT_ADD = 2

def is_bg_ipa(node) -> bool:
    return isinstance(node, mwparserfromhell.wikicode.Template) and node.name == "bg-IPA"

def visit_page(page_name: str, audio_file_name: str) -> bool:
    p = pywikibot.Page(SITE, page_name)
    parsed = mwparserfromhell.parse(p.text)

    # sections = parsed.get_sections([2, 3, 4, 5, 6, 7])
    try:
        bulgarian_section: mwparserfromhell.wikicode.Wikicode = parsed.get_sections([2], "Bulgarian")[0]
    except IndexError:
        print("No Bulgarian entry for term", page_name, file=sys.stderr)
        return

    edit_summary = ""
    # bulgarian_subsections = bulgarian_section.get_sections([3, 4, 5, 6, 7])
    etymology_sections = bulgarian_section.get_sections([3], "Etymology")
    pronunciation_subsections = bulgarian_section.get_sections([3, 4], "Pronunciation")
    pronunciation_subsections_l3 = bulgarian_section.get_sections([3], "Pronunciation")

    if len(etymology_sections) < 2 and not pronunciation_subsections:
        all_headers = set()
        for template in bulgarian_section.filter(forcetype=mwparserfromhell.wikicode.Template):
            if str(template.name) in HEAD_TEMPLATES:
                all_headers.update(process_header(template))
        
        if len(all_headers) > 1:
            pass
        else:
            if len(all_headers) == 1:
                term = all_headers.pop()
            else:
                term = page_name

            add_pronunciation_section(bulgarian_section, term)
            pronunciation_subsections = bulgarian_section.get_sections([3, 4], "Pronunciation")
            pronunciation_subsections_l3 = bulgarian_section.get_sections([3], "Pronunciation")
            edit_summary += "Added pronunciation section; "

    def should_edit() -> PageEditStatus:
        if len(pronunciation_subsections) != 1 and not pronunciation_subsections_l3:
            # Need one existing pronunciation section to attach to,
            # or if none exists then it could be created later
            return PageEditStatus.CANNOT_ADD
        
        for template in pronunciation_subsections[0].filter(forcetype=mwparserfromhell.wikicode.Template):
            if template.name == "audio":
                return PageEditStatus.NOTHING_TO_ADD
        
        vowels = "[аъоуеияѝю]"
        if len(re.findall(vowels, page_name)) == 1:
            # Monosyllabic so add audio
            return PageEditStatus.SUCCESS

        prons = 0
        heads = 0
        for template in bulgarian_section.filter(forcetype=mwparserfromhell.wikicode.Template):
            if template.name == "bg-IPA":
                prons += 1
            elif str(template.name) in HEAD_TEMPLATES:
                heads += 1
        
        if prons > 1:
            # More than one pronunciation template or more than one part of speech (which may have different stress?)
            return PageEditStatus.CANNOT_ADD
        
        if pronunciation_subsections_l3:
            # If there is an L3, that means an editor has identified there to be only one common pronunciatin
            return PageEditStatus.SUCCESS

        if heads > 1:
            return PageEditStatus.CANNOT_ADD

        if len(bulgarian_section.get_sections([3], "Etymology")) > 1:
            # If multiple etymologies (homographs), skip
            return PageEditStatus.CANNOT_ADD


        return PageEditStatus.SUCCESS

    # pyperclip.copy(get_audio_template_from_file_name(audio_file_name))
    # webbrowser.open_new_tab(get_wikitonary_edit_url(page_name, sections))
    edit_status = should_edit()
    if edit_status is PageEditStatus.SUCCESS:
        i = 0
        pron_section: mwparserfromhell.wikicode.Wikicode = pronunciation_subsections[0]
        
        templates: list[mwparserfromhell.wikicode.Template] = pron_section.filter_templates()
        TO_INSERT = "\n" + get_audio_template_from_file_name(audio_file_name)

        if is_bg_ipa(templates[0]):
            pron_section.insert_after(templates[0], TO_INSERT)
        else:
            pron_section.insert(1, TO_INSERT)

        p.text = str(parsed)
        edit_summary += ("A" if edit_summary == "" else "a") + "dd audio from User:Kiril kovachev"
        p.save(edit_summary, minor=False)

    return edit_status

def run(attention: list[str], contribs: Iterable[str]):
    for namespaced_filename in contribs:
        filename = namespaced_filename[5:]
        page_name = namespaced_filename[namespaced_filename.rfind("Kiril kovachev-")+1+len("Kiril kovachev"):-4]
        status = visit_page(page_name, filename)

        if status is PageEditStatus.CANNOT_ADD:
            attention.append(page_name)
            print(f"Failed to update page {page_name}, requires manual attention", file=sys.stderr)

def get_lines(filename: str) -> list[str]:
    try:
        with open(filename) as f:
            lines = [line.strip() for line in f.readlines()]
    except:
        with open(filename, mode="w") as f:
            pass

        lines = []

    return lines

def contributions(user: pywikibot.User, seen: list[str] = None, quit_if_seen: bool = True) -> Generator[str, None, None]:
    if seen is None: seen = []
    
    for record in user.contributions(total=-1):
        file = record[0].title()
        
        if quit_if_seen and file in seen:
            print("Caught up to latest changes, quitting")
            return

        if file.startswith("File") and file.endswith(".wav") and "LL" in file:
            yield file
        else:
            print("Ignoring contribution", file, file=sys.stderr)

        seen.append(file)

def auto_add():
    attention = get_lines(NEED_ATTENTION)
    seen = get_lines(SEEN_ENTRIES)

    me = pywikibot.User(COMMONS, "User:Kiril kovachev")

    try:
        run(attention, contributions(me, seen))
    except KeyboardInterrupt:
        print()
    finally:
        with open(NEED_ATTENTION, mode="w") as f:
            f.write("\n".join(attention))

        with open(SEEN_ENTRIES, mode="w") as f:
            f.write("\n".join(seen))

def manual():
    attention = get_lines(NEED_ATTENTION)

    try:
        for line in attention:
            p = pywikibot.Page(SITE, line)
            parsed = mwparserfromhell.parse(p.text)
            sections = parsed.get_sections([2, 3, 4, 5, 6, 7])

            pyperclip.copy(f"\n===Pronunciation===\n* {{{{bg-IPA|{line}}}}}\n" + get_audio_template_from_file_name(f"File:LL-Q7918 (bul)-Kiril kovachev-{line}.wav") + "\n")
            webbrowser.open_new_tab(get_wikitonary_edit_url(line, sections))
            input("Press enter for the next file: ")
            attention.remove(line)
    except KeyboardInterrupt:
        print()
    finally:
        with open(NEED_ATTENTION, mode="w") as f:
            f.write("\n".join(attention))

def reorder(limit: int = 2300):
    me = pywikibot.User(SITE, "User:KovachevBot")

    disordered: list[str] = []
    PRECEDENCE = [["bg-IPA", "IPA"], "audio", "rhymes", ["bg-hyph", "hyph"]]

    get_precedence = lambda x: PRECEDENCE.index([item for item in PRECEDENCE if (x in item if type(item) is list else x == item)][0])

    for page, *_ in me.contributions(limit):
        title = page.title()
        print("Visiting", title)
        content = page.text
        parsed = mwparserfromhell.parse(content)
        bulgarian_section: mwparserfromhell.wikicode.Wikicode = parsed.get_sections([2], "Bulgarian")[0]
        pronunciation = bulgarian_section.get_sections([3], "Pronunciation")
        if not pronunciation: continue
        pronunciation: mwparserfromhell.wikicode.Wikicode = pronunciation[0]
        highest_precedence = 0
        for template in pronunciation.filter(forcetype=mwparserfromhell.wikicode.Template):
            try:
                template_precedence = get_precedence(str(template.name))
            except:
                template_precedence = -1
            if template_precedence > highest_precedence:
                highest_precedence = template_precedence
            elif template_precedence < highest_precedence:
                print("Entry is out of order:", title)
                disordered.append(title)
                break
    print(disordered)

def main():
    mode = len(sys.argv) > 1 and sys.argv[1] or "auto"

    if mode == "auto":
        auto_add()
    elif mode == "manual":
        manual()
    elif mode == "reorder":
        reorder()
    else:
        print("Unrecognized mode", mode)

if __name__ == "__main__":
    main()