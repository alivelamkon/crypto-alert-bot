import os
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from supabase import create_client, Client

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# ---------- Environment variables (set these in Render) ----------
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
RENDER_EXTERNAL_URL = os.environ["RENDER_EXTERNAL_URL"]  # e.g. https://your-app.onrender.com
PORT = int(os.environ.get("PORT", 10000))

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------- Conversation states ----------
SYMBOL, TIMEFRAME, TRIGGER_TYPE, DIRECTION, PRICE, RSI, CONFIRM = range(7)

TIMEFRAMES = ["15m", "1h", "4h", "1d"]


def main_menu_keyboard():
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("➕ آلارم جدید", callback_data="new_alarm")],
            [InlineKeyboardButton("📋 آلارم‌های من", callback_data="list_alarms")],
            [InlineKeyboardButton("🗑 حذف آلارم", callback_data="delete_alarm")],
        ]
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام! از منو انتخاب کن:", reply_markup=main_menu_keyboard())


async def menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "new_alarm":
        await query.edit_message_text("نماد ارز رو بفرست (مثلاً BTC یا ETH):")
        return SYMBOL

    if query.data == "list_alarms":
        await show_alarms(query, context)
        return ConversationHandler.END

    if query.data == "delete_alarm":
        await show_delete_list(query, context)
        return ConversationHandler.END

    if query.data.startswith("del_"):
        alarm_id = int(query.data.split("_", 1)[1])
        supabase.table("alarms").delete().eq("id", alarm_id).execute()
        await query.edit_message_text("آلارم حذف شد ✅")
        return ConversationHandler.END


async def show_alarms(query, context):
    user_id = query.from_user.id
    res = supabase.table("alarms").select("*").eq("user_id", user_id).eq("active", True).execute()
    rows = res.data
    if not rows:
        await query.edit_message_text("هیچ آلارم فعالی نداری.")
        return
    lines = []
    for r in rows:
        lines.append(
            f"• {r['symbol']} | {r['timeframe']} | {r['trigger_type']} "
            f"{'بالای' if r['direction']=='above' else 'پایین'} {r['target_price']} "
            f"| RSI: {'✅' if r['rsi_on'] else '❌'}"
        )
    await query.edit_message_text("\n".join(lines))


async def show_delete_list(query, context):
    user_id = query.from_user.id
    res = supabase.table("alarms").select("*").eq("user_id", user_id).eq("active", True).execute()
    rows = res.data
    if not rows:
        await query.edit_message_text("چیزی برای حذف نیست.")
        return
    buttons = [
        [InlineKeyboardButton(f"{r['symbol']} {r['timeframe']} {r['target_price']}", callback_data=f"del_{r['id']}")]
        for r in rows
    ]
    await query.edit_message_text("کدوم رو حذف کنم؟", reply_markup=InlineKeyboardMarkup(buttons))


# ---------- New alarm conversation ----------
async def got_symbol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    symbol = update.message.text.strip().upper()
    if not symbol.endswith("USDT"):
        symbol += "USDT"
    context.user_data["symbol"] = symbol

    buttons = [[InlineKeyboardButton(tf, callback_data=f"tf_{tf}") for tf in TIMEFRAMES]]
    await update.message.reply_text("تایم‌فریم رو انتخاب کن:", reply_markup=InlineKeyboardMarkup(buttons))
    return TIMEFRAME


async def got_timeframe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["timeframe"] = query.data.split("_", 1)[1]

    buttons = [
        [
            InlineKeyboardButton("🎯 Touch", callback_data="trg_Touch"),
            InlineKeyboardButton("🔒 Close", callback_data="trg_Close"),
        ]
    ]
    await query.edit_message_text("نوع Trigger رو انتخاب کن:", reply_markup=InlineKeyboardMarkup(buttons))
    return TRIGGER_TYPE


async def got_trigger_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["trigger_type"] = query.data.split("_", 1)[1]

    buttons = [
        [
            InlineKeyboardButton("📈 بالای قیمت", callback_data="dir_above"),
            InlineKeyboardButton("📉 پایین قیمت", callback_data="dir_below"),
        ]
    ]
    await query.edit_message_text("جهت رو انتخاب کن:", reply_markup=InlineKeyboardMarkup(buttons))
    return DIRECTION


async def got_direction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["direction"] = query.data.split("_", 1)[1]
    await query.edit_message_text("قیمت هدف رو بفرست (مثلاً 70000):")
    return PRICE


async def got_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().replace(",", "")
    try:
        price = float(text)
    except ValueError:
        await update.message.reply_text("قیمت معتبر نیست، دوباره بفرست (فقط عدد):")
        return PRICE
    context.user_data["target_price"] = price

    buttons = [
        [
            InlineKeyboardButton("✅ RSI فعال", callback_data="rsi_1"),
            InlineKeyboardButton("❌ بدون RSI", callback_data="rsi_0"),
        ]
    ]
    await update.message.reply_text("RSI هم چک بشه؟", reply_markup=InlineKeyboardMarkup(buttons))
    return RSI


async def got_rsi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["rsi_on"] = query.data == "rsi_1"

    d = context.user_data
    direction_fa = "بالای" if d["direction"] == "above" else "پایین"
    summary = (
        f"{d['symbol']} | {d['timeframe']} | {d['trigger_type']} {direction_fa} {d['target_price']} "
        f"| RSI: {'فعال' if d['rsi_on'] else 'خاموش'}"
    )
    buttons = [
        [
            InlineKeyboardButton("✅ تایید و ذخیره", callback_data="confirm_yes"),
            InlineKeyboardButton("❌ لغو", callback_data="confirm_no"),
        ]
    ]
    await query.edit_message_text(summary, reply_markup=InlineKeyboardMarkup(buttons))
    return CONFIRM


async def got_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "confirm_no":
        await query.edit_message_text("لغو شد.")
        context.user_data.clear()
        return ConversationHandler.END

    d = context.user_data
    supabase.table("alarms").insert(
        {
            "user_id": query.from_user.id,
            "symbol": d["symbol"],
            "timeframe": d["timeframe"],
            "trigger_type": d["trigger_type"],
            "direction": d["direction"],
            "target_price": d["target_price"],
            "rsi_on": d["rsi_on"],
            "active": True,
        }
    ).execute()

    await query.edit_message_text("آلارم ذخیره شد ✅")
    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("لغو شد.")
    return ConversationHandler.END


def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(menu_router, pattern="^new_alarm$")],
        states={
            SYMBOL: [MessageHandler(filters.TEXT & ~filters.COMMAND, got_symbol)],
            TIMEFRAME: [CallbackQueryHandler(got_timeframe, pattern="^tf_")],
            TRIGGER_TYPE: [CallbackQueryHandler(got_trigger_type, pattern="^trg_")],
            DIRECTION: [CallbackQueryHandler(got_direction, pattern="^dir_")],
            PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, got_price)],
            RSI: [CallbackQueryHandler(got_rsi, pattern="^rsi_")],
            CONFIRM: [CallbackQueryHandler(got_confirm, pattern="^confirm_")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv)
    # menu buttons that are NOT part of the "new alarm" conversation
    app.add_handler(CallbackQueryHandler(menu_router, pattern="^(list_alarms|delete_alarm|del_)"))

    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TELEGRAM_TOKEN,
        webhook_url=f"{RENDER_EXTERNAL_URL}/{TELEGRAM_TOKEN}",
    )


if __name__ == "__main__":
    main()
