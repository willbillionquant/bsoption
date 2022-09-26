import os
codepath = os.path.dirname(os.path.abspath(__file__))
import sys
sys.path.append('..')

from datetime import datetime, timedelta
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

def getdayslater(date='2022-01-01', numday=0):
    """Obtain datestring format in the form '%Y-%m-%d %H:%M:%S:%f'."""
    afterdate = datetime.strptime(date, '%Y-%m-%d') + timedelta(days=numday) - timedelta(seconds=1)
    afterstr = afterdate.strftime('%Y-%m-%d %H:%M:%S:%f')
    return afterstr

class NYopchain():

    def __init__(self):
        self.engine = create_engine(f'sqlite:///{os.path.join(chainpath, "nyopchain.db")}')
        self.collist = ['tradedate', 'asset', 'optype', 'expiry', 'strike', 'iv', 'vol', 'oi', 'last', 'bid', 'ask', 'mid']
        self.colstr = '`' + '`, `'.join(self.collist) + '`'

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
            renamedict = {'lastPrice': 'last', 'volume': 'vol', 'openInterest': 'oi', 'impliedVolatility': 'iv'}
            for df in [dfcall, dfput]:
                df.drop(['contractSymbol', 'lastTradeDate', 'inTheMoney', 'contractSize', 'currency', 'change',
                         'percentChange'],
                        axis=1, inplace=True)
                df.rename(columns=renamedict, inplace=True)
                df['asset'] = asset
                df['expiry'] = expday
            dfchain = pd.concat([dfcall, dfput], axis=0)
            dfchain['tradedate'] = lasttd
            dfchain['tradedate'] = pd.to_datetime(dfchain['tradedate'])
            dfchain = dfchain[self.collist[:-1]]
            for col in self.collist[4:-1]:
                dfchain[col] = pd.to_numeric(dfchain[col])
            dfchain['mid'] = (dfchain['bid'] + dfchain['ask']) / 2
            dfchain['iv'] = np.round(100 * dfchain['iv'], 2)
            dfchain.sort_values(['optype', 'strike'], inplace=True)
            dfchainall = pd.concat([dfchainall, dfchain], axis=0)

        return dfchainall

    def appendchaindf(self, dfchain):
        """Insert a dataframe of option chain."""
        assetlist = dfchain['asset'].unique()
        with self.engine.connect() as con:
            for asset in assetlist:
                dfchain1 = dfchain[dfchain['asset'] == asset]
                dfchain1.to_sql(asset, con=con, if_exists='append', index=False)

    def loadopdata(self, inputdict, orderfield=('tradedate', 'optype', 'strike',)):
        """Load option data of specific requirements."""
        stmtselect = f" SELECT {self.colstr} FROM `{inputdict['asset']}` \
                        WHERE ((`optype` = '{inputdict['optype'][0]}') OR (`optype` = '{inputdict['optype'][1]}')) \
                        AND `strike` between {inputdict['strike_lowerbound']} and {inputdict['strike_upperbound']} \
                        AND `expiry` between '{getdayslater(inputdict['startexpiry'])}' \
                        and '{getdayslater(inputdict['endexpiry'], 1)}' \
                        AND `tradedate` between '{getdayslater(inputdict['starttd'])}' \
                        and '{getdayslater(inputdict['endtd'], 1)}' \
                        ORDER BY {', '.join(orderfield)}"

        with self.engine.connect() as con:
            result = con.execute(stmtselect).fetchall()

        dfdata = pd.DataFrame(result, columns=self.collist)

        for col in ['tradedate', 'expiry']:
            dfdata[col] = pd.to_datetime(dfdata[col])

        for col in self.collist[4:]:
            dfdata[col] = pd.to_numeric(dfdata[col])

        return dfdata