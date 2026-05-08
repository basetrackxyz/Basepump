import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import wallet
import balance

BOT_TOKEN = "8110443376:AAGfKnEel8g_BZoxD22-AnSgkcfeWbp4QVo"
ENCRYPTION_SECRET = "GUGA GAGA"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    username = update.effective_user.first_name or "anon"
    existing = wallet.get_wallet(user_id)
    if existing:
        address, _ = existing
        await update.message.reply_text(
            f"👋 Welcome back, {username}!\n\n"
            f"💼 Your wallet:\n`{address}`\n\n"
            f"Use /balance to check ETH\n"
            f"Use /create to launch a token\n"
            f"Use /export to get your private key",
            parse_mode="Markdown"
        )
    else:
        address, priv = wallet.create_wallet(user_id, ENCRYPTION_SECRET + user_id)
        await update.message.reply_text(
            f"🚀 Welcome to BasePump, {username}!\n\n"
            f"✅ Wallet created:\n`{address}`\n\n"
            f"⚠️ This wallet is custodial. Use /export to take self-custody.\n\n"
            f"Use /create to launch your first token.",
            parse_mode="Markdown"
        )

async def check_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    row = wallet.get_wallet(user_id)
    if not row:
        await update.message.reply_text("No wallet found. Send /start first.")
        return
    address, _ = row
    await update.message.reply_text("⏳ Checking balance...")
    try:
        eth = balance.get_eth_balance(address)
        price = balance.get_eth_price_usd()
        usd_val = f"(≈ ${eth * price:,.2f} USD)" if price else ""
        await update.message.reply_text(
            f"💼 Wallet: `{address}`\n\n"
            f"💰 Balance: `{eth:.6f} ETH` {usd_val}\n\n"
            f"🌐 Network: Base Sepolia\n"
            f"🔗 [View on Explorer](https://sepolia.basescan.org/address/{address})",
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error fetching balance: {str(e)}")

async def export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    row = wallet.get_wallet(user_id)
    if not row:
        await update.message.reply_text("No wallet found. Send /start first.")
        return
    _, encrypted_key = row
    priv = wallet.decrypt_key(encrypted_key, ENCRYPTION_SECRET + user_id)
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=f"🔑 Your private key:\n\n`{priv}`\n\n"
                 f"⚠️ Never share this. Import into MetaMask or any EVM wallet.",
            parse_mode="Markdown"
        )
        if update.effective_chat.type != "private":
            await update.message.reply_text("✅ Private key sent to your DMs.")
    except Exception as e:
        await update.message.reply_text("❌ Could not DM you. Start a private chat with the bot first.")

def main():
    wallet.init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("balance", check_balance))
    app.add_handler(CommandHandler("export", export))
    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()


# Dummy HTTP server to satisfy Render port check
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'BasePump bot is running')
    def log_message(self, format, *args):
        pass

def run_server():
    server = HTTPServer(('0.0.0.0', 8080), Handler)
    server.serve_forever()

threading.Thread(target=run_server, daemon=True).start()
