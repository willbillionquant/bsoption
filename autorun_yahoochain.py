import os
codepath = os.path.dirname(os.path.abspath(__file__))
import sys
sys.path.append('..')

from configparser import ConfigParser
configstrat = ConfigParser()
configstrat.read(os.path.join(codepath, 'setting_yahoochain.ini'))
chainpath = configstrat['paths'].get('chainpath')



from datetime import datetime, timedelta
from itertools import product
import numpy as np
import pandas as pd
from pandas import ExcelWriter

from bsoption.bsmodel import *
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import yfinance as yf
ohlcvdfield = ['op', 'hi', 'lo', 'cl', 'vol', 'div']

chainpath = r'D:\Trading\Data\options\nyse'