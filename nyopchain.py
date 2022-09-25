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
        self.displayfieldstr = 'tradedate, asset, optype, expiry, strike, bid, ask'

    def getopchainyahoo(self, asset):
        """Obtain most recent trading day option chain data from yahoo finance API."""
        Ticker = yf.Ticker(asset)
        expdaylist = Ticker.options
        df1d = Ticker.history(period='1d')
        lasttd = df1d.index[0].strftime('%Y-%m-%d')

        dfchainall = pd.DataFrame()
        for daystr in expdaylist:
            expday = datetime.strptime(daystr, '%Y-%m-%d')
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
            dfchainall = pd.concat([dfchainall, dfchain], axis=0)

        return dfchainall

    def appendchaindf(self, dfchain):
        """Insert a dataframe of option chain."""
        assetlist = dfchain['asset'].unique()
        with self.engine.connect() as con:
            for asset in assetlist:
                dfchain1 = dfchain[dfchain['asset'] == asset]
                dfchain1.to_sql(asset, con=con, if_exists='append')


    def loadopdata(self, inputdict):
        """Load option data of specific requirements."""

        stmt_selectfinal = ""
        for month in inputdict['month']:
            stmt_selectcontract = \
                f"SELECT {prefixfieldstr}, {fieldstrdict[inputdict['style']]}, {', '.join(oilist)} \
                FROM `{inputdict['asset']}` \
                WHERE `asset` = '{inputdict['asset']}' \
                AND ((`optype` = '{inputdict['optype'][0]}') OR (`optype` = '{inputdict['optype'][1]}')  ) \
                AND `strike` between {inputdict['strike_lowerbound']} and {inputdict['strike_upperbound']} \
                AND `tradedate` between '{getdayslater(inputdict['startdate'])}' and '{getdayslater(inputdict['enddate'], 1)}'"
            stmt_selectfinal += f" UNION {stmt_selectcontract}"
        stmt_selectfinal += f" ORDER BY {', '.join(orderfield)}"



        with self.engine.connect() as con:
            pass






