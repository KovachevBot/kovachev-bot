# Running help
In order to run the script, first of all see the uppermost README for details.
Secondly, in order to run this particular script, you will require the JSON data I am using.
The content is not included here out of compliance with copyright restrictions,
but are accessible through https://anacreondjt.gitlab.io/docs/dicts/. Check the first link on the page;
if there is no MEGA link, check the Wayback machine on today's date, 10 July 2023.
You need the file at `yomichan/（三省堂）スーパー大辞林［3.0］.zip` (i.e. in the `yomichan` folder, 
then see the relevant file.) Extract the zip once downloaded. Wherever you decide to put the extracted
`term_bank_1.json` file, take note of its path and write that as the value of `DJR_DATA_FILE` in `daijirin.py`:
this file will be loaded at runtime to access the dictionary data.
