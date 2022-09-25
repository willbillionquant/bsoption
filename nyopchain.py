import os
codepath = os.path.dirname(os.path.abspath(__file__))
import sys
sys.path.append('..')

from datetime import datetime
import numpy as np
import pandas as pd
from sqlalchemy import create_engine

from configparser import ConfigParser
configchain = ConfigParser()
configchain.read(os.path.join(codepath, 'setting_yahoochain.ini'))
chainpath = configchain['paths'].get('chainpath')

import logging
currenttime = datetime.now().strftime('%Y%m%d')
logchainpath = os.path.join(chainpath, 'logs')
if not os.path.exists(logchainpath):
    os.makedirs(logchainpath)

import yfinance as yf

logfile = os.path.join(logchainpath, f'yahoochain_{currenttime}.txt')
logging.basicConfig(filename=logfile, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class NYopchain():

    def __init__(self):
        self.engine = create_engine(f'sqlite:///{os.path.join(chainpath, "nyopchain.db")}')
        self.collist = ['tradedate', 'contract', 'asset', 'optype', 'expiry', 'strike',
                        'last', 'bid', 'ask', 'chg', 'pctchg', 'iv', 'vol', 'oi']

    def getopchainyahoo(self, asset):
        """Obtain most recent trading day option chain data from yahoo finance API."""
        Ticker = yf.Ticker(asset)
        expdaylist = Ticker.options
        df1d = Ticker.history(period='1d')
        lasttd = df1d.index[0].strftime('%Y-%m-%d')

        chaindict = {}
        for daystr in expdaylist:
            expday = datetime.strptime(daystr, '%Y-%m-%d')
            if expday.weekday() == 4:
                chainlist = Ticker.option_chain(daystr)
                dfcall = chainlist[0]
                dfcall['optype'] = 'C'
                dfput = chainlist[1]
                dfput['optype'] = 'P'
                renamedict = {'contractSymbol': 'contract', 'lastTradeDate': 'ltdate', 'lastPrice': 'last',
                              'change': 'chg', 'percentChange': 'pctchg', 'volume': 'vol', 'openInterest': 'oi',
                              'impliedVolatility': 'iv'}
                for df in [dfcall, dfput]:
                    df.drop(['inTheMoney', 'contractSize', 'currency'], axis=1, inplace=True)
                    df.rename(columns=renamedict, inplace=True)
                    df['asset'] = asset
                    df['expiry'] = expday
                dfchain = pd.concat([dfcall, dfput], axis=0)
                dfchain = dfchain[self.collist]
                for col in self.collist[5:]:
                    dfchain[col] = pd.to_numeric(dfchain[col])
                dfchain['chg'] = np.round(dfchain['chg'], 2)
                dfchain['pctchg'] = np.round(dfchain['pctchg'], 4)
                dfchain['iv'] = np.round(100 * dfchain['iv'], 2)
                dfchain['tradedate'] = lasttd
                dfchain.set_index('contract', inplace=True)
                dfchain.sort_index(inplace=True)
                chaindict[daystr] = dfchain

        return chaindict

    def loadopdata(self, inputdict):
        """Load option data of specific requirements."""

        with self.engine.connect() as con:
            pass

    def appendchaindict(self, chaindict):
        """Insert a dict of option chain at a day close into database."""
        with self.engine.connect() as con:
            for daystr, dfchain in chaindict.items():
                pass








