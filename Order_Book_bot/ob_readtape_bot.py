import time
# import schedule
from datetime import datetime
import math
import warnings
import os

import ccxt
import pandas as pd
import numpy

import dontshareconfig

warnings.filterwarnings("ignore")

# credentials
exchange = ccxt.kucoin({  # he uses phemex look why? maybe comissions
    'enableReteLimit': True,
    'apiKey': dontshareconfig.xP_KUCOIN_KEY,
    'secret': dontshareconfig.xP_KUCOIN_SECRET
})

symbol = 'BTC/USDT'
size = 1000
target = 15
mas_loss = -7


def order_book():
    if not os.path.isfile('order_book.csv'):
        df = pd.DataFrame()
    else:
        df = pd.read_csv('order_book.csv')

    temp_df = pd.DataFrame()

    now = datetime.now()
    dt_string = now.strftime('%m/%d/%Y %H:%M:%S')
    print(dt_string)
    comptime = int(time.time())
    print(comptime)

    temp_df['dt'] = [dt_string]
    temp_df['comptime'] = [comptime]

    print(f'---------L1 {exchange.name}')
    phe_book = exchange.fetch_order_book(symbol=symbol, params={'group': 10})

    phe_bids = phe_book['bids']
    phe_asks = phe_book['asks']

    phe_bid_vol_list = []
    phe_bid_price_list = []
    for bid in phe_bids:
        phe_bid_vol_list.append(bid[1])  # bid[1] = volume
        phe_bid_price_list.append(bid[0])  # bid[0] = price

    # print(phe_bid_vol_list)

    '''
    sum up volume list
    BTC/USDT contracts are 1/1000 of a BTC
    '''
    phe_bid_total_book_vol = sum(phe_bid_vol_list) * 1000
    # print(f'Total volume of bids in BTC/USDT: {phe_bid_total_book_vol}')

    temp_df['Phe_Bid'] = [phe_bid_total_book_vol]

    # combine aks vol
    phe_ask_vol_list = []
    phe_ask_price_list = []
    for ask in phe_asks:
        phe_ask_vol_list.append(ask[1])  # ask[1] = volume
        phe_ask_price_list.append(ask[0])  # ask[0] = price

    # print(phe_ask_vol_list)

    phe_ask_total_book_vol = sum(phe_ask_vol_list) * 1000
    # print(f'Total volume of bids in BTC/USDT: {phe_ask_vol_list}')

    temp_df['Phe_Ask'] = [phe_ask_total_book_vol]

    print(f'Phes total BUY orderbook vol is {phe_bid_total_book_vol}')
    print(f'Phes total ASK orderbook vol is {phe_ask_total_book_vol}')

    # compare volumes to last time through
    try:
        volumesdiff = float((temp_df['Phe_Bid']) - float(df['Phe_Bid'].values[-1]))
    except KeyError:
        volumesdiff = 0

    print(f'volume diff between this and last execution: {volumesdiff}')

    phe_bid_perc_change = round(volumesdiff / float(temp_df['Phe_Bid']), 3)
    print(f'% of volume change: {phe_bid_perc_change}')
    temp_df['Phe_bid_chng'] = [phe_bid_perc_change]

    # compare asks to last time through
    try:
        asksdiff = float((temp_df['Phe_Ask']) - float(df['Phe_Ask'].values[-1]))
    except KeyError:
        asksdiff = 0

    print(f'Bid diff between this and last execution: {asksdiff}')

    phe_ask_perc_change = round(asksdiff / float(temp_df['Phe_Ask']), 3)
    print(f'% of volume change: {phe_ask_perc_change}')
    temp_df['Phe_ask_chng'] = [phe_ask_perc_change]

    # save to csv
    df = df.append(temp_df)
    df.to_csv('order_book.csv', index=False)


order_book()
