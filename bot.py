import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from supabase import create_client


# =====================
# ENV VARIABLES
# =====================

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


# =====================
# SUPABASE CONNECTION
# =====================

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)


# =====================
# START MENU
# =====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    keyboard = [
        [
            InlineKeyboardButton(
                "➕ ساخت آلارم",
                callback_data="create_alert"
            )
        ],
        [
            InlineKeyboardButton(
                "📋 آلارم‌های من",
                callback_data="my_alerts"
            )
        ],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "سلام 👋\nربات آلارم کریپتو آماده است.",
        reply_markup=reply_markup
    )


# =====================
# BUTTON HANDLER
# =====================

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)

    if query.data == "create_alert":

        await query.edit_message_text(
            "➕ ساخت آلارم\n\n"
            "این بخش در مرحله بعد تکمیل می‌شود."
        )


    elif query.data == "my_alerts":

        result = (
            supabase
            .table("alerts")
            .select("*")
            .eq("user_id", user_id)
            .execute()
        )

        alerts = result.data

        if not alerts:
            text = "📭 هیچ آلارمی ثبت نشده."
        else:
            text = "📋 آلارم‌های شما:\n\n"

            for alert in alerts:
                text += (
                    f"🔹 {alert['symbol']}\n"
                    f"💰 {alert['target_price']}\n"
                    f"⏱ {alert['timeframe']}\n\n"
                )

        await query.edit_message_text(text)


# =====================
# MAIN
# =====================

def main():

    app = Application.builder() \
        .token(BOT_TOKEN) \
        .build()


    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    app.add_handler(
        CallbackQueryHandler(buttons)
    )


    print("Bot started...")

    app.run_polling()


if __name__ == "__main__":
    main()
