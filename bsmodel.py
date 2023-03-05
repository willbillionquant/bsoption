import os
codepath_bsoption = os.path.dirname(os.path.abspath(__file__))
import sys
sys.path.append('..')

import numpy as np
import pandas as pd
from scipy.stats import norm

import plotly.graph_objects as go
from plotly.subplots import make_subplots

class BSModel():
    """
    Determines the price for a European-style vanilla option using the Black-Scholes model.
    """

    def __init__(self, S, K, T, sig, rf=0):
        self.S = S  # Underlying price
        self.K = K  # Strike price
        self.T = T / 365  # Number of days to expiry
        self.sig = sig  # IV ( 50% = 0.5)
        self.rf = rf  # risk-free rate
        self.d1 = self.getZscore()[0]
        self.d2 = self.getZscore()[1]
        self.cPrice = self.getOpPrice('C')
        self.pPrice = self.getOpPrice('P')
        self.cDelta = self.getDelta('C')
        self.pDelta = self.getDelta('P')
        self.cTheta = self.getTheta('C')
        self.pTheta = self.getTheta('P')
        self.Vega = round(self.S * norm.pdf(self.d1) * (self.T ** 0.5) / 100, 6)
        self.Gamma = round(norm.pdf(self.d1) / (self.S * self.sig * (self.T ** 0.5)), 9)

    def getZscore(self):
        """Compute two essential z-scores for option pricing."""
        d1 = (np.log(self.S / self.K) + self.T * (self.rf + 0.5 * (self.sig ** 2))) / (self.sig * (self.T ** 0.5))
        d2 = d1 - self.sig * (self.T ** 0.5)
        return d1, d2

    def getOpPrice(self, opType):
        """Compute option price by Black-Scholes Model."""
        assert opType in ['C', 'P'], AttributeError('Must be call or put!')
        if opType == 'C':
            opPrice = self.S * norm.cdf(self.d1, 0, 1) - self.K * np.exp(- self.rf * self.T) * norm.cdf(self.d2, 0, 1)
        else:
            opPrice = self.K * np.exp(- self.rf * self.T) * norm.cdf(-self.d2, 0, 1) - self.S * norm.cdf(-self.d1, 0, 1)

        return round(opPrice, 4)

    def getDelta(self, opType):
        """Return call or put delta = inceremental change per unit increment in underlying."""
        assert opType in ['C', 'P'], AttributeError('Must be call or put!')
        if opType == 'C':
            delta = norm.cdf(self.d1)
        else:
            delta = norm.cdf(self.d1) - 1
        return round(delta, 6)

    def getTheta(self, opType):
        """Return call or put theta = time value per day."""
        assert opType in ['C', 'P'], AttributeError('Must be call or put!')
        if opType == 'C':
            t1 = - self.S * norm.pdf(self.d1) * self.sig / (2 * (self.T) ** 0.5)
            t2 = self.rf * self.K * np.exp(- self.rf * self.T) * norm.cdf(self.d2)
        else:
            t1 = - self.S * norm.pdf(self.d1) * self.sig / (2 * (self.T) ** 0.5)
            t2 = self.rf * self.K * np.exp(- self.rf * self.T) * norm.cdf(- self.d2)
        return round((t1 + t2) / 365, 6)

    def getpayoff(self, numday=(7, 28, 56), Long=True, preExpiry=False):
        """Obtain payoff diagram at expiry and (if `preExpiry` enabled) payoff of each given days before expiry."""
        halfplus = lambda x: x if x > 0 else 0
        lowb = self.K * (1 - self.sig / 2)
        upb = self.K * (1 + self.sig / 2)
        priceArray = np.linspace(lowb, upb, 100)
        # Payoff Dataframe: call & put at expiry
        dfprice = pd.DataFrame(columns=['spot', 'expC', 'expP'])
        dfprice['spot'] = priceArray
        dfprice['expC'] = (dfprice['spot'] - self.K).apply(halfplus) * (1 if Long else -1)
        dfprice['expP'] = (self.K - dfprice['spot']).apply(halfplus) * (1 if Long else -1)
        # Add payoff plots
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05,
                            row_heights=[0.5, 0.5], specs=[[{"type": "scatter"}]] * 2, subplot_titles=("Call", "Put"))

        fig.add_trace(go.Scatter(x=dfprice['spot'], y=dfprice['expC'],
                                 mode="lines", name="Call-Exp", line_color='#43b117'), row=1, col=1)

        fig.add_trace(go.Scatter(x=dfprice['spot'], y=dfprice['expP'],
                                 mode="lines", name="Put-Exp", line_color='#1756b1'), row=2, col=1)

        if preExpiry:
            for day in numday:
                dfprice[f'{day}dayC'] = round(dfprice['spot'].apply(lambda x: BSModel(x, self.K, day, self.sig).cPrice), 2)
                dfprice[f'{day}dayP'] = round(dfprice['spot'].apply(lambda x: BSModel(x, self.K, day, self.sig).pPrice), 2)

                if not Long:
                    dfprice[f'{day}dayC'] *= -1
                    dfprice[f'{day}dayP'] *= -1

                fig.add_trace(go.Scatter(x=dfprice['spot'], y=dfprice[f'{day}dayC'],
                                         mode="markers", name=f"Call-{day}D", line_color='#d516cc'), row=1, col=1)

                fig.add_trace(go.Scatter(x=dfprice['spot'], y=dfprice[f'{day}dayP'],
                                         mode="markers", name=f"Put-{day}D", line_color='#d51653'), row=2, col=1)

        side = 'LONG' if Long else 'SHORT'
        fig.update_layout(height=800, showlegend=False, title_text=f'{side}-side Payoff curve', title_x=0.5)
        fig.show()

def getivbisect(S, K, T, P, opType, rf=0, lowb=0, upb=400.0, maxstep=20, pcterr=0.001):
    """Obtain an estimate of IV by bisection method."""
    BSstart = BSModel(S, K, T, lowb / 100, rf)  # Lower estimate of original option price
    BSend = BSModel(S, K, T, upb / 100, rf)  # Upper estimate of original option price
    assert opType in ['C', 'P'], AttributeError('Must be call or put!')
    lowprice = BSstart.getOpPrice(opType)
    upPrice = BSend.getOpPrice(opType)
    assert ((P >= lowprice) and (P <= upPrice)), AttributeError('IV should be between lower & upper bounds!')

    if (T == 0) or (P == abs(S - K)):
        sig = 0
    else:
        # Initialize guess
        step = 1
        sig = (lowb + upb) / 2
        # Loop of bisection method
        while step <= maxstep:
            # End iteration if upper bound & lower bound are within margin of error
            diffprice = upPrice - lowprice
            if diffprice < pcterr * P:
                break
            else:  # Take mid-point of current interval and cut interval in half
                sig = (lowb + upb) / 2
                newprice = BSModel(S, K, T, sig / 100, rf).getOpPrice(opType)
                if newprice > P:
                    upb = sig
                    upPrice = newprice
                else:
                    lowb = sig
                    lowprice = newprice

                step += 1

    return round(sig, 2)

def getoneopcurve(dfop, opfield, spotfield='ftclose', uptoexpiry=True):
    """Obtain option price curve."""
    fig = make_subplots(rows=7, cols=1, shared_xaxes=True, vertical_spacing=0.05,
                        row_heights=[0.25, 0.15, 0.1, 0.1, 0.1, 0.1, 0.1], specs=[[{"type": "scatter"}]] * 7,
                        subplot_titles=("Option price", "Underlying", "IV", "Delta", "Theta", "Vega", "Gamma"))
    # Option price curve
    fig.add_trace(go.Scatter(x=dfop.index, y=dfop[opfield],
                             mode="lines", name="Option Price", line_color='#43b117'), row=1, col=1)

    # Underlying Futures price curve
    fig.add_trace(go.Scatter(x=dfop.index, y=dfop[spotfield],
                             mode="lines", name="Underlying", line_color='#1756b1'), row=2, col=1)

    if uptoexpiry:  # The backtesting period includes the expiry date
        # Option IV curve
        fig.add_trace(go.Scatter(x=dfop.index[:-1], y=dfop['sig'].iloc[:-1],
                                 mode="lines", name="IV", line_color='#b119b1'), row=3, col=1)
        # Theta curve
        fig.add_trace(go.Scatter(x=dfop.index[:-1], y=dfop['theta'].iloc[:-1],
                                 mode="lines", name="Theta", line_color='#c50c47'), row=5, col=1)
    else:
        # Option IV curve
        fig.add_trace(go.Scatter(x=dfop.index, y=dfop['sig'],
                                 mode="lines", name="IV", line_color='#b119b1'), row=3, col=1)
        # Theta curve
        fig.add_trace(go.Scatter(x=dfop.index, y=dfop['theta'],
                                 mode="lines", name="Theta", line_color='#c50c47'), row=5, col=1)
    # Delta curve
    fig.add_trace(go.Scatter(x=dfop.index, y=dfop['delta'],
                             mode="lines", name="Delta", line_color='#60dd34'), row=4, col=1)
    # Vega curve
    fig.add_trace(go.Scatter(x=dfop.index, y=dfop['vega'],
                             mode="lines", name="Vega", line_color='#acdd34'), row=6, col=1)

    # Gamma curve
    fig.add_trace(go.Scatter(x=dfop.index, y=dfop['gamma'],
                             mode="lines", name="Gamma", line_color='#1956ee'), row=7, col=1)

    # Chart title
    fig.update_layout(height=800, showlegend=False, title_text="Option Price curve", title_x=0.5)
    fig.show()

