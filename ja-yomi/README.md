# Japanese yomi removal script
This script is intended to traverse the tracking template/category https://en.wiktionary.org/wiki/Special:WhatLinksHere/Template:tracking/ja-pron/yomi on the English Wiktionary.
We recently removed the `yomi` (alias: `y`) parameter from the pronunciation template {{ja-pron}}, so this script is intended to remove all occurrences of this
now-deprecated and unnecessary parameter from entries in this category.

## Method of operation
The script iterates over all the entries in this category, then performs a simple API call in `mwparserfromhell` to get rid of the yomis for each occurrence of {{ja-pron}}.
The way this is done is to iterate over all templates (`for template in parsed.ifilter(forcetype=Template, recursive=False)`) and, for any one whose
name is `ja-pron`, remove any `y` or `yomi` parameters if they exist.
```
    for template in parsed.ifilter(forcetype=Template, recursive=False):
        if template.name != "ja-pron":
            continue

        if template.has("y"):
            template.remove("y")
        if template.has("yomi"):
            template.remove("yomi")
```

## Method to guarantee no malfunction
The safeguard I have is to check the page text before and after editing: we expect all the {{ja-pron}}s to stay in the same order
that they were originally, since my script doesn't change the fundamental arrangement of the page, but with each one having one less argument
(determinable by counting the number of |s) than it did before the edit. We assert this every single time an edit is made, so that if this invariant
is somehow broken, and an error must have occurred somewhere, the program will halt immediately and before making the edit at all.
I also make use of backups using Python's `difflib`, which creates unified diff files for every edit that is made, which is then stored to disk.
If there arises any issue with the bot's edits, these can be used to undo them.
