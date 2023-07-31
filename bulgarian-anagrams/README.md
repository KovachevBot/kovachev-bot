# Bulgarian anagram script
This script goes through the word list found in this directory, `words.txt`, and calculates the alphagram—i.e. the sorted list of letters, e.g. for 'mouse', 'emosu'—for each word, and associates it as a set of words that share this alphagram, inside of a dictionary (`anagrams`). E.g. the dictionary's entry for "бор" is {"бор", "роб"}.

Then, for each of these words, it goes to the Wiktionary entry for that word and adds all of its other anagrams.
We make sure also to append the Anagrams section after every other section under the L2 Bulgarian header, but before any categories or categorisation templates placed at the end; I do this with the help of JeffDoozan's regex for categories, and traverse from the bottom of the Bulgarian section until all the categories have been surpassed and we can safely place the section.

The data for this is sourced from the database from rechnik.chitanka.info, which is very expansive and contains over 120k words.
However, many of these are obscure and not even defined in their system, so there are concerns about the validity of some anagrams.
The total number of unique alphagrams (excluding those with only 1 corresponding word, i.e. useless for this project) was 3944.