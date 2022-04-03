import sys
sys.path.append('..')

from hkexoi.bsmodel import *

stratdict = {
        'spread': (1, -1),  # debit/credit spread: LONG 1 leg SHORT other
        'strangle': (1, 1)  # strangle / straddle: Same direction both side
        }

def appendratiostrat(num1, num2):
    """Append ratio spread/strangle into strategy dict."""
    stratdict[f'ratio_{num1}:{num2}'] = (num1, num2)

    return stratdict

class Opduo():
    """
    Formulate option strategy involving 2 distinct option series.
    """

    def __init__(self, op1, str1, exp1, op2, str2, exp2, q=0, rf=0):
        self.op1 = op1  # Option type of first instrument (call or put)
        self.str1 = str1  # 1st strike price
        self.exp1 = exp1  # 1st expiry date
        self.op2 = op2  # Option type of first instrument (call or put)
        self.str2 = str2  # 1st strike price
        self.exp2 = exp2  # 1st expiry date
        self.q = q  # Dividend rate
        self.rf = rf  # risk-free rate

    def getduomodel(self, spot, tradedate, sig1, sig2):
        """Obtain a pair of BSModel object given trading date, spot & IVs."""
        day1 = (self.exp1 - tradedate).days  # days to expiry of option 1
        day2 = (self.exp2 - tradedate).days  # days to expiry of option 2
        BS1 = BSModel(spot, self.str1, day1, sig1 / 100)  # BSModel of option 1
        BS2 = BSModel(spot, self.str2, day2, sig2 / 100)  # BSModel of option 2
        return BS1, BS2

    def getstratspec(self, spot, tradedate, sig1, sig2, strat, side="LONG", digit=2):
        """Obtain strategy price & greeks."""
        # Pair of BSModel objects
        BS1, BS2 = self.getduomodel(spot, tradedate, sig1, sig2)
        opprice1 = BS1.getopprice(self.op1)
        opprice2 = BS2.getopprice(self.op2)
        # identify option strategy type
        ratiopair = stratdict[strat]
        assert side in ['LONG', 'SHORT'], AttributeError('Must be LONG or SHORT!')
        sign = lambda x: 1 if x == 'LONG' else -1
        # Strategy price
        stratprice = round((opprice1 * ratiopair[0] + opprice2 * ratiopair[1]) * sign(side), digit)
        # Strategy delta
        delta = round((BS1.getdelta(self.op1) * ratiopair[0] + BS2.getdelta(self.op2) * ratiopair[1]) * sign(side), 4)
        # strategy theta
        theta = round((BS1.gettheta(self.op1) * ratiopair[0] + BS2.gettheta(self.op2) * ratiopair[1]) * sign(side), 4)
        # strategy vega
        vega = round((BS1.vega * ratiopair[0] + BS2.vega * ratiopair[1]) * sign(side), 4)
        #  strategy gamma
        gamma = round((BS1.gamma * ratiopair[0] + BS2.gamma * ratiopair[1]) * sign(side), 4)

        return stratprice, delta, theta, vega, gamma

