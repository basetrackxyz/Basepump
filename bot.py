import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ContextTypes, ConversationHandler, filters
)
import wallet
import balance
import create
import config

BOT_TOKEN         = config.get_bot_token()
ENCRYPTION_SECRET = config.get_encryption_secret()

NAME, SYMBOL, DESCRIPTION = range(3)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id  = str(update.effective_user.id)
    username = update.effective_user.first_name or "anon"
    existing = wallet.get_wallet(user_id)
    if existing:
        address, _ = existing
        await update.message.reply_text(
            f"👋 Welcome back, {username}!\n\n"
            f"💼 Wallet: `{address}`\n\n"
            f"/balance — check ETH\n"
            f"/create — launch a token\n"
            f"/export — get private key",
            parse_mode="Markdown"
        )
    else:
        address, _ = wallet.create_wallet(user_id, ENCRYPTION_SECRET + user_id)
        await update.message.reply_text(
            f"🚀 Welcome to BasePump, {username}!\n\n"
            f"✅ Wallet created:\n`{address}`\n\n"
            f"⚠️ Custodial wallet. Use /export to self-custody.\n\n"
            f"Use /create to launch your first token.",
            parse_mode="Markdown"
        )

async def check_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    row = wallet.get_wallet(user_id)
    if not row:
        await update.message.reply_text("No wallet. Send /start first.")
        return
    address, _ = row
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
    row = wallet.get_wallet(user_id)
    if not row:
        await update.message.reply_text("No wallet. Send /start first.")
        return
    _, encrypted_key = row
    priv = wallet.decrypt_key(encrypted_key, ENCRYPTION_SECRET + user_id)
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
    row = wallet.get_wallet(user_id)
    if not row:
        await update.message.reply_text("No wallet. Send /start first.")
        return ConversationHandler.END
    address, _ = row
    eth = balance.get_eth_balance(address)
    if eth < 0.001:
        await update.message.reply_text(
            f"❌ Insufficient balance.\n\n"
            f"You have `{eth:.6f} ETH`.\n"
            f"Need at least `0.001 ETH`.\n\n"
            f"Deposit to:\n`{address}`",
            parse_mode="Markdown"
        )
        return ConversationHandler.END
    await update.message.reply_text(
        "🚀 *Create a new token*\n\n"
        "Step 1/3: What is your token name?\n"
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
        f"Step 2/3: Token symbol?\n_(e.g. PEPE, max 10 chars)_",
        parse_mode="Markdown"
    )
    return SYMBOL

async def get_symbol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    symbol = update.message.text.strip().upper()
    if len(symbol) < 1 or len(symbol) > 10:
        await update.message.reply_text("❌ Symbol must be 1-10 chars. Try again:")
        return SYMBOL
    context.user_data['token_symbol'] = symbol
    await update.message.reply_text(
        f"✅ Symbol: *{symbol}*\n\n"
        f"Step 3/3: Short description?\n_(max 200 chars)_",
        parse_mode="Markdown"
    )
    return DESCRIPTION

async def get_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    description = update.message.text.strip()
    if len(description) > 200:
        await update.message.reply_text("❌ Max 200 chars. Try again:")
        return DESCRIPTION
    name    = context.user_data['token_name']
    symbol  = context.user_data['token_symbol']
    user_id = str(update.effective_user.id)
    await update.message.reply_text(
        f"⏳ Deploying *{name}* (${symbol})...\n\nThis may take 30-60 seconds.",
        parse_mode="Markdown"
    )
    try:
        row = wallet.get_wallet(user_id)
        _, encrypted_key = row
        priv_key = wallet.decrypt_key(encrypted_key, ENCRYPTION_SECRET + user_id)
        token_address, tx_hash = create.deploy_token(priv_key, name, symbol, description)
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

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'BasePump is running')
    def log_message(self, format, *args):
        pass

def run_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), Handler)
    server.serve_forever()

def main():
    wallet.init_db()
    threading.Thread(target=run_server, daemon=True).start()
    print(f"HTTP server started")
    app = Application.builder().token(BOT_TOKEN).build()
    create_handler = ConversationHandler(
        entry_points=[CommandHandler("create", create_start)],
        states={
            NAME:        [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            SYMBOL:      [MessageHandler(filters.TEXT & ~filters.COMMAND, get_symbol)],
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_description)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("balance", check_balance))
    app.add_handler(CommandHandler("export", export))
    app.add_handler(create_handler)
    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
