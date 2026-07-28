import requests
import pandas as pd
import ta


BASE_URL = "https://api.binance.com"


def normalize_symbol(symbol):
    """
    تبدیل BTC به BTCUSDT
    """
    symbol = symbol.upper()

    if not symbol.endswith("USDT"):
        symbol += "USDT"

    return symbol


def check_symbol(symbol):
    """
    بررسی وجود جفت ارز در Binance
    """

    symbol = normalize_symbol(symbol)

    url = f"{BASE_URL}/api/v3/exchangeInfo"

    response = requests.get(url, timeout=10)
    data = response.json()

    symbols = [
        item["symbol"]
        for item in data["symbols"]
    ]

    return symbol if symbol in symbols else None



def get_price(symbol):
    """
    گرفتن قیمت لحظه‌ای
    """

    symbol = normalize_symbol(symbol)

    url = f"{BASE_URL}/api/v3/ticker/price"

    response = requests.get(
        url,
        params={"symbol": symbol},
        timeout=10
    )

    data = response.json()

    return float(data["price"])



def get_candles(symbol, interval="1h", limit=100):
    """
    گرفتن کندل‌ها برای RSI
    """

    symbol = normalize_symbol(symbol)

    url = f"{BASE_URL}/api/v3/klines"

    response = requests.get(
        url,
        params={
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        },
        timeout=10
    )

    data = response.json()

    candles = pd.DataFrame(
        data,
        columns=[
            "time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_volume",
            "trades",
            "taker_buy_base",
            "taker_buy_quote",
            "ignore"
        ]
    )

    candles["close"] = candles["close"].astype(float)

    return candles



def get_rsi(symbol, interval="1h"):
    """
    محاسبه RSI 14
    """

    candles = get_candles(
        symbol,
        interval
    )

    rsi = ta.momentum.RSIIndicator(
        candles["close"],
        window=14
    )

    value = rsi.rsi().iloc[-1]

    return round(float(value), 2)
