# Bot de administracion Mikrotik

Este proyecto implementa un bot de Telegram para la gestion remota de routers Mikrotik mediante acciones simplificadas. Utiliza la libreria `netmiko` para la comunicacion SSH y `python-telegram-bot` para la interfaz de chat.

## Funcionalidades

El bot permite realizar las siguientes operaciones desde un chat de Telegram autorizado:

*   **Monitorizacion**: Visualizacion de la carga de CPU y tiempo de actividad (uptime) del router.
*   **Gestion de Usuarios PPPoE**:
    *   Listado de usuarios activos.
    *   Listado de usuarios inactivos (configurados pero no conectados).
    *   Creacion de nuevos usuarios (secretos) con perfil predefinido.
    *   Suspension de servicio: Deshabilita el secreto y desconecta la sesion activa.
    *   Activacion de servicio: Habilita secretos previamente deshabilitados.
*   **Operaciones en Lote**: Capacidad para seleccionar multiples usuarios simultaneamente para suspender o activar sus servicios.

## Instalacion y Configuracion

1.  Asegurese de tener instalado Python 3.8 o superior y el gestor de dependencias `uv`.
2.  Sincronice el entorno de desarrollo:
    ```bash
    uv sync
    ```
3.  Cree un archivo llamado `.env` en el directorio raiz del proyecto con el siguiente contenido:

```env
TELEGRAM_TOKEN=su_token_de_telegram
USER_ID=su_id_de_usuario_telegram
ROUTER_IP=direccion_ip_del_router
ROUTER_USER=usuario_ssh
ROUTER_PASS=contrasena_ssh
```

El `USER_ID` sirve como medida de seguridad para asegurar que solo el usuario autorizado pueda interactuar con el bot.

## Ejecucion

Para iniciar el bot utilizando `uv`:

```bash
uv run python main.py
```

El bot iniciara la conexion con la API de Telegram y quedara a la espera de comandos. Use `/start` en el chat con el bot para desplegar el panel de control.
