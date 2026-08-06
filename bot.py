import os
import logging

from aiohttp import web
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from price_check import run_price_check
from alarms import register_alarms_handlers

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# ---------- Environment variables (set these in Render) ----------
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
RENDER_EXTERNAL_URL = os.environ["RENDER_EXTERNAL_URL"]
PORT = int(os.environ.get("PORT", 10000))

# ---------- import هوشمند برای بخش‌هایی که هنوز ساخته نشدن ----------
try:
    from portfolio import register_portfolio_handlers
    HAS_PORTFOLIO = True
except ImportError:
    HAS_PORTFOLIO = False

try:
    from journal import register_journal_handlers
    HAS_JOURNAL = True
except ImportError:
    HAS_JOURNAL = False

try:
    from calculator import register_calculator_handlers
    HAS_CALCULATOR = True
except ImportError:
    HAS_CALCULATOR = False

# ---------- منوی پایین ثابت (Reply Keyboard) ----------
MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["🔔 آلارم", "💼 پورتفولیو"],
        ["📝 ژورنال", "🧮 ماشین حساب"],
    ],
    resize_keyboard=True,
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام! از منو انتخاب کن:", reply_markup=MAIN_KEYBOARD)


async def coming_soon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚧 این بخش هنوز ساخته نشده، به‌زودی اضافه میشه.")


def build_application():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    # آلارم - همیشه فعال
    register_alarms_handlers(app)

    # پورتفولیو - اگه فایلش موجود بود فعال، وگرنه پیام "به‌زودی"
    if HAS_PORTFOLIO:
        register_portfolio_handlers(app)
    else:
        app.add_handler(MessageHandler(filters.Regex("^💼 پورتفولیو$"), coming_soon))

    # ژورنال - اگه فایلش موجود بود فعال، وگرنه پیام "به‌زودی"
    if HAS_JOURNAL:
        register_journal_handlers(app)
    else:
        app.add_handler(MessageHandler(filters.Regex("^📝 ژورنال$"), coming_soon))

    # ماشین حساب - اگه فایلش موجود بود فعال، وگرنه پیام "به‌زودی"
    if HAS_CALCULATOR:
        register_calculator_handlers(app)
    else:
        app.add_handler(MessageHandler(filters.Regex("^🧮 ماشین حساب$"), coming_soon))

    return app


application = build_application()


# ---------- aiohttp web server: telegram webhook + price-check endpoint ----------
async def telegram_webhook(request: web.Request):
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return web.Response(text="OK")


async def check_prices(request: web.Request):
    try:
        n = run_price_check()
        return web.Response(text=f"checked {n} alarms")
    except Exception as e:
        log.exception("price check failed")
        return web.Response(text=f"error: {e}", status=500)


async def health(request: web.Request):
    return web.Response(text="alive")


async def on_startup(app: web.Application):
    await application.initialize()
    await application.bot.set_webhook(url=f"{RENDER_EXTERNAL_URL}/{TELEGRAM_TOKEN}")
    await application.start()
    log.info("Application started, webhook set")


async def on_cleanup(app: web.Application):
    await application.stop()
    await application.shutdown()


def main():
    web_app = web.Application()
    web_app.router.add_post(f"/{TELEGRAM_TOKEN}", telegram_webhook)
    web_app.router.add_get("/check", check_prices)
    web_app.router.add_get("/", health)
    web_app.on_startup.append(on_startup)
    web_app.on_cleanup.append(on_cleanup)
    web.run_app(web_app, host="0.0.0.0", port=PORT)


if __name__ == "__main__":
    main()
