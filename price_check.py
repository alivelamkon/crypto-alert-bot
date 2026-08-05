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


def get_active_alarms():
    url = f"{SUPABASE_URL}/rest/v1/alarms?active=eq.true"
    r = requests.get(url, headers=HEADERS, timeout=15)
    r.raise_for_status()
    return r.json()


def update_alarm(alarm_id, fields):
    url = f"{SUPABASE_URL}/rest/v1/alarms?id=eq.{alarm_id}"
    r = requests.patch(url, headers=HEADERS, json=fields, timeout=15)
    r.raise_for_status()


def get_klines(symbol, interval, limit=2):
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    return r.json()


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


def fire_alert(alarm, price):
    symbol = alarm["symbol"]
    tv_url = f"https://www.tradingview.com/chart/?symbol=BINANCE:{symbol}"
    direction_fa = "بالای" if alarm["direction"] == "above" else "پایین"
    text = (
        f"🚨 {symbol}\n"
        f"قیمت: {price}\n"
        f"تایم‌فریم: {alarm['timeframe']}\n"
        f"Trigger: {alarm['trigger_type']} {direction_fa} {alarm['target_price']}"
    )
    send_telegram(alarm["user_id"], text, tv_url)


def check_close(alarm, closed_candle):
    candle_time = closed_candle[0]
    close_price = float(closed_candle[4])
    target = float(alarm["target_price"])

    if alarm.get("last_checked_candle_time") == candle_time:
        return  # این کندل قبلاً چک شده

    hit = (
        (alarm["direction"] == "above" and close_price >= target)
        or (alarm["direction"] == "below" and close_price <= target)
    )

    update_alarm(alarm["id"], {"last_checked_candle_time": candle_time})

    if hit:
        fire_alert(alarm, close_price)


def check_touch(alarm, open_candle):
    candle_time = open_candle[0]
    high = float(open_candle[2])
    low = float(open_candle[3])
    target = float(alarm["target_price"])

    # کندل جدید شروع شده -> فلگ تاچ رو ریست کن
    if alarm.get("last_checked_candle_time") != candle_time:
        update_alarm(alarm["id"], {
            "last_checked_candle_time": candle_time,
            "already_touched_this_candle": False,
        })
        alarm["already_touched_this_candle"] = False

    if alarm.get("already_touched_this_candle"):
        return  # قبلاً تو همین کندل تاچ رو گزارش دادیم

    hit = (
        (alarm["direction"] == "above" and high >= target)
        or (alarm["direction"] == "below" and low <= target)
    )

    if hit:
        update_alarm(alarm["id"], {"already_touched_this_candle": True})
        fire_alert(alarm, target)


def check_alarm(alarm):
    klines = get_klines(alarm["symbol"], alarm["timeframe"], limit=2)
    if len(klines) < 2:
        return

    closed_candle = klines[-2]  # کندل بسته‌شده
    open_candle = klines[-1]    # کندل در حال شکل‌گیری

    if alarm["trigger_type"] == "Close":
        check_close(alarm, closed_candle)
    else:
        check_touch(alarm, open_candle)


def main():
    alarms = get_active_alarms()
    for alarm in alarms:
        try:
            check_alarm(alarm)
        except Exception as e:
            print(f"خطا در چک آلارم {alarm.get('id')}: {e}")


if __name__ == "__main__":
    main()
