from collections import defaultdict
import json
import unicodedata
import regex as re

GRAVE = chr(0x300)
ACUTE = chr(0x301)
BREVE = chr(0x306)
TIE   = chr(0x361)
PRIMARY = chr(0x2C8)
SECONDARY = chr(0x2CC)
TIE = chr(0x361)
FRONTED = chr(0x31F)
DOTUNDER = chr(0x323)
HYPH = chr(0x2027)

vowels = "aɤɔuɛiɐo"
vowels_c = f"[{vowels}]"
vowels_g = "[аъоуеияѝюАЪОУЕИЯЍЮ]"
cons = f"bvɡdʒzjklwmnprstfxʃɣʲ{TIE}"
cons_c = f"[{cons}]"
voiced_cons = f"bvɡdʒzɣ{TIE}"
voiced_cons_c = f"[{voiced_cons}]"
accents = PRIMARY + SECONDARY
accents_c = f"[{accents}]"

phonetic_chars_map = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "ɡ",
    "д": "d",
    "е": "ɛ",
    "ж": "ʒ",
    "з": "z",
    "и": "i",
    "й": "j",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "ɔ",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ў": "w",
    "ф": "f",
    "х": "x",
    "ц": f"t{TIE}s",
    "ч": f"t{TIE}ʃ",
    "ш": "ʃ",
    "щ": "ʃt",
    "ъ": "ɤ",
    "ь": "ʲ",
    "ю": "ʲu",
    "я": "ʲa",
    GRAVE: SECONDARY,
    ACUTE: PRIMARY
}

devoicing = {
    "b": "p", "d": "t", "ɡ": "k",
    "z": "s", "ʒ": "ʃ",
    "v": "f"
}

voicing = {
    "p": "b", "t": "d", "k": "ɡ",
    "s": "z", "ʃ": "ʒ", "x": "ɣ",
    "f": "v"
}

def count_vowels(word):
    vowel_count = len(re.findall(vowels_g, word))
    return vowel_count


IPA_prefixes = ["bɛz", "vɤz", "vɤzproiz", "iz", "naiz", "poiz", "prɛvɤz", "proiz", "raz"]


def rsub(word: str, pattern: str, repl) -> str:
    if isinstance(repl, dict):
        transl = lambda m: m.group(0).translate(str.maketrans(repl))
        return re.sub(pattern, transl, word)
    else:
        return re.sub(pattern, repl, word)


def rsub_repeatedly(word: str, pattern: str, repl) -> str:
    old = ""
    while old != word:
        old = word
        word = rsub(word, pattern, repl)
    return word


def rmatch(word: str, pattern: str) -> list[str]:
    comp = re.compile(pattern)
    m = comp.match(word)
    if m:
        return m.groups()
    else:
        return [None for _ in range(comp.groups)]


def toIPA(term, endschwa=False):
    origterm = term
    term = unicodedata.normalize("NFD", term.lower())
    term = rsub(term, "у" + BREVE, "ў") # recompose ў
    term = rsub(term, "и" + BREVE, "й") # recompose й
    
    if term.find(GRAVE) != -1 and not term.find(ACUTE):
        raise ValueError(f"Use acute accent, not grave accent, for primary stress: {origterm}")

    # allow DOTUNDER to signal same as endschwa=1    
    term = rsub(term, f"а({accents_c}?){DOTUNDER}", "ъ\\1")
    term = rsub(term, f"я({accents_c}?){DOTUNDER}", "ʲɤ\\1")
    term = rsub(term, ".", phonetic_chars_map)

    # Mark word boundaries
    term = rsub(term, r"(\s+)", "#\\1#")
    term = f"#{term}#"

    # Convert verbal and definite endings
    if endschwa:
        term = rsub(term, "a(" + PRIMARY + "t?#)", "ɤ\\1")

    # Change ʲ to j after vowels or word-initially
    term = rsub(term, "([" + vowels + "#]" + accents_c + "?)ʲ", "\\1j")

    ########## Move stress #######-

    # First, move leftwards over the vowel.
    term = rsub(term, "(" + vowels_c + ")(" + accents_c + ")", "\\2\\1")
    # Then, move leftwards over j or soft sign.
    term = rsub(term, "([jʲ])(" + accents_c + ")", "\\2\\1")
    # Then, move leftwards over a single consonant.
    term = rsub(term, "(" + cons_c + ")(" + accents_c + ")", "\\2\\1")
    # Then, move leftwards over Cl/Cr combinations where C is an obstruent (NOTE: IPA ɡ).
    term = rsub(term, "([bdɡptkxfv]" + ")(" + accents_c + ")([rl])", "\\2\\1\\3")
    # Then, move leftwards over kv/gv (NOTE: IPA ɡ).
    term = rsub(term, "([kɡ]" + ")(" + accents_c + ")(v)", "\\2\\1\\3")
    # Then, move leftwards over sC combinations, where C is a stop or resonant (NOTE: IPA ɡ).
    term = rsub(term, "([sz]" + ")(" + accents_c + ")([bdɡptkvlrmn])", "\\2\\1\\3")
    # Then, move leftwards over affricates not followed by a consonant.
    term = rsub(term, "([td]" + TIE + "?)(" + accents_c + ")([szʃʒ][" + vowels + "ʲ])", "\\2\\1\\3")
    # If we ended up in the middle of a tied affricate, move to its right.
    term = rsub(term, "(" + TIE + ")(" + accents_c + ")(" + cons_c + ")", "\\1\\3\\2")
    # Then, move leftwards over any remaining consonants at the beginning of a word.
    term = rsub(term, "#(" + cons_c + "*)(" + accents_c + ")", "#\\2\\1")
    # Then correct for known prefixes.
    for prefix in IPA_prefixes:
        prefix_prefix, prefix_final_cons = rmatch(prefix, "^(.*?)(" + cons_c + "*)$")
        if prefix_final_cons:
            # Check for accent moved too far to the left into a prefix, e.g. безбрачие accented as беˈзбрачие instead
            # of безˈбрачие
            term = rsub(term, "#(" + prefix_prefix + ")(" + accents_c + ")(" + prefix_final_cons + ")", "#\\1\\3\\2")


    # Finally, if there is an explicit syllable boundary in the cluster of consonants where the stress is, put it there.
    # First check for accent to the right of the explicit syllable boundary.
    term = rsub(term, "(" + cons_c + "*)\\.(" + cons_c + "*)(" + accents_c + ")(" + cons_c + "*)", "\\1\\3\\2\\4")
    # Then check for accent to the left of the explicit syllable boundary.
    term = rsub(term, "(" + cons_c + "*)(" + accents_c + ")(" + cons_c + "*)\\.(" + cons_c + "*)", "\\1\\3\\2\\4")
    # Finally, remove any remaining syllable boundaries.
    term = rsub(term, "\\.", "")

    ########## Vowel reduction (in unstressed syllables) #######-
    def reduce_vowel(vowel):
        return rsub(vowel, "[aɔɤu]", { "a": "ɐ", "ɔ": "o", "ɤ": "ɐ", "u": "o" })

    # Reduce all vowels before the stress, except if the word has no accent at all. (FIXME: This is presumably
    # intended for single-syllable words without accents, but if the word is multisyllabic without accents,
    # presumably all vowels should be reduced.)
    def reduce_overall(m):
        a, b = m.groups()
        if count_vowels(origterm) <= 1:
            return a + b
        else:
            return reduce_vowel(a) + b

    term = rsub(term, "(#[^#" + accents + "]*)(.*?#)", reduce_overall)

    # Reduce all vowels after the accent except the first vowel after the accent mark (which is stressed).
    term = rsub(term, "(" + accents_c + "[^aɛiɔuɤ#]*[aɛiɔuɤ])([^#" + accents + "]*)", lambda m:  m.group(1) + reduce_vowel(m.group(2)))

    ########## Vowel assimilation to adjacent consonants (fronting/raising) #######-
    term = rsub(term, "([ʃʒʲj])([aouɤ])", "\\1\\2" + FRONTED)

    # Hard l
    term = rsub_repeatedly(term, "l([^ʲɛi])", "ɫ\\1")


    # Voicing assimilation
    term = rsub(term, "([bdɡzʒv" + TIE + "]*)(" + accents_c + "?[ptksʃfx#])", lambda m: rsub(m.group(1), ".", devoicing) + m.group(2))
    term = rsub(term, "([ptksʃfx" + TIE + "]*)(" + accents_c + "?[bdɡzʒ])", lambda m: rsub(m.group(1), ".", voicing) + m.group(2))
    term = rsub(term, "n(" + accents_c + "?[ɡk]+)", "ŋ\\1")
    term = rsub(term, "m(" + accents_c + "?[fv]+)", "ɱ\\1")

    # Sibilant assimilation
    term = rsub(term, "[sz](" + accents_c + "?[td]?" + TIE + "?)([ʃʒ])", "\\2\\1\\2")

    # Reduce consonant clusters
    term = rsub(term, "([szʃʒ])[td](" + accents_c + "?)([tdknml])", "\\2\\1\\3")

    # Strip hashes
    term = rsub(term, "#", "")
    
    return term


def get_rhyme(term: str) -> str:
    def get_rhyme_ipa(ipa: str):
        stress_index = ipa.rindex(PRIMARY)
        rhyme_start_index = stress_index
        while rhyme_start_index < len(ipa) and not re.match(vowels_c, ipa[rhyme_start_index]):
            rhyme_start_index += 1
        
        return f"{ipa[rhyme_start_index:]}"

    return get_rhyme_ipa(toIPA(term))


# Each possible rhyme (suffix) will have a list of member words
rhymes: dict[str, list[str]] = defaultdict(list)

# Issues to consider:
#  - Terms that end in a stressed vowel
#  - Terms that have more than one word (space or hyphen)
#  - Whether to include fronting in the IPA transcription
with open("out/words.txt") as f:
    for line in f:
        line = line.strip().replace("`", ACUTE)
        if ACUTE not in line:
            if count_vowels(line) == 1:
                line = re.sub(f"({vowels_g})", "\\1" + ACUTE, line)
            else:
                continue
        
        if re.search(f"{vowels_g}{ACUTE}$"):
            continue

        rhyme = get_rhyme(line)
        rhymes[rhyme].append(line)

rhymes = {key: value for (key, value) in rhymes.items() if len(value) >= 3}
with open("rhymes.json", "w") as f:
    json.dump(rhymes, f, ensure_ascii=False)
