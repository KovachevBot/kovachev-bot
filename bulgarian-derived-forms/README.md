# Bulgarian Derived form generator
The purpose of this script is to automatically generate Bulgarian derived form entries from nouns' declension tables.
It was developed in 2021 to improve the coverage of non-lemma forms of Bulgarian nouns, however was not approved by consensus and hence did not make it to deployment.
One reason for this was that most noun forms are straightforward sum-of-parts suffixations of the base noun, hence the expansion did not provide
much benefit whilst remaining a complex and error-prone task.

## Function
The exact method of operation is described by the code itself, but the gist is the following:
- The noun lemma is found and the relevant declension table section is expanded to its HTML/Wikicode form.
- The declension data is interpreted depending on the specific labels and values in the table.
- Entries that correspond to each declension are generated and appended to their respectively-titled pages.
