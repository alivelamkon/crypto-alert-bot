import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
)

from database import init_db, get_user_alerts


TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("➕ ساخت آلارم", callback_data="create"),
        ],
        [
            InlineKeyboardButton("🔔 آلارم‌های من", callback_data="my_alerts"),
        ],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🤖 Crypto Alert Bot\n\n"
        "آماده دریافت آلارم‌های کریپتو هستم.",
        reply_markup=reply_markup
    )


async def my_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    alerts = get_user_alerts(user_id)

    if not alerts:
        text = "🔔 هیچ آلارمی ثبت نشده."
    else:
        text = "🔔 آلارم‌های شما:\n\n"

        for alert in alerts:
            text += (
                f"#{alert[0]} | {alert[2]}\n"
                f"🎯 قیمت: {alert[3]}\n"
                f"📌 وضعیت: {alert[8]}\n\n"
            )

    await query.edit_message_text(text)


async def create_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "➕ ساخت آلارم\n\n"
        "در نسخه بعدی، مرحله به مرحله ازت می‌پرسم:\n"
        "1) ارز\n"
        "2) قیمت\n"
        "3) نوع فعال شدن\n"
        "4) تایم‌فریم\n"
        "5) تکرار"
    )


def main():
    init_db()

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(
        CallbackQueryHandler(
            my_alerts,
            pattern="my_alerts"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            create_alert,
            pattern="create"
        )
    )

    app.run_polling()


if __name__ == "__main__":
    main()
