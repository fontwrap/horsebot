1. Before running the bot, you will need to:
    * copy your ssl '.key' and '.crt' files into the betfair/ssl_certs folder
    * edit settings.py, entering your username, password & app key
    * edit the bet triggers in settings.py to your requirements

2. To run the bot, launch manager.py. The preference is to do this from a
   command terminal. Assuming that manager.py is located in your HOME folder,
   inside a folder named 'horsebot', the command would be:
   'python horsebot/manager.py'

3. To stop the bot running, the easiest way is to kill the process from a
   command terminal:
   'ps x' # lists running processes
   'kill N' # where 'N' is the process id number (first number on the left)

4. The bot is currently setup in 'TEST MODE'. No bets will be placed until
   settings.py is edited so that TEST_MODE = False

5. When you've finished programming and are ready for the bot to run 24/7,
   change exit_on_error to False in settings.py. You will see some common errors
   such as 'ConnectTimeoutError' - these are caused by http/server errors, most
   often at Betfair's end, especially at peak times. More detailed errors may
   require investigation as they could be due to bugs in your bot code.

6. The bot will sleep between markets to save bandwidth & data requests. This
   is most useful if you leave the bot running 24/7 (e.g. on a VPS server) and
   there are no more races for several hours.

7. The bot has been developed using Python 3.2 on Debian Wheezy. It should
   run fine with Python 2.7.9 (Debian Jessie?), but if you encounter any errors,
   please let me know.

8. When coding in Python, using print() and exit() statements are a handy way
   to test code. e.g.
   my_var = 'hello!'
   print(my_var)
   exit() # this will stop the bot

9. Betfair set all times to UTC/GMT. The bot uses your PC time in UTC to check
   the current time, therefore you need to make sure your PC clock is synchronised
   with an NTP time server. You can install this using Synaptic Package Manager
   OR run the following commands in a terminal:
   'su' # login as root user (admin)
   <enter root password>
   'aptitude install ntp'
   'exit' # logout of root account

10. My preferred Python editor is called Editra. You can install this from the
    Synaptic Package Manager and set it up as a Python IDE:
    http://www.editra.org/setup_python_ide

11. Note that if placing M.O.C. (MarketOnClose) bets, your bets will revert to
    BSP bets IF they are unmatched when the market goes inplay. Betfair have
    minimum stake limits of £2 for Back bets and £10 for Lay bets.
