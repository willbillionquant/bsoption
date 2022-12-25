import os
codepath_bsoption = os.path.dirname(os.path.abspath(__file__))
import sys
sys.path.append('..')

def getfinalopprice(optype, strike, price):
    """Obtain the option price at expiry."""
    assert optype in ['C', 'P'], AttributeError('Option type has to be "C" or "P"!')
    return (max(price - strike, 0), max(strike - price, 0))[(optype == 'P')]