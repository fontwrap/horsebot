"""betfair bot manager"""
import settings
import traceback
from time import sleep
from sys import argv, exit

AUS = False # default to UK betting exchange

# simplify common error messages
ERRORS = [
    'ConnectTimeoutError',
    'ReadTimeoutError',
#    'APINGException',
    'Connection aborted'
]

# initiate bot
while True: # loop forever
    try:
        from horsebot import BetBot
        from logger import Logger
        log = Logger(AUS)
        log.xprint('STARTING BOT...')
        # create bot object & start bot
        bot = BetBot()
        bot.run(AUS)
    except Exception as exc:
        from logger import Logger
        log = Logger(AUS)
        msg = traceback.format_exc()
        for err in ERRORS:
            if err in msg:
                msg = 'ERROR: %s' % err
                break
        msg = '#### BOT CRASH ####\n%s' % msg
        log.xprint(msg, True) # print to err_log.txt
        if settings.exit_on_error: exit()
    sleep(5) # give errors time to clear
