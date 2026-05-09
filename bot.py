import os
import logging
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ContextTypes, ConversationHandler, filters
)
import wallet
import balance
import create
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
        await update.message.reply_text("❌ DM failed. Chat with bot privately first.")

async def create_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    address, _ = wallet.get_wallet(user_id, ENCRYPTION_SECRET)
    eth = balance.get_eth_balance(address)
    if eth < 0.0001:
        await update.message.reply_text(
            f"❌ Insufficient balance.\n\n"
            f"You have `{eth:.6f} ETH`.\n"
            f"Need a small amount of ETH for gas.\n\n"
            f"Deposit to:\n`{address}`",
            parse_mode="Markdown"
        )
        return ConversationHandler.END
    await update.message.reply_text(
        "🚀 *Create a new token*\n\n"
        "Step 1/2: What is your token name?\n"
        "_(e.g. Pepe Coin)_",
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
        f"✅ Name: *{name}*\n\n"
        f"Step 2/2: Token symbol?\n_(e.g. PEPE, max 10 chars)_",
        parse_mode="Markdown"
    )
    return SYMBOL

async def get_symbol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    symbol = update.message.text.strip().upper()
    if len(symbol) < 1 or len(symbol) > 10:
        await update.message.reply_text("❌ Symbol must be 1-10 chars. Try again:")
        return SYMBOL
    context.user_data['token_symbol'] = symbol
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
            await update.message.reply_text(
                f"⚠️ Deployed but no address returned.\nTX: `{tx_hash}`",
                parse_mode="Markdown"
            )
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
    app.add_handler(create_handler)

    print(f"Starting webhook on port {PORT}")
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=f"{WEBHOOK_URL}/webhook",
        url_path="webhook"
    )

if __name__ == "__main__":
    main()
