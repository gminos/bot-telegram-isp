import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, filters, ConversationHandler, MessageHandler
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

ASK_NAME, ASK_PASSWORD = range(2)

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

def obtener_usuarios_activos(mikrotik_device: dict[str, str]) -> str:
    try:
        with ConnectHandler(**mikrotik_device) as conn:
            output = conn.send_command("/ppp active print terse without-paging")
            
            usuarios = re.findall(r'name=([^\s]+)', output)

            if not usuarios:
                return "No hay usuarios PPPoE activos actualmente."

            lista_nombres = "\n".join([f"- {u}" for u in usuarios])
            
            return (
                f"**Usuarios activos ({len(usuarios)})**\n\n"
                f"{lista_nombres}"
            )
    except Exception as e:
        return f"Error de conexion: {str(e)}"

def obtener_usuarios_inactivos(mikrotik_device: dict[str, str]) -> str:
    try:
        with ConnectHandler(**mikrotik_device) as conn:
            output_secrets = conn.send_command("/ppp secret print terse without-paging")
            secrets = set(re.findall(r'name=([^\s]+)', output_secrets))
            
            output_active = conn.send_command("/ppp active print terse without-paging")
            active = set(re.findall(r'name=([^\s]+)', output_active))
            
            inactivos = secrets - active
            
            if not inactivos:
                return "Todos los usuarios configurados estan activos."

            lista_inactivos = "\n".join([f"- {u}" for u in sorted(inactivos)])
            
            return (
                f"**Usuarios inactivos ({len(inactivos)})**\n\n"
                f"{lista_inactivos}"
            )
    except Exception as e:
        return f"Error de conexion: {str(e)}"

def crear_secreto_mikrotik(mikrotik_device: dict[str, str], name: str, password: str, service: str = 'pppoe', profile: str = 'profile_10_mbps') -> str:
    try:
        with ConnectHandler(**mikrotik_device) as conn:
            output_check = conn.send_command(f'/ppp secret print where name="{name}"')

            if name in output_check:
                return f"El usuario {name} ya existe."

            command = f'/ppp secret add name="{name}" password="{password}" service={service} profile={profile}'
            conn.send_command(command)
            
            output_verify = conn.send_command(f'/ppp secret print where name="{name}"')
            if name in output_verify:
                return f"Usuario '{name}' creado exitosamente."
            else:
                return f"No se pudo verificar la creacion de '{name}'."

    except Exception as e:
        return f"Error al crear usuario: {str(e)}"

async def start_create_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    _ = await query.answer()
    
    _ = await query.edit_message_text(text="Por favor, escribe el nombre del nuevo usuario:")
    
    return ASK_NAME

async def receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = update.message.text
    context.user_data['new_user_name'] = name
    
    _ = await update.message.reply_text(f"Genial. Ahora escribe la contrasena para {name}:")
    
    return ASK_PASSWORD

async def receive_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    password = update.message.text
    name = context.user_data.get('new_user_name')
    
    _ = await update.message.reply_text("Creando usuario en Mikrotik, por favor espera...")
    
    resultado = crear_secreto_mikrotik(mikrotik_config(), name, password)
    
    _ = await update.message.reply_text(resultado)
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    _ = await update.message.reply_text("Operacion cancelada.")
    return ConversationHandler.END

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
            InlineKeyboardButton("Ver Usuarios activos", callback_data="btn_activos")
        ],
        [
            InlineKeyboardButton("Ver Usuarios inactivos", callback_data="btn_inactivos")
        ],
        [
            InlineKeyboardButton("Agregar nuevo usuario", callback_data="btn_add_user")
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

    elif query.data == 'btn_activos':
        _ = await query.edit_message_text(text="Buscando usuarios activos...")
        resultado = obtener_usuarios_activos(mikrotik_config())
        _ = await query.edit_message_text(text=resultado, parse_mode="Markdown")

    elif query.data == 'btn_inactivos':
        _ = await query.edit_message_text(text="Buscando usuarios inactivos...")
        resultado = obtener_usuarios_inactivos(mikrotik_config())
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

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_create_user, pattern='^btn_add_user$')],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_name)],
            ASK_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_password)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('start', start, filters=filters.User(user_id=USER_ID)))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(CommandHandler("help", help_command, filters=filters.User(user_id=USER_ID)))

    application.run_polling()


if __name__ == "__main__":
    main()
