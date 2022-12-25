import os
codepath_bsoption = os.path.dirname(os.path.abspath(__file__))
import sys
sys.path.append('..')

import numpy as np
import pandas as pd

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from bsoption.bsmodel import BSModel

def getgex(dfchain, spotprice, ptfactor=100, decplace=4):
    """Obtain gamma exposure of each option contract per 1% move of underlying."""
    dfgex = dfchain.copy()
    dfgex['c_GEX'] = dfgex['c_gamma'] * dfgex['c_oi'] * ptfactor * spotprice / 100
    dfgex['p_GEX'] = -dfgex['p_gamma'] * dfgex['p_oi'] * ptfactor * spotprice / 100
    dfgex['GEX'] = dfgex['c_GEX'] + dfgex['p_GEX']
    for col in ['c_GEX', 'p_GEX', 'GEX']:
        dfgex[col] = np.round(dfgex[col], decplace)

    return dfgex

def getnewgex(dfgex, info, spotprice, ptfactor=100, decplace=4):
    """Obtain total GEX of an option chain with arbitary underlying price."""
    # Alter underlying price
    dfnewgex = dfgex.copy()
    # Recompute option price, delta and gamma
    dfnewgex.reset_index(inplace=True)
    tdays = (info[2] - info[1]).days
    colbs_c = dfnewgex.apply(lambda row: BSModel(spotprice, row['strike'], tdays, row['c_iv'] / 100), axis=1)
    dfnewgex['c_close'] = np.round(colbs_c.apply(lambda x: x.cprice), 2)
    dfnewgex['c_delta'] = np.round(colbs_c.apply(lambda x: x.cdelta), 4)
    dfnewgex['c_gamma'] = colbs_c.apply(lambda x: x.gamma)
    colbs_p = dfnewgex.apply(lambda row: BSModel(spotprice, row['strike'], tdays, row['p_iv'] / 100), axis=1)
    dfnewgex['p_close'] = np.round(colbs_p.apply(lambda x: x.pprice), 2)
    dfnewgex['p_delta'] = np.round(colbs_p.apply(lambda x: x.pdelta), 4)
    dfnewgex['p_gamma'] = colbs_p.apply(lambda x: x.gamma)
    # GEX
    dfnewgex['c_GEX'] = np.round(dfnewgex['c_gamma'] * dfnewgex['c_oi'] * ptfactor * spotprice / 100, decplace)
    dfnewgex['p_GEX'] = np.round(dfnewgex['p_gamma'] * dfnewgex['p_oi'] * ptfactor * -1 * spotprice / 100, decplace)
    dfnewgex['GEX'] = np.round(dfnewgex['c_GEX'] + dfnewgex['p_GEX'], decplace)
    # Set back `strike` as index
    dfnewgex.set_index('strike', inplace=True)

    return dfnewgex

def gettotalgex(dfgex):
    """Obtain call-GEX, put-GEX and total-GEX."""
    return round(dfgex['c_GEX'].sum(), 2), round(dfgex['p_GEX'].sum(), 2), round(dfgex['GEX'].sum(), 2)

def plotgex(dfgex, info):
    """Plot call GEX, put GEX and net GEX."""
    tdstr = info[1].strftime('%Y-%m-%d')
    expiry = info[2].strftime('%Y-%m-%d')
    spotprice = info[-1]
    gexsum_c, gexsum_p, gexsum = gettotalgex(dfgex)

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.125, row_heights=[8.0, 8.0],
                        specs=[[{"type": "bar"}], [{"type": "bar"}]],
                        subplot_titles=(f'Call-GEX: {gexsum_c}, Put-GEX: {gexsum_p}', f'Net GEX: {gexsum}'))

    fig.add_trace(go.Bar(x=dfgex.index, y=dfgex['c_GEX'], name="Call GEX",
                         marker=dict(color='#34dd74', line=dict(color='#34dd74', width=2))),
                  row=1, col=1)

    fig.add_trace(go.Bar(x=dfgex.index, y=dfgex['p_GEX'], name="Put GEX",
                         marker=dict(color='#dd3462', line=dict(color='#dd3462', width=2))),
                  row=1, col=1)

    fig.add_trace(go.Bar(x=dfgex.index, y=dfgex['GEX'], name="GEX",
                         marker=dict(color='#1956ee', line=dict(color='#1956ee', width=2))),
                  row=2, col=1)

    titletext = f'{info[0]} GEX of expiry {expiry} on {tdstr} at {spotprice} \n'

    fig.update_layout(title=titletext, title_x=0.5, width=1000, height=800)
    fig.show()

def get0gamma(dfchain, info, ptfactor=100, rangefactor=0.125, gridfactor=0.0125, plot=True):
    """Obtain zero gamma level."""
    # GEX according to true underlying price
    spotprice = info[-1]
    dfgex = getgex(dfchain, spotprice)
    cgex0, pgex0, ngex0 = gettotalgex(dfgex)
    # Grid of spot price levels (in geometric sequence)
    exprange = np.arange(-rangefactor, rangefactor, gridfactor)
    spotlevels = [spotprice * np.exp(exp) for exp in exprange]

    # Obtain GEX for all spot price levels
    dfsumgex = pd.DataFrame()
    for level in spotlevels:
        dfnewgex = getnewgex(dfgex, info, level, ptfactor)
        cgex, pgex, ngex = gettotalgex(dfnewgex)
        dfsumgex.loc[level, 'c_GEX'] = cgex
        dfsumgex.loc[level, 'p_GEX'] = pgex
        dfsumgex.loc[level, 'GEX'] = ngex
    # Obtain zero gamma level by linear interpolation
    if (dfsumgex['GEX'].min() * dfsumgex['GEX'].max()) > 0:
        zerogexlevel = None
    else:
        for p1, p2 in zip(dfsumgex.index[:-1], dfsumgex.index[1:]):
            level1 = dfsumgex.loc[p1, 'GEX']
            level2 = dfsumgex.loc[p2, 'GEX']
            if level1 * level2 < 0:
                zerogexlevel = round((p1 * level2 - p2 * level1) / (level2 - level1), 2)
                break
            else:
                zerogexlevel = p2
    # Visualize GEX at different spot price
    if plot:
        fig = make_subplots(rows=1, cols=1, shared_xaxes=True, row_heights=[6.0], specs=[[{"type": "scatter"}]])

        fig.add_trace(go.Scatter(x=dfsumgex.index, y=dfsumgex['GEX'], mode='lines+markers', name='spot levels'),
                      row=1, col=1)

        fig.add_trace(go.Scatter(x=[spotprice], y=[ngex0], mode='markers', name='spot price',
                                 marker=dict(size=20, color='#66dc19')), row=1, col=1)

        if zerogexlevel != None:
            fig.add_trace(go.Scatter(x=[zerogexlevel], y=[0], mode='markers', name='0-gamma level',
                                     marker=dict(size=20, color=' #ee195a')), row=1, col=1)

        tdstr = info[1].strftime('%Y-%m-%d')
        expiry = info[2].strftime('%Y-%m-%d')
        fig.update_layout(title=f'Gamma levels of {info[0]} of expiry {expiry} on {tdstr}',
                          title_x=0.5, width=1000, height=800)
        fig.show()

    return dfsumgex, zerogexlevel