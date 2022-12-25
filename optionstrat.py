import os
codepath_bsoption = os.path.dirname(os.path.abspath(__file__))
import sys
sys.path.append('..')

from bsoption import *
from bsoption.bsmodel import *

stratdict = {
        'spread': (1, -1),  # debit/credit spread: LONG 1 leg SHORT other
        'strangle': (1, 1),  # strangle / straddle: Same direction both side
        'synthetic': (1, -1),  # LC + SP / LP + SC
        }

def appendratiostrat(num1, num2):
    """Append ratio spread/strangle into strategy dict."""
    stratdict[f'ratio_{num1}:{num2}'] = (num1, num2)

    return stratdict


class Opduo():
    """
    Formulate option strategy involving 2 distinct option series.
    """

    def __init__(self, op1, str1, exp1, sig1, op2, str2, exp2, sig2, strat, q=0, rf=0):
        self.op1 = op1  # Option type of first instrument (call or put)
        self.str1 = str1  # 1st strike price
        self.exp1 = exp1  # 1st expiry date
        self.sig1 = sig1  # 1st IV
        self.op2 = op2  # Option type of first instrument (call or put)
        self.str2 = str2  # 2nd strike price
        self.exp2 = exp2  # 2nd expiry date
        self.sig2 = sig2  # 2nd IV
        self.q = q  # Dividend rate
        self.rf = rf  # risk-free rate
        self.strat = strat  # strategy type (spread / strangle / synthetic)
        self.ratiopair = stratdict[self.strat]
        self.ratio1 = self.ratiopair[0]
        self.ratio2 = self.ratiopair[1]

    def getduomodel(self, spot, tradedate):
        """Obtain a pair of BSModel object given trading date, spot & IVs."""
        day1 = (self.exp1 - tradedate).days  # days to expiry of option 1
        day2 = (self.exp2 - tradedate).days  # days to expiry of option 2
        BS1 = BSModel(spot, self.str1, day1, self.sig1)  # BSModel of option 1
        BS2 = BSModel(spot, self.str2, day2, self.sig2)  # BSModel of option 2
        return BS1, BS2

    def getstratspec(self, spot, tradedate, opside="LONG", digit=2):
        """Obtain strategy price & greeks."""
        # Assert combo side
        assert opside in ['LONG', 'SHORT'], AttributeError('opside must be LONG or SHORT!')
        # Pair of BSModel objects
        BS1, BS2 = self.getduomodel(spot, tradedate)
        opprice1 = BS1.getopprice(self.op1)
        opprice2 = BS2.getopprice(self.op2)
        sign = lambda x: 1 if x == 'LONG' else -1
        # Strategy price
        stratprice = round((opprice1 * self.ratio1 + opprice2 * self.ratio2) * sign(opside), digit)
        # Strategy delta
        delta = round((BS1.getdelta(self.op1) * self.ratio1 + BS2.getdelta(self.op2) * self.ratio2) * sign(opside), 4)
        # strategy theta
        theta = round((BS1.gettheta(self.op1) * self.ratio1 + BS2.gettheta(self.op2) * self.ratio2) * sign(opside), 4)
        # strategy vega
        vega = round((BS1.vega * self.ratio1 + BS2.vega * self.ratio2) * sign(opside), 4)
        #  strategy gamma
        gamma = round((BS1.gamma * self.ratio1 + BS2.gamma * self.ratio2) * sign(opside), 4)

        return stratprice, delta, theta, vega, gamma

    def getpayoff(self, preexpiry=False, numday=(7, 21, 63), opside='LONG'):
        """Obtain payoff diagram at expiry and (if `preexpiry` enabled) payoff of each given days before expiry."""
        # Assert combo side
        assert opside in ['LONG', 'SHORT'], AttributeError('opside must be LONG or SHORT!')
        # price axis bounds and scales
        minK = min([self.str1, self.str2])
        maxK = max([self.str1, self.str2])
        sig = max([self.sig1, self.sig2])
        lowb = minK * (1 - sig / 2)
        upb = maxK * (1 + sig / 2)
        pricearr = np.linspace(lowb, upb, 200)
        # Payoff dataframe
        dfprice = pd.DataFrame(columns=['spot', 'exp1', 'exp2', 'exp'])
        dfprice['spot'] = pricearr
        halfplus = lambda x: x if x > 0 else 0
        for num in [1, 2]:
            if self.__dict__[f'op{num}'] == 'C':
                dfprice[f'exp{num}'] = (dfprice['spot'] - self.__dict__[f'str{num}']).apply(halfplus)
            else:
                dfprice[f'exp{num}'] = (self.__dict__[f'str{num}'] - dfprice['spot']).apply(halfplus)
        dfprice['exp'] = dfprice['exp1'] * self.ratio1 + dfprice['exp2'] * self.ratio2
        if opside == 'SHORT':
            dfprice['exp'] *= -1
        # Payoff subplot
        fig = make_subplots(rows=1, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.5],
                            specs=[[{"type": "scatter"}]])

        fig.add_trace(
            go.Scatter(x=dfprice['spot'], y=dfprice['exp'], mode="lines", name="At Expiry", line_color='#43b117'),
            row=1, col=1)
        # Pre-expiry payoff curve
        if preexpiry:
            for day in numday:
                for num in [1, 2]:
                    if self.__dict__[f'op{num}'] == 'C':
                        bsfunc = lambda x: BSModel(x, self.__dict__[f'str{num}'], day,
                                                   self.__dict__[f'sig{num}']).cprice
                    else:
                        bsfunc = lambda x: BSModel(x, self.__dict__[f'str{num}'], day,
                                                   self.__dict__[f'sig{num}']).pprice
                    dfprice[f'temp{num}'] = round(dfprice['spot'].apply(bsfunc), 2)
                dfprice[f'{day}day'] = dfprice['temp1'] * self.ratio1 + dfprice['temp2'] * self.ratio2
                if opside == 'SHORT':
                    dfprice[f'{day}day'] *= -1
                fig.add_trace(go.Scatter(x=dfprice['spot'], y=dfprice[f'{day}day'],
                                         mode="markers", name=f"{day}D", line_color='#d516cc'), row=1, col=1)
        # Chart title
        fig.update_layout(height=800, showlegend=False, title_x=0.5,
                          title_text=f'{opside}-{self.strat}-{self.str1}{self.op1}-{self.str2}{self.op2}')
        fig.show()