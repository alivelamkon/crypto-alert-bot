import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from supabase import create_client, Client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------- Conversation states ----------
ASSET_SYMBOL, ASSET_AMOUNT = range(2)


def portfolio_menu_keyboard():
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("➕ افزودن دارایی", callback_data="add_asset")],
            [InlineKeyboardButton("📊 مشاهده پورتفولیو", callback_data="view_portfolio")],
            [InlineKeyboardButton("🗑 حذف دارایی", callback_data="delete_asset")],
        ]
    )


async def open_portfolio_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """وقتی کاربر دکمه‌ی پایین '💼 پورتفولیو' رو می‌زنه"""
    await update.message.reply_text("منوی پورتفولیو:", reply_markup=portfolio_menu_keyboard())


def get_price(symbol_pair):
    """symbol_pair مثل BTCUSDT"""
    url = "https://api.binance.com/api/v3/ticker/price"
    r = requests.get(url, params={"symbol": symbol_pair}, timeout=15)
    r.raise_for_status()
    return float(r.json()["price"])


async def menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "add_asset":
        await query.edit_message_text("نماد ارز رو بفرست (مثلاً BTC یا ETH):")
        return ASSET_SYMBOL

    if query.data == "view_portfolio":
        await show_portfolio(query, context)
        return ConversationHandler.END

    if query.data == "delete_asset":
        await show_delete_list(query, context)
        return ConversationHandler.END

    if query.data.startswith("delh_"):
        holding_id = int(query.data.split("_", 1)[1])
        supabase.table("holdings").delete().eq("id", holding_id).execute()
        await query.edit_message_text("دارایی حذف شد ✅")
        return ConversationHandler.END


async def show_portfolio(query, context):
    user_id = query.from_user.id
    res = supabase.table("holdings").select("*").eq("user_id", user_id).execute()
    rows = res.data
    if not rows:
        await query.edit_message_text("هنوز دارایی‌ای ثبت نکردی.")
        return

    lines = []
    total = 0.0
    for r in rows:
        symbol_pair = r["symbol"]  # مثل BTCUSDT
        base_symbol = symbol_pair.replace("USDT", "")
        amount = float(r["amount"])
        try:
            price = get_price(symbol_pair)
            value = amount * price
            total += value
            lines.append(f"• {base_symbol}: {amount} ≈ {value:,.2f}$")
        except Exception:
            lines.append(f"• {base_symbol}: {amount} (قیمت در دسترس نیست)")

    lines.append(f"\n💰 ارزش کل: {total:,.2f}$")
    await query.edit_message_text("\n".join(lines))


async def show_delete_list(query, context):
    user_id = query.from_user.id
    res = supabase.table("holdings").select("*").eq("user_id", user_id).execute()
    rows = res.data
    if not rows:
        await query.edit_message_text("چیزی برای حذف نیست.")
        return
    buttons = [
        [InlineKeyboardButton(f"{r['symbol'].replace('USDT', '')} - {r['amount']}", callback_data=f"delh_{r['id']}")]
        for r in rows
    ]
    await query.edit_message_text("کدوم رو حذف کنم؟", reply_markup=InlineKeyboardMarkup(buttons))


async def got_asset_symbol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    symbol = update.message.text.strip().upper()
    if not symbol.endswith("USDT"):
        symbol += "USDT"
    context.user_data["asset_symbol"] = symbol
    await update.message.reply_text("چه مقدار داری؟ (فقط عدد):")
    return ASSET_AMOUNT


async def got_asset_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text.strip().replace(",", ""))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("عدد معتبر نیست، دوباره بفرست:")
        return ASSET_AMOUNT

    symbol = context.user_data["asset_symbol"]
    supabase.table("holdings").insert(
        {
            "user_id": update.effective_user.id,
            "symbol": symbol,
            "amount": amount,
        }
    ).execute()

    await update.message.reply_text(f"دارایی ثبت شد ✅ ({symbol.replace('USDT', '')}: {amount})")
    context.user_data.pop("asset_symbol", None)
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("asset_symbol", None)
    await update.message.reply_text("لغو شد.")
    return ConversationHandler.END


def register_portfolio_handlers(app):
    """این تابع رو bot.py صدا می‌زنه تا هندلرهای پورتفولیو رو ثبت کنه"""
    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(menu_router, pattern="^add_asset$")],
        states={
            ASSET_SYMBOL: [MessageHandler(filters.TEXT & ~filters.COMMAND, got_asset_symbol)],
            ASSET_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, got_asset_amount)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(MessageHandler(filters.Regex("^💼 پورتفولیو$"), open_portfolio_menu))
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(menu_router, pattern="^(view_portfolio|delete_asset|delh_)"))
