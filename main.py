import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, filters
from dotenv import load_dotenv
from netmiko import ConnectHandler
import os
import re

_ = load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
USER_ID = int(os.getenv('USER_ID', 0))

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def mikrotik_config() -> dict[str,str]:
    host = os.getenv('ROUTER_IP')
    user = os.getenv('ROUTER_USER')
    password = os.getenv('ROUTER_PASS')

    if not host or not user or not password:
        raise ValueError("Faltan variables")

    return {
        'device_type': 'mikrotik_routeros',
        'host': host,
        'username': user,
        'password': password,
    }

def obtener_bridge(mikrotik_device: dict[str,str]) -> str:
    try:
        with ConnectHandler(**mikrotik_device) as conn:
            output = conn.send_command("/interface bridge print without-paging")
            bridge = re.search(r'name="([^"]+)"', output)

            if bridge:
                return f"Puente encontrado: {bridge.group(1)}"
            else:
                return "No encontre ningun bridge"

    except Exception as e:
        return f"Error de conexion: {str(e)}"

def obtener_datos_router(mikrotik_device: dict[str,str]) -> str:
    try:
        with ConnectHandler(**mikrotik_device) as conn:
            output = conn.send_command("/system resource print without-paging")
            cpu = re.search(r'cpu-load:\s+(\d+)%', output)
            uptime = re.search(r'uptime:\s+(.+)', output)
            val_cpu = cpu.group(1) if cpu else "?"
            val_uptime = uptime.group(1).strip() if uptime else "?"

            return (
                f"**Estado del Mikrotik**\n\n"
                f"**CPU:** {val_cpu}%\n"
                f"**Uptime:** {val_uptime}"
            )

    except Exception as e:
        return f"Error de conexion: {str(e)}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.effective_chat:
        return

    usuario = update.effective_user.first_name

    keyboard = [
        [
            InlineKeyboardButton("Ver Estado CPU", callback_data='btn_estado'),
            InlineKeyboardButton("Ver Bridge", callback_data='btn_bridge')
        ],
        [
            InlineKeyboardButton("Cancelar / Cerrar", callback_data='btn_cerrar')
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    _ = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Hola {usuario}!\nSelecciona una opcion del panel de control:",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query

    if not query: return

    _ = await query.answer()

    if query.data == 'btn_estado':
        _ = await query.edit_message_text(text="Obteniendo estado del CPU...")
        resultado = obtener_datos_router(mikrotik_config())
        _ = await query.edit_message_text(text=resultado, parse_mode="Markdown")

    elif query.data == 'btn_bridge':
        _ = await query.edit_message_text(text="Buscando Bridge...")
        resultado = obtener_bridge(mikrotik_config())
        _ = await query.edit_message_text(text=resultado, parse_mode="Markdown")

    elif query.data == 'btn_cerrar':
        _ = await query.delete_message()

async def help_command(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return 

    _ = await update.message.reply_text("Usa /start para iniciar conversacion.")


def main() -> None:
    
    if not USER_ID or not TELEGRAM_TOKEN:
        return

    application = ApplicationBuilder().token(TELEGRAM_TOKEN).connect_timeout(30).read_timeout(30).build()

    application.add_handler(CommandHandler('start', start, filters=filters.User(user_id=USER_ID)))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(CommandHandler("help", help_command, filters=filters.User(user_id=USER_ID)))

    application.run_polling()


if __name__ == "__main__":
    main()
