import os
import requests

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
}

RSI_PERIOD = 14

# کش برای هر ترکیب symbol+timeframe -> فقط یک بار در هر اجرا از بایننس گرفته میشه
_KLINES_CACHE = {}


def get_active_alarms():
    url = f"{SUPABASE_URL}/rest/v1/alarms?active=eq.true"
    r = requests.get(url, headers=HEADERS, timeout=15)
    r.raise_for_status()
    return r.json()


def update_alarm(alarm_id, fields):
    url = f"{SUPABASE_URL}/rest/v1/alarms?id=eq.{alarm_id}"
    r = requests.patch(url, headers=HEADERS, json=fields, timeout=15)
    r.raise_for_status()


def get_klines_cached(symbol, interval, limit=100):
    key = (symbol, interval)
    if key in _KLINES_CACHE:
        return _KLINES_CACHE[key]

    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    klines = r.json()

    _KLINES_CACHE[key] = klines
    return klines


def compute_rsi(closes, period=RSI_PERIOD):
    if len(closes) < period + 1:
        return None

    deltas = [closes[i + 1] - closes[i] for i in range(len(closes) - 1)]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


def send_telegram(chat_id, text, tradingview_url):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "reply_markup": {
            "inline_keyboard": [[{"text": "📊 مشاهده در TradingView", "url": tradingview_url}]]
        },
    }
    r = requests.post(url, json=payload, timeout=15)
    r.raise_for_status()


def fire_alert(alarm, price, rsi_value):
    symbol = alarm["symbol"]
    tv_url = f"https://www.tradingview.com/chart/?symbol=BINANCE:{symbol}"
    direction_fa = "بالای" if alarm["direction"] == "above" else "پایین"

    text = (
        f"🚨 {symbol}\n"
        f"قیمت: {price}\n"
        f"تایم‌فریم: {alarm['timeframe']}\n"
        f"Trigger: {alarm['trigger_type']} {direction_fa} {alarm['target_price']}"
    )
    if alarm.get("rsi_on"):
        text += f"\nRSI: {rsi_value if rsi_value is not None else 'نامشخص'}"

    send_telegram(alarm["user_id"], text, tv_url)


def check_close(alarm, closed_candle, rsi_value):
    candle_time = closed_candle[0]
    close_price = float(closed_candle[4])
    target = float(alarm["target_price"])

    if alarm.get("last_checked_candle_time") == candle_time:
        return

    hit = (
        (alarm["direction"] == "above" and close_price >= target)
        or (alarm["direction"] == "below" and close_price <= target)
    )

    update_alarm(alarm["id"], {"last_checked_candle_time": candle_time})

    if hit:
        fire_alert(alarm, close_price, rsi_value)


def check_touch(alarm, open_candle, rsi_value):
    candle_time = open_candle[0]
    high = float(open_candle[2])
    low = float(open_candle[3])
    target = float(alarm["target_price"])

    if alarm.get("last_checked_candle_time") != candle_time:
        update_alarm(alarm["id"], {
            "last_checked_candle_time": candle_time,
            "already_touched_this_candle": False,
        })
        alarm["already_touched_this_candle"] = False

    if alarm.get("already_touched_this_candle"):
        return

    hit = (
        (alarm["direction"] == "above" and high >= target)
        or (alarm["direction"] == "below" and low <= target)
    )

    if hit:
        update_alarm(alarm["id"], {"already_touched_this_candle": True})
        fire_alert(alarm, target, rsi_value)


def check_alarm(alarm):
    klines = get_klines_cached(alarm["symbol"], alarm["timeframe"], limit=100)
    if len(klines) < 2:
        return

    closed_candle = klines[-2]
    open_candle = klines[-1]

    rsi_value = None
    if alarm.get("rsi_on"):
        closed_closes = [float(k[4]) for k in klines[:-1]]
        rsi_value = compute_rsi(closed_closes)

    if alarm["trigger_type"] == "Close":
        check_close(alarm, closed_candle, rsi_value)
    else:
        check_touch(alarm, open_candle, rsi_value)


def main():
    alarms = get_active_alarms()
    for alarm in alarms:
        try:
            check_alarm(alarm)
        except Exception as e:
            print(f"خطا در چک آلارم {alarm.get('id')}: {e}")


if __name__ == "__main__":
    main()
