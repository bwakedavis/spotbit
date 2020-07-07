from flask import Flask, render_template
import json
import time
from  datetime import datetime, timedelta
import sqlite3
import sys
import ccxt
import os
from threading import Thread
from pathlib import Path 

#Config Settings
allowedFields = ["pruneDepth", "exchanges", "currencies"]
configPath = Path("~/.spotbit/spotbit.config").expanduser()
#Default values; these will be overwritten when the config file is read
pruneDepth = 1e5
exchanges = ["bitmex", "coinbase"]
currencies = ["USD"]
currency="USD"
#Database
p = Path("~/.spotbit/sb.db").expanduser()
db = sqlite3.connect(p)
print("db opened in {}".format(p))
app = Flask(__name__)

# Create a dict that contains ccxt objects for every supported exchange. 
# The API will query a subset of these exchanges based on what the user has specified
# Unsupported exchanges: bitvaro phemex
def init_supported_exchanges():
    objects = {"acx":ccxt.acx(), "anxpro":ccxt.anxpro(), "aofex":ccxt.aofex(), "bcex":ccxt.bcex(), "bequant":ccxt.bequant(), "bibox":ccxt.bibox(), "bigone":ccxt.bigone(), "binance":ccxt.binance(), "bit2c":ccxt.bit2c(), "bitbank":ccxt.bitbank(), "bitbay":ccxt.bitbay(), "bitfinex":ccxt.bitfinex(), "bitflyer":ccxt.bitflyer(), "bitforex":ccxt.bitforex(), "bithumb":ccxt.bithumb(), "bitkk":ccxt.bitkk(), "bitmart":ccxt.bitmart(), "bitmax":ccxt.bitmax(), "bitstamp":ccxt.bitstamp(), "bittrex":ccxt.bittrex(), "bitz":ccxt.bitz(), "bl3p":ccxt.bl3p(), "bleutrade":ccxt.bleutrade(), "braziliex":ccxt.braziliex(), "btcalpha":ccxt.btcalpha(), "btcbox":ccxt.btcbox(), "btcmarkets":ccxt.btcmarkets(), "btctradeim":ccxt.btctradeim(), "btctradeua":ccxt.btctradeua(), "btcturk":ccxt.btcturk(), "buda":ccxt.buda(), "bw":ccxt.bw(), "bybit":ccxt.bybit(), "bytetrade":ccxt.bytetrade(), "cex":ccxt.cex(), "chilebit":ccxt.chilebit(), "coinbase":ccxt.coinbase(), "coincheck":ccxt.coincheck(), "coinegg":ccxt.coinegg(), "coinex":ccxt.coinex(), "coinfalcon":ccxt.coinfalcon(), "coinfloor":ccxt.coinfloor(), "coingi":ccxt.coingi(), "coinmarketcap":ccxt.coinmarketcap(), "coinmate":ccxt.coinmate(), "coinone":ccxt.coinone(), "coinspot":ccxt.coinspot(), "coolcoin":ccxt.coolcoin(), "coss":ccxt.coss(), "crex24":ccxt.crex24(), "currencycom":ccxt.currencycom(), "deribit":ccxt.deribit(), "digifinex":ccxt.digifinex(), "dsx":ccxt.dsx(), "eterbase":ccxt.eterbase(), "exmo":ccxt.exmo(), "exx":ccxt.exx(), "fcoin":ccxt.fcoin(), "fcoinjp":ccxt.fcoinjp, "flowbtc":ccxt.flowbtc(), "foxbit":ccxt.foxbit(), "ftx":ccxt.ftx(), "fybse":ccxt.fybse(), "gateio":ccxt.gateio(), "gemini":ccxt.gemini(), "hbtc":ccxt.hbtc(), "hitbtc":ccxt.hitbtc(), "hollaex":ccxt.hollaex(), "huobipro":ccxt.huobipro(), "ice3x":ccxt.ice3x(), "idex":ccxt.idex(), "independentreserve":ccxt.independentreserve(), "indodax":ccxt.indodax(), "itbit":ccxt.itbit(), "kraken":ccxt.kraken(), "kucoin":ccxt.kucoin(), "kuna":ccxt.kuna(), "lakebtc":ccxt.lakebtc(), "latoken":ccxt.latoken(), "lbank":ccxt.lbank(), "liquid":ccxt.liquid(), "livecoin":ccxt.livecoin(), "luno":ccxt.luno(), "lykke":ccxt.lykke(), "mercado":ccxt.mercado(), "mixcoins":ccxt.mixcoins(), "oceanex":ccxt.oceanex(), "okcoin":ccxt.okcoin(), "okex":ccxt.okex(), "paymium":ccxt.paymium(), "poloniex":ccxt.poloniex(), "probit":ccxt.probit(), "qtrade":ccxt.qtrade(), "rightbtc":ccxt.rightbtc(), "southxchange":ccxt.southxchange(), "stex":ccxt.stex(), "stronghold":ccxt.stronghold(), "surbitcoin":ccxt.surbitcoin(), "therock":ccxt.therock(), "tidebit":ccxt.tidebit(), "tidex":ccxt.tidex(), "upbit":ccxt.upbit(), "vaultoro":ccxt.vaultoro(), "vbtc":ccxt.vbtc(), "wavesexchange":ccxt.wavesexchange(), "whitebit":ccxt.whitebit(), "xbtce":ccxt.xbtce(), "yobit":ccxt.yobit(), "zaif":ccxt.zaif(), "zb":ccxt.zb()}
    return objects

# Check if a given exchange is in the list of supported exchanges.
# Currently, the list of supported exchanges is all those supported by ccxt aside from a small handful.
def is_supported(exchange):
    try:
        obj = ex_objs[exchange]
        if obj != None:
            return True
        else:
            return False
    except Exception as e:
        return False

# We create a list of all exchanges to do error checking on user input
ex_objs = init_supported_exchanges()
print("created list of {} exchanges".format(len(ex_objs)))

@app.route('/status')
def status():
    return "server is running"

# Get the latest price entry in the database.
@app.route('/now/<currency>/<exchange>')
def now(currency, exchange):
    db_n = sqlite3.connect(p)
    ticker = "BTC-{}".format(currency.upper())
    statement = "SELECT * FROM {} WHERE pair = '{}' AND timestamp = (SELECT MAX(timestamp) FROM {}) LIMIT 1;".format(exchange, ticker, exchange)
    cursor = db_n.execute(statement)
    res = cursor.fetchone()
    db_n.close()
    print(res)
    return {'id':res[0], 'timestamp':res[1], 'datetime':res[2], 'currency_pair':res[3], 'open':res[4], 'high':res[5], 'low':res[6], 'close':res[7], 'vol':res[8]} 

# Get data from local storage inside of a certain range.
@app.route('/hist/<currency>/<exchange>/<date_start>/<date_end>', methods=['GET'])
def hist(currency, exchange, date_start, date_end):
    db_n = sqlite3.connect(p)
    if (str(date_start)).isdigit():
        date_s = (datetime.fromisoformat(date_start.replace("T", " "))).timestamp()*1000
        date_e = (datetime.fromisoformat(date_end.replace("T", " "))).timestamp()*1000
    else:
        date_s = (datetime.fromisoformat(date_start.replace("T", " ")))
        date_e = (datetime.fromisoformat(date_end.replace("T", " ")))
    statement = "SELECT * FROM {} WHERE datetime > '{}' AND datetime < '{}';".format(exchange, date_s, date_e)
    cursor = db_n.execute(statement)
    res = cursor.fetchall()
    db_n.close()
    return {'data':res}

# Make an HTTP GET request to exchanges via the ccxt API
# TODO: add error checking for if an exchange supports ohlc data. If not, default to regular price data. (done)
# Loop through all chosen exchanges, check if they are supported, loop through all chosen currencies, for each make request to ohlc endpoint if supported, else price ticker. Write data to local storage.
# Bitfinex special rule: bitfinex returns candles from the beginning of time, not the most recent. This is a behavior of the API itself and has nothing to do with this code or ccxt. Therefore we must specify the timeframe desired in the optional params field of the function call with a dictionary of available options.
def request(exchanges,currency,interval):
    db_n = sqlite3.connect(p)
    while True:
        for e in exchanges:
            if is_supported(e):
                for curr in currencies:
                        ticker = "BTC/{}".format(curr)
                        if ex_objs[e].has['fetchOHLCV']:
                            candle = None
                            if e == "bitfinex":
                                params = {'limit':100, 'start':(round((datetime.now()-timedelta(hours=1)).timestamp()*1000)), 'end':round(datetime.now().timestamp()*1000)}
                                candle = ex_objs[e].fetch_ohlcv(symbol=ticker, timeframe='1m', since=None, params=params)
                                print(candle)
                            else:
                                candle = ex_objs[e].fetch_ohlcv(ticker, '1m') #'ticker' was listed as 'symbol' before | interval should be determined in the config file 
                            for line in candle:
                                ts = datetime.fromtimestamp(line[0]/1e3) #check here if we have a ms timestamp or not
                                statement = "INSERT INTO {} (timestamp, datetime, pair, open, high, low, close, volume) VALUES ({}, '{}', '{}', {}, {}, {}, {}, {});".format(e, line[0], ts, ticker.replace("/", "-"), line[1], line[2], line[3], line[4], line[5])
                                db_n.execute(statement)
                                db_n.commit()
                            print("inserted into {} {} {} times".format(e, curr, len(candle)))
                        else:
                            price = ex_objs[e].fetch_ticker(ticker)
                            ts = datetime.fromtimestamp(price['timestamp'])
                            statement = "INSERT INTO {} (timestamp, datetime, pair, open, high, low, close, volume) VALUES ({}, '{}', '{}', {}, {}, {}, {}, {});".format(e, price['timestamp'], ts, ticker.replace("/", "-"), 0.0, 0.0, 0.0, price['last'], 0.0)
                            print(statement)
                            db_n.execute(statement)
                            db_n.commit()
                        time.sleep(interval)
    db_n.close()

# Read the values stored in the config file and store them in memory.
# Run during install and at every run of the server.
# Returns void
def read_config():
    with open(configPath, "r") as f:
        lines = f.readlines()
        #read each line in the file
        for line in lines:
            #split the current line
            setting_line = line.split("=")
            #if there are invalid lines in the file ignore them
            if setting_line[0] not in allowedFields:
                print("invalid config setting {}".format(setting_line[0]))
            elif setting_line[0] == "pruneDepth":
                try:
                    pruneDepth = int(setting_line[1])
                except Exception as e:
                    print("could not read pruneDepth field. Using default setting. Error: {}".format(e))
            elif setting_line[0] == "exchanges":
                exs = setting_line[1].split(" ")
                for e in exs:
                    if is_supported(e) == False:
                        print("{} is not supported by ccxt!".format(e))
                    e_formatted = e.replace("\n", "")
                    if e_formatted not in exchanges:
                        if "\n" in e:
                            exchanges.append(e_formatted)
                        else:
                            exchanges.append(e_formatted)
            elif setting_line[0] == "currencies":
                currs = setting_line[1].split(" ")
                for c in currs:
                    #need to make sure currency codes are all caps and have newlines dropped off
                    c_formatted = (c.replace("\n", "")).upper()
                    if c_formatted not in currencies:
                        if "\n" in c:
                            currencies.append(c_formatted)
                        else:
                            currencies.append(c_formatted)
            else:
                return
    #print statement for debugging
    print("Settings read:\n pruneDepth: {}\n exchanges: {}\n currencies: {}".format(pruneDepth, exchanges, currencies))

# This method is called at the first run.
# It sets up the required tables inside of a local sqlite3 database. There is one table for each exchange.
# Tables are only created if they do not already exist. Install will attempt to create tables for every listed exchange at once when called.
def install():
    read_config()
    #create the sqlite db
    print("creating tables for {} exchanges.".format(len(exchanges)))
    for exchange in exchanges:
        #change this to f-strings
        sql = "CREATE TABLE IF NOT EXISTS {} (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp INTEGER, datetime TEXT, pair TEXT, open REAL, high REAL, low REAL, close REAL, volume REAL)".format(exchange)
        print("created table for {}".format(exchange))
        db.execute(sql)
        db.commit()
    db.close()

# drop length - pruneDepth from each table. 
# if there is nothing to prune then nothing will be pruned.
def prune(pruneDepth):
    for exchange in exchanges:
        cursor = db.execute("SELECT id FROM {}".format(exchange))
        length = cursor[-1][0]
        statement = "DELETE FROM {} WHERE id < {};".format(exchange, length-pruneDepth)
        db.execute(statement)
        db.commit()

if __name__ == "__main__":
    install() #install will call read_config
    prices_thread = Thread(target=request, args=(exchanges, currency, 5))
    prices_thread.start()
    app.run()
    db.close()

