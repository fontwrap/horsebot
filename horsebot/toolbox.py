import os
import imp
import pickle
import settings
from time import time, sleep

throttle = {
    'wait': 1.0, # seconds between requests
    'next': time(),
    'keep_alive': time() + 900, # 15 mins from now
    'update_closed': time() + 3600 # 1hr from now
}
abs_path = os.path.abspath(os.path.dirname(__file__))
ignores_path = abs_path + '/ignores.pkl'

def load_ignores():
    """unpickle ignores file"""
    ignores = unpickle_file(ignores_path, list())
    return ignores

def pickle_data(filepath = '', data = None):
    """pickle data"""
    try:
        f = open(filepath, 'wb')
        pickle.dump(data, f)
        f.close()
    except:
        pass

def unpickle_file(filepath = '', obj_type = None):
    """unpickle file. returns object.
    if file doesn't exist, returns obj_type (list, dict, etc)
    """
    if os.path.exists(filepath):
        f = open(filepath, 'rb')
        data = pickle.load(f)
        f.close()
        return data
    return obj_type # empty list, dict, etc

def do_throttle():
    """return when it's safe to continue"""
    now = time()
    if now < throttle['next']:
        wait = throttle['next'] - now
        sleep(wait)
    throttle['next'] = time() + throttle['wait']
    return

def update_ignores(market_id = '', reason = ''):
    """update ignores list"""
    if market_id:
        # add market to ignores dict
        if market_id not in bot.ignores:
            bot.ignores.append(market_id)
            pickle_data(ignores_path, bot.ignores)
            # log reason
            msg = 'Market %s IGNORED. Reason = %s' % (market_id, reason)
            bot.logger.xprint(msg)
    else:
        # check for closed markets periodically
        count = len(bot.ignores)
        now = time()
        if count > 0 and now > throttle['update_closed']:
            throttle['update_closed'] = now + 3600 # 1hr from now
            msg = 'Purging ignores list...'
            bot.logger.xprint(msg)
            for i in range(0, count, 5):
                market_ids = bot.ignores[i:i+5] # list of upto 5 market ids
                do_throttle()
                books = get_market_books(market_ids)
                for book in books:
                    if book['status'] == 'CLOSED':
                        # remove from ignores
                        market_id = book['marketId']
                        bot.ignores.remove(market_id)
                        pickle_data(ignores_path, bot.ignores)

def do_login(username = '', password = ''):
    """login to betfair & set session status"""
    msg = 'Logging in to Betfair API-NG...'
    bot.logger.xprint(msg)
    bot.session = False
    resp = bot.api.login(username, password)
    if resp == 'SUCCESS':
        # login OK
        bot.session = True
        msg = 'Login: SUCCESS'
        bot.logger.xprint(msg)
    else:
        # login failed
        bot.session = False
        msg = 'Login: FAIL...\n %s' % resp
        raise Exception(msg)

def keep_alive():
    """refresh login session. sessions expire after 20 mins.
    NOTE: betfair throttle = max 1 req every 7 mins
    """
    now = time()
    if now > throttle['keep_alive']:
        # refresh
        resp = bot.api.keep_alive()
        if resp == 'SUCCESS':
            throttle['keep_alive'] = now + 900 # add 15 mins
            bot.session = True
            msg = 'Keep-Alive: SUCCESS'
            bot.logger.xprint(msg)
        else:
            msg = 'api.keep_alive() resp = %s' % resp
            raise Exception(msg)

def reload_settings():
    """reload settings file if it has been modified"""
    modtime = os.stat(settings.__file__).st_mtime
    if modtime > bot.settings_modtime:
        # settings file has been modified...
        imp.reload(settings)
        bot.settings_modtime = modtime
        msg = 'SETTINGS MODULE RELOADED'
        bot.logger.xprint(msg)

def get_market_books(market_ids = None):
    """returns a list of prices for given market ids
    NOTE: maximum = 5 markets per request
    """
    market_ids = market_ids[:5] # force max length = 5
    price_data = ['EX_BEST_OFFERS'] # top 3 prices
    virtual = True # include virtual prices
    market_books = bot.api.get_market_books(market_ids, price_data, virtual) # upto 5 markets in one hit
    if type(market_books) is list:
        return market_books
    else:
        msg = 'api.get_market_books() resp = %s' % markets
        raise Exception(msg)

def place_bets(market_bets = None):
    """loop through markets and place bets
    @market_bets: type = dict
    """
    for market_id in market_bets:
        bets = market_bets[market_id]
        if bets:
            bet_count = len(bets)
            text = 'BET'
            if bet_count > 1: text = 'BETS'
            msg = 'PLACING %s %s ON MARKET %s...' % (bet_count, text, market_id)
            for bet in bets:
                msg += '\n%s' % bet
            msg += '\n'
            do_throttle() # max 5 bets per second!
            resp = bot.api.place_bets(market_id, bets)
            if type(resp) is dict and 'status' in resp:
                if resp['status'] == 'SUCCESS': # ALL bets were placed
                    bet_ids = []
                    for bet in resp['instructionReports']:
                        bet_ids.append(bet['betId'])
                    msg += 'Result: SUCCESS\n'
                    msg += 'Bet Ids: %s' % bet_ids
                    bot.logger.xprint(msg)
                else:
                    msg += 'Result: FAIL (%s)\n' % resp['errorCode']
                    msg += 'API-NG RESPONSE: %s' % resp
                    raise Exception(msg)
            else:
                msg += 'Result: FAIL\n%s' % resp
                raise Exception(msg)
