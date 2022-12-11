# Bybit Trading Bot v2.14
# (C) 2022 Ryan Hayabusa 2022 
# Github: https://github.com/ryu878 
# Discord: ryuryu#4087
# Web: https://aadresearch.xyz
#######################################################################################################
# pip install -U pip
# pip install pybit
# pip install colorama
# pip install pandas
# pip install ta
# pip install python-binance
# pip install ccxt

import os
import ta
import ccxt
import time
import json
import uuid
import random
import sqlite3
import datetime
import pandas as pd
from config import *
from inspect import currentframe
from pybit import usdt_perpetual
from binance.client import Client
from colorama import init, Fore, Back, Style



exchange = ccxt.bybit({'apiKey':api_key,'secret':api_secret})
binance_client = Client(binance_api_key, binance_api_secret)
client = usdt_perpetual.HTTP(endpoint=endpoint,api_key=api_key,api_secret=api_secret)


enable_trading = input('Enable Trading? (0 - Disable, 1 - Enable) ')
symbol = input('What Asset To trade? ')
symbol = (symbol+'USDT').upper()


def get_balance():
    my_balance = exchange.fetchBalance()
    global available_balance
    global realised_pnl
    global equity
    global wallet_balance
    global unrealised_pnl
    available_balance = float(my_balance['info']['result']['USDT']['available_balance'])
    realised_pnl = my_balance['info']['result']['USDT']['realised_pnl']
    unrealised_pnl = my_balance['info']['result']['USDT']['unrealised_pnl']
    wallet_balance = my_balance['info']['result']['USDT']['wallet_balance']
    equity = my_balance['info']['result']['USDT']['equity']


def get_orderbook():

    orderbook = exchange.fetchOrderBook(symbol=symbol, limit=10)
    global ask
    global bid
    bid = orderbook['bids'][0][0] if len (orderbook['bids']) > 0 else None
    ask = orderbook['asks'][0][0] if len (orderbook['asks']) > 0 else None


def get_decimals():

    symbol_decimals  = client.query_symbol()
    for decimal in symbol_decimals['result']:
        if decimal['name'] == symbol:
            global decimals
            global leverage
            global tick_size
            global min_trading_qty
            global qty_step
            decimals = decimal['price_scale']
            leverage = decimal['leverage_filter']['max_leverage']
            tick_size = decimal['price_filter']['tick_size']
            min_trading_qty = decimal['lot_size_filter']['min_trading_qty']
            qty_step = decimal['lot_size_filter']['qty_step']


get_decimals()


print('Min lot size for',symbol,'is:',min_trading_qty)
print('Max leverage is:',leverage)


get_balance()
time.sleep(0.01)
get_orderbook()

what_1x_is = round((float(equity) / float(ask)) / (100 / float(leverage)),2)

print('        1x size:',what_1x_is)
print('        0.1x is:',what_1x_is/10)
print('          0.01x:',what_1x_is/100)

min_lot_size = input('What size to trade? ')


started = datetime.datetime.now().strftime('%H:%M:%S')


def get_linenumber():

    cf = currentframe()
    global line_number
    line_number = cf.f_back.f_lineno


def cancel_entry_orders():
    orders = client.get_active_order(symbol=symbol)
    for order in orders['result']['data']:
        if order['order_status'] != 'Filled' and order['side'] == 'Sell' and order['order_status'] != 'Cancelled' and order['reduce_only'] == False:     
            client.cancel_active_order(symbol=symbol, order_id=order['order_id'])
        elif order['order_status'] != 'Filled' and order['side'] == 'Buy' and order['order_status'] != 'Cancelled' and order['reduce_only'] == False:
            client.cancel_active_order(symbol=symbol, order_id=order['order_id'])

        
def cancel_close_orders():
    orders = client.get_active_order(symbol=symbol)
    for order in orders['result']['data']:
        if order['order_status'] != 'Filled' and order['side'] == 'Buy' and order['order_status'] != 'Cancelled' and order['reduce_only'] == True:
            client.cancel_active_order(symbol=symbol, order_id=order['order_id'])
        elif order['order_status'] != 'Filled' and order['side'] == 'Sell' and order['order_status'] != 'Cancelled' and order['reduce_only'] == True:
            client.cancel_active_order(symbol=symbol, order_id=order['order_id'])


def get_close_orders():
    orders = client.get_active_order(symbol=symbol,limit=200)

    # print(orders)

    for order in orders['result']['data']:

        global tp_buy_order_size
        global tp_buy_order_id
        global tp_buy_order_prc
        global tp_sell_order_size
        global tp_sell_order_id
        global tp_sell_order_prc
        
        if order['order_status'] == 'New' and order['order_status'] and order['order_status'] != 'Filled' and order['side'] == "Buy" and order['reduce_only'] == True:

            tp_buy_order_size = order['qty']
            tp_buy_order_id = order['order_id']
            tp_buy_order_prc = order['price']

            print('│     Buy Close order:',tp_buy_order_size, tp_buy_order_prc)
        
        else:
            # print('No Close Buy orders found')
            pass


        if order['order_status'] == 'New' and order['order_status'] and order['order_status'] != 'Filled' and order['side'] == "Sell" and order['reduce_only'] == True:

            tp_sell_order_size = order['qty']
            tp_sell_order_id = order['order_id']
            tp_sell_order_prc = order['price']

            print('│     Sell Close order:',tp_sell_order_size, tp_sell_order_prc)
        
        else:
            # print('No Close Sell orders found')
            pass


try:
    # Get decimals for the selected pair
    get_decimals()
except Exception as e:
    get_linenumber()
    print(line_number, 'exeception: {}'.format(e))

#------------------------------

def get_ema_3_5_high_bybit():

    bars = exchange.fetchOHLCV(symbol=symbol, timeframe='5m', limit=9)
    df = pd.DataFrame(bars,columns=['Time','Open','High','Low','Close','Vol'])
    df['EMA 3-5 High'] = ta.trend.EMAIndicator(df['High'], window=3).ema_indicator()
    global ema_3_5_high_bybit
    ema_3_5_high_bybit = round((df['EMA 3-5 High'][8]).astype(float),decimals)


def get_ema_3_1_high_bybit():

    bars = exchange.fetchOHLCV(symbol=symbol, timeframe='1m', limit=9)
    df = pd.DataFrame(bars,columns=['Time','Open','High','Low','Close','Vol'])
    df['EMA 3-1 High'] = ta.trend.EMAIndicator(df['High'], window=3).ema_indicator()
    global ema_3_1_high_bybit
    ema_3_1_high_bybit = round((df['EMA 3-1 High'][8]).astype(float),decimals)


def get_ema_3_5_low_bybit():

    bars = exchange.fetchOHLCV(symbol=symbol, timeframe='5m', limit=9)
    df = pd.DataFrame(bars,columns=['Time','Open','High','Low','Close','Vol'])
    df['EMA 3-5 Low'] = ta.trend.EMAIndicator(df['Low'], window=3).ema_indicator()
    global ema_3_5_low_bybit
    ema_3_5_low_bybit = round((df['EMA 3-5 Low'][8]).astype(float),decimals)


def get_ema_3_1_low_bybit():

    bars = exchange.fetchOHLCV(symbol=symbol, timeframe='1m', limit=9)
    df = pd.DataFrame(bars,columns=['Time','Open','High','Low','Close','Vol'])
    df['EMA 3-1 Low'] = ta.trend.EMAIndicator(df['Low'], window=3).ema_indicator()
    global ema_3_1_low_bybit
    ema_3_1_low_bybit = round((df['EMA 3-1 Low'][8]).astype(float),decimals)

# ------------------------------

def get_ema_6_5_high_bybit():

    bars = exchange.fetchOHLCV(symbol=symbol, timeframe='5m', limit=18)
    df = pd.DataFrame(bars,columns=['Time','Open','High','Low','Close','Vol'])
    df['EMA 6-5 High'] = ta.trend.EMAIndicator(df['High'], window=6).ema_indicator()
    global ema_6_5_high_bybit
    ema_6_5_high_bybit = round((df['EMA 6-5 High'][17]).astype(float),decimals)


def get_ema_6_1_high_bybit():

    bars = exchange.fetchOHLCV(symbol=symbol, timeframe='1m', limit=18)
    df = pd.DataFrame(bars,columns=['Time','Open','High','Low','Close','Vol'])
    df['EMA 6-1 High'] = ta.trend.EMAIndicator(df['High'], window=6).ema_indicator()
    global ema_6_1_high_bybit
    ema_6_1_high_bybit = round((df['EMA 6-1 High'][17]).astype(float),decimals)


def get_ema_6_5_low_bybit():

    bars = exchange.fetchOHLCV(symbol=symbol, timeframe='5m', limit=18)
    df = pd.DataFrame(bars,columns=['Time','Open','High','Low','Close','Vol'])
    df['EMA 6-5 Low'] = ta.trend.EMAIndicator(df['Low'], window=6).ema_indicator()
    global ema_6_5_low_bybit
    ema_6_5_low_bybit = round((df['EMA 6-5 Low'][17]).astype(float),decimals)


def get_ema_6_1_low_bybit():

    bars = exchange.fetchOHLCV(symbol=symbol, timeframe='1m', limit=18)
    df = pd.DataFrame(bars,columns=['Time','Open','High','Low','Close','Vol'])
    df['EMA 6-1 Low'] = ta.trend.EMAIndicator(df['Low'], window=6).ema_indicator()
    global ema_6_1_low_bybit
    ema_6_1_low_bybit = round((df['EMA 6-1 Low'][17]).astype(float),decimals)

# ------------------------------

def get_ema_60_1_binance():
    bars = binance_client.futures_klines(symbol=symbol, interval='1m', limit=180)
    df = pd.DataFrame(bars, columns=['Time','Open','High','Low','Close','Vol','1','2','3','4','5','6'])
    df['EMA 60-1 Close'] = ta.trend.EMAIndicator(df['Close'], window=60).ema_indicator()
    global ema_60_1_binance
    ema_60_1_binance = round((df['EMA 60-1 Close'][179]).astype(float),decimals)


def get_ema_60_5_binance():
    bars = binance_client.futures_klines(symbol=symbol, interval='5m', limit=180)
    df = pd.DataFrame(bars, columns=['Time','Open','High','Low','Close','Vol','1','2','3','4','5','6'])
    df['EMA 60-5 Close'] = ta.trend.EMAIndicator(df['Close'], window=60).ema_indicator()
    global ema_60_5_binance
    ema_60_5_binance = round((df['EMA 60-5 Close'][179]).astype(float),decimals)

# ------------------------------

def get_ema_120_1_binance():
    bars = binance_client.futures_klines(symbol=symbol,interval='1m', limit=360)
    df = pd.DataFrame(bars, columns=['Time','Open','High','Low','Close','Vol','1','2','3','4','5','6'])
    df['EMA 120-1 Close'] = ta.trend.EMAIndicator(df['Close'], window=120).ema_indicator()
    global ema_120_1_binance
    ema_120_1_binance = round((df['EMA 120-1 Close'][359]).astype(float),decimals)


def get_ema_120_5_binance():
    bars = binance_client.futures_klines(symbol=symbol,interval='5m', limit=360)
    df = pd.DataFrame(bars, columns=['Time','Open','High','Low','Close','Vol','1','2','3','4','5','6'])
    df['EMA 120-5 Close'] = ta.trend.EMAIndicator(df['Close'], window=120).ema_indicator()
    global ema_120_5_binance
    ema_120_5_binance = round((df['EMA 120-5 Close'][359]).astype(float),decimals)

# ------------------------------

def get_ema_240_1_binance():
    bars = binance_client.futures_klines(symbol=symbol,interval='1m', limit=720)
    df = pd.DataFrame(bars, columns=['Time','Open','High','Low','Close','Vol','1','2','3','4','5','6'])
    df['EMA 240-1 Close'] = ta.trend.EMAIndicator(df['Close'], window=240).ema_indicator()
    global ema_240_1_binance
    ema_240_1_binance = round((df['EMA 240-1 Close'][719]).astype(float),decimals)


def get_ema_240_5_binance():
    bars = binance_client.futures_klines(symbol=symbol,interval='5m', limit=720)
    df = pd.DataFrame(bars, columns=['Time','Open','High','Low','Close','Vol','1','2','3','4','5','6'])
    df['EMA 240-5 Close'] = ta.trend.EMAIndicator(df['Close'], window=240).ema_indicator()
    global ema_240_5_binance
    ema_240_5_binance = round((df['EMA 240-5 Close'][719]).astype(float),decimals)

# ------------------------------

def get_position():
    positions = client.my_position(symbol=symbol)
    for position in positions['result']:
        if position['side'] == 'Sell':
            global sell_position_size
            global sell_position_prce
            sell_position_size = position['size']
            sell_position_prce = position['entry_price']
        if position['side'] == 'Buy':
            global buy_position_size
            global buy_position_prce
            buy_position_size = position['size']
            buy_position_prce = position['entry_price']

####################################################################################### Start


while True:

    try:
        # Get EMAs
        get_ema_3_5_high_bybit()
        time.sleep(0.01)
        get_ema_3_5_low_bybit()
        get_ema_60_5_binance()
        time.sleep(0.01)
        get_ema_120_5_binance()
        time.sleep(0.01)
        get_ema_240_5_binance()
        get_ema_3_1_high_bybit()
        time.sleep(0.01)
        get_ema_3_1_low_bybit()
        get_ema_60_1_binance()
        time.sleep(0.01)
        get_ema_120_1_binance()
        time.sleep(0.01)
        get_ema_240_1_binance()
        get_ema_6_5_high_bybit()
        time.sleep(0.01)
        get_ema_6_1_high_bybit()
        time.sleep(0.01)
        get_ema_6_1_low_bybit()
        time.sleep(0.01)
        get_ema_6_5_low_bybit()
        time.sleep(0.01)
    except Exception as e:
        get_linenumber()
        print(line_number, 'exeception: {}'.format(e))
        pass


    ma_order_long_1m = ema_60_1_binance < ema_120_1_binance and ema_120_1_binance < ema_240_1_binance and ema_3_1_high_bybit < ema_60_1_binance
    ma_order_long_5m = ema_60_5_binance < ema_120_5_binance and ema_120_5_binance < ema_240_5_binance and ema_3_5_high_bybit < ema_60_5_binance
    
    ma_order_shrt_1m = ema_60_1_binance > ema_120_1_binance and ema_120_1_binance > ema_240_1_binance and ema_3_1_low_bybit > ema_60_1_binance
    ma_order_shrt_5m = ema_60_5_binance > ema_120_5_binance and ema_120_5_binance > ema_240_5_binance and ema_3_5_low_bybit > ema_60_5_binance

    good_ma_order_long = ma_order_long_1m == True and ma_order_long_5m == True
    good_ma_order_shrt = ma_order_shrt_1m == True and ma_order_shrt_5m == True


    try:
        # Get Orderbook data
        get_orderbook()   
    except Exception as e:
        get_linenumber()
        print(line_number, 'exeception: {}'.format(e))
        pass


    good_shrt_conditions = good_ma_order_shrt == True and ask > ema_3_5_high_bybit and ask > ema_3_1_high_bybit
    # good_long_conditions = good_ma_order_long == True and bid < ema_3_5_low_bybit and bid < ema_3_1_low_bybit
    good_long_conditions = good_ma_order_long == True and ask > ema_3_5_high_bybit and ask > ema_3_1_high_bybit


    # good_trade_conditions = good_shrt_conditions == True or good_long_conditions == True
    good_short_trade_conditions = ask > ema_3_1_high_bybit


    try:
        get_balance()
        time.sleep(0.01)
    except Exception as e:
        get_linenumber()
        print(line_number, 'exeception: {}'.format(e))
        pass


    what_1x_is = round((float(equity) / float(ask)) / (100 / float(leverage)),2)
    max_size = what_1x_is


    print('╭─────────────────────────────────────────────╮')
    print('│          Ryuryu\'s bybit bot v2.14           │')
    print('├─────────────────────────────────────────────┤')
    print('│               Asset:',symbol)
    print('│        Max leverage:',leverage)
    print('│            Lot size:',min_lot_size,'| 1x:',what_1x_is)
    print('├─────────────────────────────────────────────┤')

    if enable_trading == '1':
        print(Fore.GREEN +'│             Trading: Enabled'+ Style.RESET_ALL)
    if enable_trading == '0':
        print(Fore.RED +'│             Trading: Disabled'+ Style.RESET_ALL)

    profit = 100 - ((float(available_balance) - float(realised_pnl)) * 100 / float(available_balance))
    profit = round(profit,2)


    print('│   Available Balance:',available_balance)
    print('│        Realized PnL:',realised_pnl)
    print('│      Wallet Balance:',wallet_balance)
    print('│              Equity:',equity)
    print('├─────────────────────────────────────────────┤')
    print('│        Realized PnL:',realised_pnl)
    print('│      UnRealized PnL:',unrealised_pnl)
    print(Fore.GREEN +'│              Profit:',profit,'%'+ Style.RESET_ALL)
    print('├─────────────────────────────────────────────┤')
    print('│                 Ask:',ask)
    print('│ MA 3 High/Low on 5m:',ema_3_5_high_bybit,'/',ema_3_5_low_bybit)
    print('│ MA 3 High/Low on 1m:',ema_3_1_high_bybit,'/',ema_3_1_low_bybit)


    try:
        get_position()
        time.sleep(0.01)
    except Exception as e:
        get_linenumber()
        print(line_number, 'exeception: {}'.format(e))
        pass


    print('├─────────────────────────────────────────────┤')
    print('│  Sell Position Size:',sell_position_size) 
    print('│ Sell Position Price:',sell_position_prce)
    # print('├─────────────────────────────────────────────┤')
    # print('│   Buy Position Size:',buy_position_size) 
    # print('│  Buy Position Price:',buy_position_prce)
    print('├─────────────────────────────────────────────┤')


    ''' First Short entry '''

    if enable_trading == '1' and sell_position_size == 0 and sell_position_size < max_size and good_short_trade_conditions == True:

        try:
            place_first_entry_market_order = client.place_active_order(\
            side='Sell',\
            symbol=symbol,\
            order_type='Market',\
            qty=min_lot_size,\
            time_in_force='GoodTillCancel',\
            reduce_only=False,\
            close_on_trigger=False)
            time.sleep(0.01)
        except Exception as e:
            get_linenumber()
            print(line_number, 'exeception: {}'.format(e))
            pass
    else:
        pass
    
    
    
    ''' Cancel Entry order '''

    if float(ask) < float(ema_3_1_high_bybit) or float(ask) < float(ema_3_5_high_bybit):
        
        try:
            cancel_entry_orders()
            time.sleep(0.01)
        except Exception as e:
            get_linenumber()
            print(line_number, 'exeception: {}'.format(e))
            pass


    ''' Take Profit for Short'''

    if sell_position_size > 0:

        # percent_to_remove = 100 - tp_perc
        # sell_tp_price = round(sell_position_prce * percent_to_remove / 100,decimals)

        # sell_tp_price = round(sell_position_prce-(ema_6_5_high_bybit - ema_6_5_low_bybit),decimals)
        sell_tp_price = round(sell_position_prce-(ema_6_1_high_bybit - ema_6_1_low_bybit),decimals)

        tp_buy_order_prc = 0
        tp_buy_order_size = 0


        try:
            get_close_orders()
            time.sleep(0.01)
        except Exception as e:
            get_linenumber()
            print(line_number, 'exeception: {}'.format(e))
            pass

            
        print('│  ',sell_tp_price)
        print('│  ',tp_buy_order_prc)


        # time.sleep(333)

        
        if tp_buy_order_prc != sell_tp_price or tp_buy_order_size != sell_position_size:

            try:
                cancel_close_orders()
                time.sleep(0.01)
            except Exception as e:
                get_linenumber()
                print(line_number, 'exeception: {}'.format(e))
                pass
    
            try:
                place_active_buy_limit_tp_order = client.place_active_order(
                side='Buy',\
                symbol=symbol,\
                order_type='Limit',\
                price=sell_tp_price,\
                qty=sell_position_size,\
                time_in_force='GoodTillCancel',\
                reduce_only=True,\
                close_on_trigger=True)
                time.sleep(0.01)
            except Exception as e:
                get_linenumber()
                print(line_number, 'exeception: {}'.format(e))
                pass


    ''' Additional Short Entry Orders '''

    not_good_short_take_profit = sell_position_prce < ema_6_1_low_bybit


    if not_good_short_take_profit == True:

        print('├─────────────────────────────────────────────┤')
        print('│  Sell position < EMA6 5m, need to place')
        print('│  additional order...')


    if sell_position_size != 0 and sell_position_size < max_size and good_short_trade_conditions == True and not_good_short_take_profit == True:

        print('├─────────────────────────────────────────────┤')
        print('│  Placing order ⇲')
        
        try:
            cancel_entry_orders()
            time.sleep(0.01)
            place_entry_order = client.place_active_order(\
            side='Sell',\
            symbol=symbol,\
            order_type='Limit',\
            price=ask,\
            qty=min_lot_size,\
            time_in_force='GoodTillCancel',\
            reduce_only=False,\
            close_on_trigger=False)
            time.sleep(0.01)
        except Exception as e:
            get_linenumber()
            print(line_number, 'exeception: {}'.format(e))
            pass
    else:
        print('├─────────────────────────────────────────────┤')
        print('│  waiting...')

    
    print('├─────────────────────────────────────────────┤')
    
    if ma_order_shrt_1m == True:
        print(Fore.RED +'│ MA order Short 1m - OK'+ Style.RESET_ALL)
    else:
        print('│ MA order Short 1m - Not OK')

    if ma_order_shrt_5m == True:
        print(Fore.RED +'│ MA order Short 5m - OK'+ Style.RESET_ALL)
    else:
        print('│ MA order Short 5m - Not OK')

    print('├─────────────────────────────────────────────┤')

    if ask > ema_3_1_high_bybit:
        print(Fore.RED +'│ Ask > EMA3 on 1m'+ Style.RESET_ALL)
    else:
        print('│ Ask < EMA3 on 1m')

    if ask > ema_3_5_high_bybit:
        print(Fore.RED +'│ Ask > EMA3 on 5m'+ Style.RESET_ALL)
    else:
        print('│ Ask < EMA3 on 5m')

    time.sleep(0.02)
