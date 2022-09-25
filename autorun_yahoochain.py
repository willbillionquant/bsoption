import os
codepath = os.path.dirname(os.path.abspath(__file__))
import sys
sys.path.append('..')

from datetime import datetime
import numpy as np
import pandas as pd
from pandas import ExcelWriter

import yfinance as yf

from configparser import ConfigParser
configchain = ConfigParser()
configchain.read(os.path.join(codepath, 'setting_yahoochain.ini'))
chainpath = configchain['paths'].get('chainpath')

import logging
currenttime = datetime.now().strftime('%Y%m%d')
logchainpath = os.path.join(chainpath, 'logs')
if not os.path.exists(logchainpath):
    os.makedirs(logchainpath)

logfile = os.path.join(logchainpath, f'yahoochain_{currenttime}.txt')
logging.basicConfig(filename=logfile, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

configassets = configchain['assets']
etflist = list(configassets.get('etf').split(','))
chipslist = list(configassets.get('chip').split(','))
assetlist = etflist + chipslist

from bsoption.nyopchain import NYopchain
Opchain = NYopchain()

def getchain(asset):
    """Download option chain from yahoo finance API."""
    # All expiry days
    Ticker = yf.Ticker(asset)
    expdaylist = Ticker.options
    # Last trading day
    df1d = Ticker.history(period='1d')
    lasttd = df1d.index[0].strftime('%Y%m%d')[2:]
    # Option chain dict with each key-value pair being a single expiry day option series
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
            collist = ['contract', 'asset', 'optype', 'expiry', 'strike', 'last', 'bid', 'ask', 'chg', 'pctchg', 'iv',
                       'vol', 'oi']
            dfchain = dfchain[collist]
            for col in ['strike', 'last', 'bid', 'ask', 'chg', 'pctchg', 'iv', 'vol', 'oi']:
                dfchain[col] = pd.to_numeric(dfchain[col])
            dfchain['chg'] = np.round(dfchain['chg'], 2)
            dfchain['pctchg'] = np.round(dfchain['pctchg'], 4)
            dfchain['iv'] = np.round(100 * dfchain['iv'], 2)
            dfchain.set_index('contract', inplace=True)
            dfchain.sort_index(inplace=True)
            chaindict[daystr] = dfchain
            logging.info(f'Option chain for {asset} expiring on {daystr} is ready.')

    # Export to excel files
    excelfile = os.path.join(chainpath, f'{asset}-{lasttd}.xlsx')
    masterwriter = ExcelWriter(excelfile, engine='xlsxwriter', datetime_format='yyyy-mm-dd', date_format='yyyy-mm-dd')
    for expday, df in chaindict.items():
        df.to_excel(masterwriter, sheet_name=expday)
    for name, sheet in masterwriter.sheets.items():
        sheet.freeze_panes(1, 1)
        sheet.set_column('A:A', 20)
        sheet.set_column('B:B', 6)
        sheet.set_column('C:C', 12)
        sheet.set_column('D:G', 8)
        sheet.set_column('H:J', 12)
        sheet.set_column('K:L', 8)
    masterwriter.save()

    return chaindict

def opchainflow():
    """Download option chain and append to database."""
    for asset in assetlist:
        try:
            dfchain = Opchain.getopchainyahoo(asset)
            Opchain.appendchaindf(dfchain)
            logging.info(f'Successfully download & append option chain of {asset}.')
        except:
            logging.info(f'Error in handling option chain of {asset}.')

if __name__ == '__main__':
    logging.info('START Yahoo Finance option chain workflow.')
    assetchaindict = {}

    for asset in assetlist:
        try:
            assetchaindict[asset] = getchain(asset)
        except:
            logging.info(f'cannot download option chain of {asset}.')

    logging.info('End of Yahoo Finance option chain workflow.')
    logging.shutdown()