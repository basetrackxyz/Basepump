import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, ConversationHandler, filters
)
import wallet
import balance
import create
import tokens
import buy as buymodule
import config

logging.basicConfig(level=logging.INFO)

BOT_TOKEN         = config.get_bot_token()
ENCRYPTION_SECRET = config.get_encryption_secret()
WEBHOOK_URL       = os.environ.get("WEBHOOK_URL", "https://basepump.onrender.com")
PORT              = int(os.environ.get("PORT", 8080))

NAME, SYMBOL = range(2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id  = str(update.effective_user.id)
    username = update.effective_user.first_name or "anon"
    address, _ = wallet.get_wallet(user_id, ENCRYPTION_SECRET)
    await update.message.reply_text(
        f"🚀 Welcome to BasePump, {username}!\n\n"
        f"💼 Your wallet:\n`{address}`\n\n"
        f"/balance — check ETH\n"
        f"/create — launch a token\n"
        f"/buy — buy a token\n"
        f"/sell — sell a token\n"
        f"/tokens — browse tokens\n"
        f"/export — get private key",
        parse_mode="Markdown"
    )

async def check_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    address, _ = wallet.get_wallet(user_id, ENCRYPTION_SECRET)
    await update.message.reply_text("⏳ Checking...")
    try:
        eth   = balance.get_eth_balance(address)
        price = balance.get_eth_price_usd()
        usd   = f"(≈ ${eth * price:,.2f} USD)" if price else ""
        await update.message.reply_text(
            f"💼 `{address}`\n\n"
            f"💰 `{eth:.6f} ETH` {usd}\n\n"
            f"🌐 Base Sepolia\n"
            f"🔗 [Explorer](https://sepolia.basescan.org/address/{address})",
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    priv = wallet.decrypt_key(user_id, ENCRYPTION_SECRET)
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=f"🔑 Private key:\n\n`{priv}`\n\n⚠️ Never share this.",
            parse_mode="Markdown"
        )
        if update.effective_chat.type != "private":
            await update.message.reply_text("✅ Sent to DMs.")
    except:
        await update.message.reply_text("❌ DM failed. Chat privately first.")

async def list_tokens(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Loading tokens...")
    try:
        token_list = tokens.get_all_tokens()
        if not token_list:
            await update.message.reply_text("No tokens yet. Be the first! /create")
            return
        msg = "🪙 *Tokens on BasePump:*\n\n"
        for i, t in enumerate(token_list[:10]):
            info = tokens.get_token_info(t['address'])
            msg += (
                f"{i+1}. *{info['name']}* (${info['symbol']})\n"
                f"   `{t['address']}`\n"
                f"   Supply: {info['total_supply']:,.2f} | ETH: {info['eth_collected']:.4f}\n\n"
            )
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def buy_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    address, _ = wallet.get_wallet(user_id, ENCRYPTION_SECRET)
    eth = balance.get_eth_balance(address)
    if eth < 0.0001:
        await update.message.reply_text(
            f"❌ Insufficient balance: `{eth:.6f} ETH`\n\nDeposit to:\n`{address}`",
            parse_mode="Markdown"
        )
        return

    try:
        token_list = tokens.get_all_tokens()
        if not token_list:
            await update.message.reply_text("No tokens available. /create one first!")
            return

        # Store in context for later use
        context.bot_data['token_list'] = token_list

        keyboard = []
        for i, t in enumerate(token_list[:8]):
            info = tokens.get_token_info(t['address'])
            keyboard.append([InlineKeyboardButton(
                f"{info['name']} (${info['symbol']})",
                callback_data=f"bt:{i}"
            )])

        await update.message.reply_text(
            "🛒 *Select a token to buy:*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def buy_token_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    idx = int(query.data.split(":")[1])
    token_list = context.bot_data.get('token_list', [])
    if not token_list or idx >= len(token_list):
        await query.edit_message_text("❌ Token not found. Try /buy again.")
        return

    token_address = token_list[idx]['address']
    context.user_data['buy_token'] = token_address
    info = tokens.get_token_info(token_address)

    keyboard = [[
        InlineKeyboardButton("0.001 ETH", callback_data=f"ba:0.001:{idx}"),
        InlineKeyboardButton("0.005 ETH", callback_data=f"ba:0.005:{idx}"),
        InlineKeyboardButton("0.01 ETH",  callback_data=f"ba:0.01:{idx}"),
    ]]

    await query.edit_message_text(
        f"🪙 *{info['name']}* (${info['symbol']})\n\nSelect amount:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def buy_amount_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, amount_eth, idx = query.data.split(":")
    idx = int(idx)
    token_list = context.bot_data.get('token_list', [])
    if not token_list or idx >= len(token_list):
        await query.edit_message_text("❌ Session expired. Try /buy again.")
        return

    token_address = token_list[idx]['address']
    amount_wei    = int(float(amount_eth) * 1e18)
    user_id       = str(query.from_user.id)
    info          = tokens.get_token_info(token_address)

    await query.edit_message_text(
        f"⏳ Buying {amount_eth} ETH of *{info['name']}*...",
        parse_mode="Markdown"
    )

    try:
        priv_key  = wallet.decrypt_key(user_id, ENCRYPTION_SECRET)
        tx_hash   = buymodule.buy_tokens(priv_key, token_address, amount_wei)
        address, _ = wallet.get_wallet(user_id, ENCRYPTION_SECRET)
        token_bal = tokens.get_token_balance(token_address, address)

        await query.edit_message_text(
            f"🎉 Bought *{info['name']}* (${info['symbol']})\n\n"
            f"💰 Spent: `{amount_eth} ETH`\n"
            f"🪙 Balance: `{token_bal/1e18:,.2f} {info['symbol']}`\n\n"
            f"📝 [TX](https://sepolia.basescan.org/tx/{tx_hash})",
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
    except Exception as e:
        await query.edit_message_text(f"❌ Buy failed: {str(e)}")

async def sell_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    address, _ = wallet.get_wallet(user_id, ENCRYPTION_SECRET)

    try:
        token_list = tokens.get_all_tokens()
        if not token_list:
            await update.message.reply_text("No tokens available.")
            return

        context.bot_data['token_list'] = token_list

        keyboard = []
        for i, t in enumerate(token_list[:8]):
            info = tokens.get_token_info(t['address'])
            bal  = tokens.get_token_balance(t['address'], address)
            if bal > 0:
                keyboard.append([InlineKeyboardButton(
                    f"{info['name']} ({bal/1e18:,.2f} {info['symbol']})",
                    callback_data=f"st:{i}:{bal}"
                )])

        if not keyboard:
            await update.message.reply_text("You don't own any tokens. /buy first!")
            return

        await update.message.reply_text(
            "💸 *Select a token to sell:*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def sell_token_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split(":")
    idx     = int(parts[1])
    bal_wei = int(parts[2])
    token_list = context.bot_data.get('token_list', [])
    if not token_list or idx >= len(token_list):
        await query.edit_message_text("❌ Session expired. Try /sell again.")
        return

    token_address = token_list[idx]['address']
    context.user_data['sell_token'] = token_address
    context.user_data['sell_bal']   = bal_wei
    info = tokens.get_token_info(token_address)

    keyboard = [[
        InlineKeyboardButton("25%",  callback_data=f"sa:25:{idx}:{bal_wei}"),
        InlineKeyboardButton("50%",  callback_data=f"sa:50:{idx}:{bal_wei}"),
        InlineKeyboardButton("100%", callback_data=f"sa:100:{idx}:{bal_wei}"),
    ]]

    await query.edit_message_text(
        f"💸 *{info['name']}* (${info['symbol']})\n\n"
        f"Balance: `{bal_wei/1e18:,.2f}`\n\nSelect % to sell:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def sell_amount_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts        = query.data.split(":")
    pct          = int(parts[1])
    idx          = int(parts[2])
    bal_wei      = int(parts[3])
    sell_wei     = int(bal_wei * pct / 100)
    user_id      = str(query.from_user.id)
    token_list   = context.bot_data.get('token_list', [])
    if not token_list or idx >= len(token_list):
        await query.edit_message_text("❌ Session expired. Try /sell again.")
        return

    token_address = token_list[idx]['address']
    info          = tokens.get_token_info(token_address)

    await query.edit_message_text(
        f"⏳ Selling {pct}% of *{info['name']}*...",
        parse_mode="Markdown"
    )

    try:
        priv_key = wallet.decrypt_key(user_id, ENCRYPTION_SECRET)
        tx_hash  = buymodule.sell_tokens(priv_key, token_address, sell_wei)
        await query.edit_message_text(
            f"✅ Sold {pct}% of *{info['name']}* (${info['symbol']})\n\n"
            f"📝 [TX](https://sepolia.basescan.org/tx/{tx_hash})",
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
    except Exception as e:
        await query.edit_message_text(f"❌ Sell failed: {str(e)}")

async def create_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    address, _ = wallet.get_wallet(user_id, ENCRYPTION_SECRET)
    eth = balance.get_eth_balance(address)
    if eth < 0.0001:
        await update.message.reply_text(
            f"❌ Insufficient balance.\n\nDeposit to:\n`{address}`",
            parse_mode="Markdown"
        )
        return ConversationHandler.END
    await update.message.reply_text(
        "🚀 *Create a new token*\n\nStep 1/2: Token name?\n_(e.g. Pepe Coin)_",
        parse_mode="Markdown"
    )
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    if len(name) < 1 or len(name) > 50:
        await update.message.reply_text("❌ Name must be 1-50 chars. Try again:")
        return NAME
    context.user_data['token_name'] = name
    await update.message.reply_text(
        f"✅ Name: *{name}*\n\nStep 2/2: Token symbol?\n_(e.g. PEPE, max 10 chars)_",
        parse_mode="Markdown"
    )
    return SYMBOL

async def get_symbol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    symbol  = update.message.text.strip().upper()
    if len(symbol) < 1 or len(symbol) > 10:
        await update.message.reply_text("❌ Symbol must be 1-10 chars. Try again:")
        return SYMBOL
    name    = context.user_data['token_name']
    user_id = str(update.effective_user.id)
    await update.message.reply_text(
        f"⏳ Deploying *{name}* (${symbol})...\n\nThis may take 30-60 seconds.",
        parse_mode="Markdown"
    )
    try:
        priv_key = wallet.decrypt_key(user_id, ENCRYPTION_SECRET)
        token_address, tx_hash = create.deploy_token(priv_key, name, symbol)
        if token_address:
            await update.message.reply_text(
                f"🎉 *{name}* (${symbol}) launched!\n\n"
                f"📍 Contract:\n`{token_address}`\n\n"
                f"🔗 [Explorer](https://sepolia.basescan.org/address/{token_address})\n"
                f"📝 [TX](https://sepolia.basescan.org/tx/{tx_hash})\n\n"
                f"Use /buy to trade!",
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
        else:
            await update.message.reply_text(f"⚠️ TX: `{tx_hash}`", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Deploy failed: {str(e)}")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Cancelled.")
    return ConversationHandler.END

def main():
    wallet.init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    create_handler = ConversationHandler(
        entry_points=[CommandHandler("create", create_start)],
        states={
            NAME:   [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            SYMBOL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_symbol)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("balance", check_balance))
    app.add_handler(CommandHandler("export", export))
    app.add_handler(CommandHandler("tokens", list_tokens))
    app.add_handler(CommandHandler("buy", buy_start))
    app.add_handler(CommandHandler("sell", sell_start))
    app.add_handler(create_handler)
    app.add_handler(CallbackQueryHandler(buy_token_selected,  pattern="^bt:"))
    app.add_handler(CallbackQueryHandler(buy_amount_selected, pattern="^ba:"))
    app.add_handler(CallbackQueryHandler(sell_token_selected, pattern="^st:"))
    app.add_handler(CallbackQueryHandler(sell_amount_selected,pattern="^sa:"))

    print(f"Starting webhook on port {PORT}")
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=f"{WEBHOOK_URL}/webhook",
        url_path="webhook"
    )

if __name__ == "__main__":
    main()
