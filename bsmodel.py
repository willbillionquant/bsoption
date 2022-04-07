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
        self.d_1 = self.getzscore()[0]
        self.d_2 = self.getzscore()[1]
        self.cprice = self.getopprice('C')
        self.pprice = self.getopprice('P')
        self.cdelta = self.getdelta('C')
        self.pdelta = self.getdelta('P')
        self.ctheta = self.gettheta('C')
        self.ptheta = self.gettheta('P')
        self.vega = self.S * norm.pdf(self.d_1) * (self.T ** 0.5) / 100
        self.gamma = norm.pdf(self.d_1) / (self.S * self.sig * (self.T ** 0.5))

    def getzscore(self):
        """Compute two essential z-scores for option pricing."""
        d_1 = (np.log(self.S / self.K) + self.T * (self.rf + 0.5 * (self.sig ** 2))) / (self.sig * (self.T ** 0.5))
        d_2 = d_1 - self.sig * (self.T ** 0.5)
        return d_1, d_2

    def getopprice(self, optype):
        """Compute option price by Black-Scholes Model."""
        assert optype in ['C', 'P'], AttributeError('Must be call or put!')
        if optype == 'C':
            opprice = self.S * norm.cdf(self.d_1, 0, 1) - self.K * np.exp(- self.rf * self.T) * norm.cdf(self.d_2, 0, 1)
        else:
            opprice = self.K * np.exp(- self.rf * self.T) * norm.cdf(-self.d_2, 0, 1) - self.S * norm.cdf(-self.d_1, 0,
                                                                                                          1)
        return opprice

    def getdelta(self, optype):
        """Return call or put delta = inceremental change per unit increment in underlying."""
        assert optype in ['C', 'P'], AttributeError('Must be call or put!')
        if optype == 'C':
            delta = norm.cdf(self.d_1)
        else:
            delta = norm.cdf(self.d_1) - 1
        return delta

    def gettheta(self, optype):
        """Return call or put theta = time value per day."""
        assert optype in ['C', 'P'], AttributeError('Must be call or put!')
        if optype == 'C':
            t_1 = - self.S * norm.pdf(self.d_1) * self.sig / (2 * (self.T) ** 0.5)
            t_2 = self.rf * self.K * np.exp(- self.rf * self.T) * norm.cdf(self.d_2)
        else:
            t_1 = - self.S * norm.pdf(self.d_1) * self.sig / (2 * (self.T) ** 0.5)
            t_2 = self.rf * self.K * np.exp(- self.rf * self.T) * norm.cdf(- self.d_2)
        return (t_1 + t_2) / 365

    def getpayoff(self, preexpiry=False, numday=(7, 14, 28, 56)):
        """Obtain payoff diagram at expiry and (if `preexpiry` enabled) payoff of each given days before expiry."""
        halfplus = lambda x: x if x > 0 else 0
        lowb = self.K * (1 - self.sig / 2)
        upb = self.K * (1 + self.sig / 2)
        pricearr = np.linspace(lowb, upb, 11)
        # Payoff Dataframe: call & put at expiry
        dfprice = pd.DataFrame(columns=['spot', 'expC', 'expP'])
        dfprice['spot'] = pricearr
        dfprice['expC'] = (dfprice['spot'] - self.K).apply(halfplus)
        dfprice['expP'] = (self.K - dfprice['spot']).apply(halfplus)
        # Add payoff plots
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05,
                            row_heights=[0.5, 0.5], specs=[[{"type": "scatter"}]] * 2,
                            subplot_titles=("Call", "Put"))
        fig.add_trace(go.Scatter(x=dfprice['spot'], y=dfprice['expC'],
                                 mode="lines", name="Call-Exp", line_color='#43b117'), row=1, col=1)
        fig.add_trace(go.Scatter(x=dfprice['spot'], y=dfprice['expP'],
                                 mode="lines", name="Put-Exp", line_color='#1756b1'), row=2, col=1)
        if preexpiry:
            for day in numday:
                dfprice[f'{day}dayC'] = round(dfprice['spot'].apply(lambda x: BSModel(x, self.K, day, self.sig).cprice), 2)
                dfprice[f'{day}dayP'] = round(dfprice['spot'].apply(lambda x: BSModel(x, self.K, day, self.sig).pprice), 2)
                fig.add_trace(go.Scatter(x=dfprice['spot'], y=dfprice[f'{day}dayC'],
                                         mode="lines+markers", name=f"Call-{day}D", line_color='#43b117'), row=1, col=1)
                fig.add_trace(go.Scatter(x=dfprice['spot'], y=dfprice[f'{day}dayP'],
                                         mode="lines+markers", name=f"Put-{day}D", line_color='#1756b1'), row=2, col=1)

        fig.update_layout(height=800, showlegend=False, title_text="Payoff curve", title_x=0.5)
        fig.show()

        return dfprice

def getivbisect(S, K, T, P, optype, rf=0, lowb=0, upb=400.0, maxstep=20, pcterr=0.001):
    """Obtain an estimate of IV by bisection method."""
    BSstart = BSModel(S, K, T, lowb / 100, rf)  # Lower estimate of original option price
    BSend = BSModel(S, K, T, upb / 100, rf)  # Upper estimate of original option price
    assert optype in ['C', 'P'], AttributeError('Must be call or put!')
    lowprice = BSstart.getopprice(optype)
    upprice = BSend.getopprice(optype)
    assert ((P >= lowprice) and (P <= upprice)), AttributeError('IV should be between lower & upper bounds!')

    if (T == 0) or (P == abs(S - K)):
        sig = 0
    else:
        # Initialize guess
        step = 1
        sig = (lowb + upb) / 2
        # Loop of bisection method
        while step <= maxstep:
            # End iteration if upper bound & lower bound are within margin of error
            diffprice = upprice - lowprice
            if diffprice < pcterr * P:
                break
            else:  # Take mid-point of current interval and cut interval in half
                sig = (lowb + upb) / 2
                newprice = BSModel(S, K, T, sig / 100, rf).getopprice(optype)
                if newprice > P:
                    upb = sig
                    upprice = newprice
                else:
                    lowb = sig
                    lowprice = newprice

                step += 1

    return round(sig, 2)

def getoneopcurve(dfop, opfield, spotfield='ftclose', uptoexpiry=True):
    """Obtain option price curve."""
    fig = make_subplots(rows=6, cols=1, shared_xaxes=True, vertical_spacing=0.05,
                        row_heights=[0.36, 0.24, 0.1, 0.1, 0.1, 0.1], specs=[[{"type": "scatter"}]] * 6,
                        subplot_titles=("Option price", "Underlying", "IV", "Delta", "Theta", "Vega"))
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

    # Chart title
    fig.update_layout(height=800, showlegend=False, title_text="Option Price curve", title_x=0.5)
    fig.show()


