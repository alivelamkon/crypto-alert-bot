from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ---------- Conversation states ----------
CAPITAL, RISK_PERCENT, ENTRY, STOP_LOSS, LEVERAGE = range(5)


def ask_capital_text():
    return "سرمایه‌ت رو بفرست (دلار، فقط عدد):"


async def start_calculator(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """وقتی کاربر دکمه‌ی پایین '🧮 ماشین حساب' یا 'دوباره محاسبه کن' رو می‌زنه"""
    context.user_data["calc"] = {}
    if update.message:
        await update.message.reply_text(ask_capital_text())
    else:
        await update.callback_query.edit_message_text(ask_capital_text())
    return CAPITAL


async def got_capital(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        value = float(update.message.text.strip().replace(",", ""))
        if value <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("عدد معتبر نیست، دوباره بفرست (فقط عدد مثبت):")
        return CAPITAL

    context.user_data["calc"]["capital"] = value
    await update.message.reply_text("درصد ریسک چقدره؟ (مثلاً 2 برای ۲٪):")
    return RISK_PERCENT


async def got_risk_percent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        value = float(update.message.text.strip().replace(",", ""))
        if value <= 0 or value > 100:
            raise ValueError
    except ValueError:
        await update.message.reply_text("عدد معتبر نیست، درصدی بین 0 تا 100 بفرست:")
        return RISK_PERCENT

    context.user_data["calc"]["risk_percent"] = value
    await update.message.reply_text("نقطه ورود چند بود؟")
    return ENTRY


async def got_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        value = float(update.message.text.strip().replace(",", ""))
        if value <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("عدد معتبر نیست، دوباره بفرست:")
        return ENTRY

    context.user_data["calc"]["entry"] = value
    await update.message.reply_text("حد ضرر چند بود؟")
    return STOP_LOSS


async def got_stop_loss(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        value = float(update.message.text.strip().replace(",", ""))
        if value <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("عدد معتبر نیست، دوباره بفرست:")
        return STOP_LOSS

    entry = context.user_data["calc"]["entry"]
    if value == entry:
        await update.message.reply_text("حد ضرر نمی‌تونه دقیقاً برابر نقطه ورود باشه، دوباره بفرست:")
        return STOP_LOSS

    context.user_data["calc"]["stop_loss"] = value
    await update.message.reply_text("لورج چند بود؟ (مثلاً 10):")
    return LEVERAGE


async def got_leverage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        value = float(update.message.text.strip().replace(",", ""))
        if value <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("عدد معتبر نیست، دوباره بفرست:")
        return LEVERAGE

    calc = context.user_data["calc"]
    calc["leverage"] = value

    capital = calc["capital"]
    risk_percent = calc["risk_percent"]
    entry = calc["entry"]
    stop_loss = calc["stop_loss"]
    leverage = calc["leverage"]

    risk_amount = capital * (risk_percent / 100)
    stop_distance_percent = abs(entry - stop_loss) / entry
    position_size = risk_amount / stop_distance_percent
    margin_required = position_size / leverage

    text = (
        "📊 نتیجه محاسبه:\n\n"
        f"💰 مبلغ ریسک: {risk_amount:,.2f}$\n"
        f"📏 حجم پوزیشن: {position_size:,.2f}$\n"
        f"🔒 مارجین لازم: {margin_required:,.2f}$"
    )

    buttons = [[InlineKeyboardButton("🔁 دوباره محاسبه کن", callback_data="calc_restart")]]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))

    context.user_data.pop("calc", None)
    return ConversationHandler.END


async def restart_from_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["calc"] = {}
    await query.edit_message_text(ask_capital_text())
    return CAPITAL


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("calc", None)
    await update.message.reply_text("لغو شد.")
    return ConversationHandler.END


def register_calculator_handlers(app):
    """این تابع رو bot.py صدا می‌زنه تا هندلرهای ماشین‌حساب رو ثبت کنه"""
    conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^🧮 ماشین حساب$"), start_calculator),
            CallbackQueryHandler(restart_from_button, pattern="^calc_restart$"),
        ],
        states={
            CAPITAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, got_capital)],
            RISK_PERCENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, got_risk_percent)],
            ENTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, got_entry)],
            STOP_LOSS: [MessageHandler(filters.TEXT & ~filters.COMMAND, got_stop_loss)],
            LEVERAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, got_leverage)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(conv)
