import os

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
    ConversationHandler
)

from database import init_db, get_user_alerts
from binance import check_symbol, get_price


TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]


SYMBOL = 1


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    keyboard = [
        [
            InlineKeyboardButton(
                "➕ ساخت آلارم",
                callback_data="create"
            )
        ],
        [
            InlineKeyboardButton(
                "🔔 آلارم‌های من",
                callback_data="my_alerts"
            )
        ]
    ]

    await update.message.reply_text(
        "🤖 Crypto Alert Bot\n\n"
        "آماده ساخت آلارم کریپتو هستم.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def my_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    alerts = get_user_alerts(
        query.from_user.id
    )

    if not alerts:
        text = "🔔 هیچ آلارمی ندارید."
    else:
        text = "🔔 آلارم‌های شما:\n\n"

        for alert in alerts:
            text += (
                f"#{alert[0]} {alert[2]}\n"
                f"🎯 {alert[3]}\n"
                f"📌 {alert[9]}\n\n"
            )

    await query.edit_message_text(text)


async def create_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "نام ارز را وارد کن:\n\n"
        "مثال:\n"
        "BTC"
    )

    return SYMBOL


async def receive_symbol(update: Update, context: ContextTypes.DEFAULT_TYPE):

    symbol = update.message.text.upper()

    result = check_symbol(symbol)

    if not result:
        await update.message.reply_text(
            "❌ این ارز در Binance پیدا نشد.\n"
            "دوباره وارد کن:"
        )
        return SYMBOL

    price = get_price(result)

    context.user_data["symbol"] = result

    await update.message.reply_text(
        f"✅ {result} پیدا شد.\n\n"
        f"💰 قیمت فعلی:\n"
        f"{price} USDT\n\n"
        "مرحله بعدی در نسخه بعدی اضافه می‌شود."
    )

    return ConversationHandler.END



def main():

    init_db()

    app = Application.builder().token(TOKEN).build()


    conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                create_alert,
                pattern="^create$"
            )
        ],
        states={
            SYMBOL: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    receive_symbol
                )
            ]
        },
        fallbacks=[]
    )


    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            my_alerts,
            pattern="^my_alerts$"
        )
    )

    app.add_handler(conv)


    app.run_polling()



if __name__ == "__main__":
    main()
