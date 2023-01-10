import time
# import schedule
from datetime import datetime
import math
import warnings
import os

import ccxt
import pandas as pd
import numpy
import schedule

import dontshareconfig

warnings.filterwarnings("ignore")


class TradingBot:
    symbol = 'BTC/USDT'
    size = 10
    target = 15
    max_loss = -7
    params = {'timeInForce': 'PostOnly'}

    def __init__(self):
        self.exchange = self.set_credentials_exchange()

    # credentials
    def set_credentials_exchange(self):
        return ccxt.kucoin({  # he uses phemex look why? maybe commissions
            'enableReteLimit': True,
            'apiKey': dontshareconfig.xP_KUCOIN_KEY,
            'secret': dontshareconfig.xP_KUCOIN_SECRET
        })

    def get_asks_bids(self):
        order_book = self.exchange.fetch_order_book(self.symbol)
        return order_book['asks'][0][0], order_book['bids'][0][0]

    def pos_info(self):  # TODO Estudiar que hace esta funcion
        params = {'type': 'swap', 'code': 'USD'}

        balance = self.exchange.fetch_balance(params)
        open_positions = balance['info']['data']['positions']

        pos_df = pd.DataFrame.from_dict(open_positions)
        pos_cost = pos_df.loc[pos_df['symbol'] == self.symbol, 'posCost'].values[0]  # esto no se que hace
        side = pos_df.loc[pos_df['symbol'] == self.symbol, 'side'].values[0]  # esto no se que hace
        pos_cost = float(pos_cost)
        pos_size = pos_df.loc[pos_df['symbol'] == self.symbol, 'size'].values[0]  # esto no se que hace
        size = float(pos_size)
        entry_price = pos_df.loc[pos_df['symbol'] == self.symbol, 'avgEntryPrice'].values[0]  # esto no se que hace
        entry_price = float(entry_price)
        leverage = pos_df.loc[pos_df['symbol'] == self.symbol, 'leverage'].values[0]  # esto no se que hace
        leverage = float(leverage)

        print(f'Symbol: {self.symbol}, side: {side}, lev: {leverage}, size: {size}, entry price: {entry_price}')

        if size > 0:
            in_pos = True
        else:
            in_pos = False

        return pos_cost, side, size, entry_price, leverage, in_pos

    def get_order_book_data(self):

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

        print(f'---------L1 {self.exchange.name}')
        phe_book = self.exchange.fetch_order_book(symbol=self.symbol, params={'group': 10})

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

        # # save to csv
        # df = df.concat(temp_df)
        # df.to_csv('order_book.csv', index=False)

        # compare total bids vs toal asks
        print('==' * 5, F'TOTAL FOR THE EXCHANGE {self.exchange.name.upper()}', '==' * 5)

        if phe_ask_total_book_vol > phe_bid_total_book_vol:
            print(f'The sum of {self.exchange.name}, Asks are bigger than the sum of Bids')
            phe_sig = 'SELL'  # 'SHORT'
            temp_df['phe_sig'] = [phe_sig]
            difference = phe_ask_total_book_vol - phe_bid_total_book_vol
            perc_diff = round((difference / phe_ask_total_book_vol) * 100, 3)
            temp_df['Phe_diff'] = [perc_diff]
            print(f'The difference is {difference}, which is a {perc_diff}%')

        elif phe_ask_total_book_vol < phe_bid_total_book_vol:
            print(f'The sum of {self.exchange.name}, Asks are bigger than the sum of Bids')
            phe_sig = 'BUY'  # 'LONG'
            temp_df['phe_sig'] = [phe_sig]
            difference = phe_bid_total_book_vol - phe_ask_total_book_vol
            perc_diff = round((difference / phe_bid_total_book_vol) * 100, 3)
            temp_df['Phe_diff'] = [perc_diff]
            print(f'The difference is {difference}, which is a {perc_diff}%')

        else:
            print('Asks and Bids ar equal')

        # Get coin info/price
        coin_dict = self.exchange.fetch_ticker(self.symbol)
        coin_price = coin_dict['last']
        print(f'{self.symbol} price: {coin_price}')
        temp_df['coin_price'] = [coin_price]

        # save to csv
        df = df.append(temp_df)
        df.to_csv('order_book.csv', index=False)

        return df, phe_sig  # order book data

    def bot(self):
        ob_data = self.get_order_book_data()
        df = ob_data[0]
        phe_sig = ob_data[1]

        asks, bids = self.get_asks_bids(self.symbol)

        # check if we are in position
        # pos_info() -> pos_cost, side, size, entry_price, leverage, in_pos
        pos_cost, side, size, entry_price, leverage, in_pos = self.pos_info()

        if not in_pos:
            print('Making orders because we are not in position')

            if phe_sig == 'BUY':
                print('Going to make buy orders, because the sig is BUY')
                self.exchange.cancel_all_orders(self.symbol)
                self.exchange.create_limit_buy_order(self.symbol, self.size, bids, self.params)
                print('just sumitted a buy order, now sleeping for 30s')
                time.sleep(30)
            elif phe_sig == 'SELL':
                print('Going to make sell orders, because the sig is SELL')
                self.exchange.create_limit_sell_order(self.symbol, self.size, bids, self.params)
                print('just sumitted a sell order, now sleeping for 30s')
                time.sleep(30)
            else:
                print('There is no signal, so there is no orders')
        else:
            print('doing nothing as we are in position')


tb = TradingBot()

schedule.every(28).seconds.do(tb.get_order_book_data)

while True:
    try:
        schedule.run_pending()
    except Exception:
        print('------------------NOT WORKING---------------------')
        time.sleep(30)
