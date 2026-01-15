import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
from dotenv import load_dotenv
import os

_ = load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
USER_ID = int(os.getenv('USER_ID', 0))

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.effective_chat:
        return

    usuario = update.effective_user.first_name
    await update.message.reply_text(f"Hola {usuario}!")

async def help_command(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return 
    await update.message.reply_text("Usa /start para iniciar conversacion.")

def main() -> None:
    if not USER_ID or not TELEGRAM_TOKEN:
        return

    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler("help", help_command))

    application.run_polling()

if __name__ == "__main__":
    main()
