# Japanese yomi removal script
This script is intended to traverse the tracking template/category https://en.wiktionary.org/wiki/Special:WhatLinksHere/Template:tracking/ja-pron/yomi on the English Wiktionary.
We recently removed the `yomi` (alias: `y`) parameter from the pronunciation template {{ja-pron}}, so this script is intended to remove all occurrences of this
now-deprecated and unnecessary parameter from entries in this category.

## Method of operation
The script iterates over all the entries in this category, then performs a simple substitution to get rid of the yomis for each occurrence of
{{ja-pron}}.
The regular expression that does this is: `({{ja-pron(?:\|[^\|]+?=[^\|]+?|\|[^\|]+)*?)\|(?:y|yomi)=(?:o|on|go|goon|ko|kan|kanon|so|soon|to|toon|ky|kanyo|kanyoon|k|kun|j|ju|y|yu|i|irr|irreg|irregular)((?:\|[^\|]+?=[^\|]+?|\|[^\|]+)*}})`
You will see two capturing groups, one before the "yomi" portion, and one after; given that these two together comprise the entire template and its arguments,
except for the yomi argument, we simply replace any match for this pattern with the two matching groups concatenated together,
e.g. if we have `{{ja-pron|しょう|y=kan|acc=0}}`, the match would contain the two subgroups  `{{ja-pron|しょう` and `|acc=0}}`, so when we put them
together, we get `{{ja-pron|しょう|acc=0}}`, and in this way the yomi is removed.

## Method to guarantee no malfunction
Although I believe the script to have no flaws, it is natural for an unforeseen bug to potentially occur, especially with a complicated regex
like this. The safeguard I have is to check the page text before and after editing: we expect all the {{ja-pron}}s to stay in the same order
that they were originally, since my script doesn't change the fundamental arrangement of the page, but with each one having one less argument
(determinable by counting the number of |s) than it did before the edit. We assert this every single time an edit is made, so that if this invariant
is somehow broken, and an error must have occurred somewhere, the program will halt immediately and before making the edit at all.
