__version__ = 1

import os
import toolbox
import settings
from logger import Logger
from betfair.api_ng import API
from datetime import datetime, timedelta

class BetBot(object):
    """betfair bot"""
    def __init__(self):
        toolbox.bot = self # allow toolbox.py to reference this bot object
        self.settings_modtime = os.stat(settings.__file__).st_mtime
        self.logger = None # set in run() function
        self.api = None # set in run() function
        self.session = False # True when logged in to Betfair
        self.ignores = toolbox.load_ignores() # reload ignores from last run
        self.markets = {} # dict for preloaded markets. keys = market ids

    def get_next_five_markets(self, search = False):
        """returns upto 5 markets starting soon
        @search: type = boolean. if True, search 48hrs ahead to find next market.
        """
        # build the request
        utc_now = datetime.utcnow()
        start_date = utc_now
        end_date = utc_now + timedelta(seconds = settings.preload_time)
        if search:
            # search 48hrs ahead so bot can sleep until next market starts
            end_date = utc_now + timedelta(hours = 48)
        start_date = start_date.strftime('%Y-%m-%dT%H:%M:%SZ')
        end_date = end_date.strftime('%Y-%m-%dT%H:%M:%SZ')
        params = {
            'filter': {
                'eventTypeIds': settings.sport_ids, # e.g. 7 = Horse Racing
                'marketCountries': settings.countries, # e.g. GB & IE
                'marketTypeCodes': settings.market_types, # e.g. 'WIN' markets
                'marketBettingTypes': ['ODDS'],
                'bspOnly': True, # only BSP markets (Req'd for M.O.C. bets)
                'inPlayOnly': False, # market NOT currently in-play
                'marketStartTime': {
                    'from': start_date,
                    'to': end_date
                }
            },
            'marketProjection': [
                'EVENT',
                'RUNNER_DESCRIPTION',
                'MARKET_START_TIME'
            ],
            'maxResults': 100,
            'sort': 'FIRST_TO_START'
        }
        # send the request
        markets = self.api.get_markets(params)
        if type(markets) is list:
            # filter response
            for market in markets[:]: # loop through COPY so we can edit on-the-fly
                market_id = market['marketId']
                if market_id in self.ignores:
                    # remove this market
                    markets.remove(market)
            # return markets
            return markets[:5] # max length = 5 markets
        else:
            msg = 'api.get_markets() resp = %s' % markets
            raise Exception(msg)

    def preload_markets(self):
        """preload markets starting soon"""
        markets = self.get_next_five_markets()
        for market in markets:
            market_id = market['marketId']
            self.markets[market_id] = market

    def get_favourite(self, book = None):
        """returns favourite price & selection id from given market book
        @book: type = dict. info returned in get_market_books()
        """
        fav = None
        for runner in book['runners']:
            if (runner['status'] == 'ACTIVE' # not a NR
                and runner['ex']['availableToBack'] # back prices available
                ):
                back_price = runner['ex']['availableToBack'][0]['price']
                sel_id = runner['selectionId']
                if not fav:
                    # initiate dict
                    fav = {'price': back_price, 'sel_id': sel_id}
                else:
                    # check if this runner has shorter price
                    if back_price < fav['price']:
                        # set this runner as potential fav
                        fav = {'price': back_price, 'sel_id': sel_id}
        # append race info & fav name
        if fav:
            market_id = book['marketId']
            market = self.markets[market_id]
            venue_name = market['event']['venue']
            start_time = market['marketStartTime'].strftime('%H:%MGMT')
            for runner in market['runners']:
                if fav['sel_id'] == runner['selectionId']:
                    runner_name = runner['runnerName']
                    break
            fav['info'] = '%s %s - %s' % (venue_name, start_time, runner_name)
        return fav

    def check_bet_triggers(self):
        """check bet triggers & place bets"""
        bets = {} # placeholder for bets. keys = market ids, vals = list of bets
        # create list of market ids to request prices for
        market_ids = []
        for market_id in self.markets:
            # check if race start time reached
            market = self.markets[market_id]
            # NOTE: trigger time allows 1 sec to process get_market_books()
            trigger_time = market['marketStartTime'] - timedelta(seconds = 1)
            if datetime.utcnow() >= trigger_time:
                # race due off any second now...
                market_ids.append(market_id)
        # get market books
        if market_ids:
            msg = 'Checking bet triggers...\n'
            msg += 'Market Ids: %s' % market_ids
            self.logger.xprint(msg)
            books = toolbox.get_market_books(market_ids)
            for book in books:
                if (book['status'] == 'OPEN'
                    and book['inplay'] == False # NOT inplay
                    ):
                    market_id = book['marketId']
                    # identify favourite
                    fav = self.get_favourite(book)
                    # check if fav price matches triggers
                    if (fav['price'] >= settings.min_price
                        and fav['price'] <= settings.max_price
                        ):
                        # fav matches price triggers - create bet
                        bet = {}
                        bet['selectionId'] = fav['sel_id']
                        bet['side'] = 'BACK'
                        bet['orderType'] = 'LIMIT'
                        bet['limitOrder'] = {
                            'size': '%.2f' % settings.stake,
                            'price': '%.2f' % fav['price'],
                            'persistenceType': 'MARKET_ON_CLOSE'
                        }
                        # notify user
                        order = bet['limitOrder']
                        msg = 'BET CREATED: %s' % fav['info']
                        # msg += ' - %s \xA3%s @ %s' % (bet['side'], order['size'], order['price'])
                        if settings.TEST_MODE:
                            msg += '\n*** TEST MODE - NO BETS WILL BE PLACED ***'
                        self.logger.xprint(msg)
                        # add to bets dict
                        if market_id not in bets:
                            bets[market_id] = [] # create empty list for bets
                        bets[market_id].append(bet)
                    else:
                        # fav DOES NOT match price triggers - add to ignores
                        reason = 'BET_TRIGGERS_NOT_MATCHED'
                        toolbox.update_ignores(market_id, reason)
        # place bets?
        if bets:
            if not settings.TEST_MODE:
                # 'LIVE' bot - place bets
                toolbox.place_bets(bets)
            # add markets to ignores if place_bets() did not raise errors
            for market_id in bets:
                reason = 'BETS_PLACED'
                if settings.TEST_MODE:
                    reason += " (NOT REALLY - WE'RE IN TEST MODE!)"
                toolbox.update_ignores(market_id, reason)

    def purge_preloaded_markets(self):
        """remove ignored market ids from self.markets"""
        market_ids = list(self.markets.keys())
        for market_id in market_ids:
            if market_id in self.ignores:
                self.markets.pop(market_id)

    def wait_for_markets(self):
        """sleep until markets are available.
        saves bandwidth
        """
        if len(self.markets) == 0:
            # check what time next market starts
            markets = self.get_next_five_markets(True) # search next 48hrs
            next_market = markets[0]
            start_time = next_market['marketStartTime']
            wake_time = start_time - timedelta(seconds = settings.preload_time)
            time_diff = wake_time - datetime.utcnow()
            sleep_time = time_diff.total_seconds()
            if sleep_time > 0:
                # sleep until next market is near start time
                str_start_time = start_time.strftime('%d-%m-%Y %H:%M:%S GMT')
                str_wake_time  = wake_time.strftime('%d-%m-%Y %H:%M:%S GMT')
                msg = 'Next market starts: %s\n' % str_start_time
                msg += 'SLEEPING until:     %s' % str_wake_time
                self.logger.xprint(msg)
                # go to sleep, but keep login session alive
                while datetime.utcnow() < wake_time:
                    toolbox.sleep(1) # save some CPU cycles!
                    toolbox.keep_alive()
                    toolbox.reload_settings()
                # wake up...
                msg = 'WAKING UP...'
                self.logger.xprint(msg)

    def run(self, aus = False):
        # create the API object
        self.username = settings.username
        self.api = API(aus, ssl_prefix = self.username)
        self.api.app_key = settings.app_key
        self.logger = Logger(aus)
        self.logger.bot_version = __version__
        # login to betfair api-ng
        toolbox.do_login(settings.username, settings.password)
        # start the bot loop
        while self.session:
            # ensure we don't exceed data request limits
            toolbox.do_throttle()
            # maintain login session
            toolbox.keep_alive()
            # check settings.py & reload if file has been edited
            toolbox.reload_settings()
            # remove closed markets from ignores
            toolbox.update_ignores()
            # wait for new markets
            self.wait_for_markets()
            # preload markets ready for betting (i.e. markets starting soon)
            self.preload_markets()
            # check bet triggers & place bets
            self.check_bet_triggers()
            # cleanup preloaded markets
            self.purge_preloaded_markets()

