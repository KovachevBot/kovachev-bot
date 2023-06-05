# kovachev-bot
The source code for my Wiktionary bot, https://en.wiktionary.org/wiki/User:KovachevBot.
Each directory contains a distinct task that the bot is assigned and works largely independently of the others, so this repository is just a central location for all the different scripts.

# Run instructions
If you are unfamiliar with Pywikibot, please refer to the Wikimedia guide on using it. (https://www.mediawiki.org/wiki/Manual:Pywikibot)
Once you have installed Pywikibot, navigate to the installation directory and ensure any scripts you wish to run from here are put in the folder `<pywikibot path>/scripts/myscripts`. This is a default directory within which scripts can be recognised from the root of the pywikibot directory. Alternatively, this step can be skipped and the command `pwb <file name>` be run, as long as the path to the file is specified. 
Otherwise, simply run: `python pwb.py <script name>` from the terminal within the pywikibot root directory. You can omit the `.py` extension if running in this way.
