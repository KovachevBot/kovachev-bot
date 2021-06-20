# kovachev-bot

The source code for my Wiktionary bot, https://en.wiktionary.org/wiki/User:KovachevBot. The purpose of the bot is to automatically generate Bulgarian derived form entries from nouns' declension tables. 
You can peer into my abominable coding practices if you wish, and can verify that I won't try to obliterate the entire platform without compunction... I'd also like to apologise for naming the bot after myself, but the Wiktionary policy made me do it :x

Please see the bot's user page if you need more specifics as to the purpose and function of the bot.

# Run instructions

If you are unfamiliar with Pywikibot, please refer to the Wikimedia guide on using it. (https://www.mediawiki.org/wiki/Manual:Pywikibot)
Once you have installed Pywikibot, navigate to the pywikibot directory (wherever you installed it, in my case inside the Documents folder) and go to pywikibot/scripts/userscripts, placing the test.py source file in there (you can reanme it if you like, doesn't matter) and then returning back to pywikibot. If in command line, i.e., one can type cd ../.. from the userscripts folder.
Then, simply run: `python pwb.py test.py` from the terminal, and the script should work as intended. Prerequisites for running also include the `wikitextparser` and `mwparserfromhell` libraries (`pip install mwparserfromhell wikitextparser`).

# Output

I have currently configured the script to also generate text files as output so that one can see what the output would look like if the bot were allowed to edit the pages as I have it configured.
If you want to demonstrate this for yourself, please comment out the part where it saves its changes: `derivative_page.save(save_message)`. I would also recommend commenting out the check that halts the generation if a Bulgarian entry already exists, as the majority of the first entries in the Nouns category are already complete with derived forms.
