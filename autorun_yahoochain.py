import os
codepath = os.path.dirname(os.path.abspath(__file__))
import sys
sys.path.append('..')

from datetime import datetime, timedelta
from configparser import ConfigParser
configchain = ConfigParser()
configchain.read(os.path.join(codepath, 'setting_yahoochain.ini'))
chainpath = configchain['paths'].get('chainpath')

configassets = configchain['assets']
etflist = list(configassets.get('etf').split(','))
chipslist = list(configassets.get('chip').split(','))
assetlist = etflist + chipslist

from litedata import holidaydictny, gettradedays
from bsoption.nyopchain import NYopchain
Opchain = NYopchain()

import logging
logfile = os.path.join(logchainpath, f'yahoochain_{currenttime}.txt')
logging.basicConfig(filename=logfile, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def opchainflow(assetlist):
    """Download option chain and append to database."""
    today = (datetime.today() - timedelta(hours=6)).strftime('%Y-%m-%d')
    tdlist = gettradedays(holidaydictny)
    lasttd = [dtstr for dtstr in tdlist if dtstr < today][-1]
    ltddate = datetime.strptime(lasttd, '%Y-%m-%d')
    nextexpiry = (ltddate + timedelta(days=7)).strftime('%Y-%m-%d')
    next2expiry = (ltddate + timedelta(days=36)).strftime('%Y-%m-%d')
    tablelist = Opchain.engine.table_names()

    for asset in assetlist:
        try:
            needupdate = False
            if asset not in tablelist:
                needupdate = True
            else:
                inputdict = {'asset': asset, 'optype': ('C', 'P'),
                             'strike_lowerbound': 0, 'strike_upperbound': 1000,
                             'startexpiry': nextexpiry, 'endexpiry': next2expiry,
                             'starttd': lasttd, 'endtd': lasttd}
                dfop = Opchain.loadopdata(inputdict)
                if dfop.shape[0] == 0:
                    needupdate = True
            if needupdate:
                dfchain = Opchain.getopchainyahoo(asset)
                Opchain.appendchaindf(dfchain)
                logging.info(f'Successfully download & append latest option chain of {asset} on {lasttd}.')
            else:
                logging.info(f'Latest option chain of {asset} on {lasttd} already available.')
        except:
            logging.info(f'Error in appending latest option chain of {asset} on {lasttd}.')

if __name__ == '__main__':
    logging.info('START Yahoo Finance option chain workflow.')
    opchainflow(assetlist)
    logging.info('End of Yahoo Finance option chain workflow.')
    logging.shutdown()