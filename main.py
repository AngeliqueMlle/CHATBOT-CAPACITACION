"""Servidor FastAPI + SocketIO para el chatbot CECOM."""
import traceback
import socketio
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Crear servidor SocketIO asíncrono
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")

# Crear app FastAPI
app = FastAPI(title="CECOM Chatbot")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Combinar en una sola app ASGI
# IMPORTANTE: ejecutar con: uvicorn main:socket_app --reload --port 8000
socket_app = socketio.ASGIApp(sio, other_asgi_app=app)


@app.get("/")
async def index():
    """Sirve la interfaz web del chatbot."""
    return FileResponse("chat.html")


@app.get("/health")
async def health():
    """Verificación de que el servidor está activo."""
    return {"status": "ok"}


@sio.event
async def connect(sid, environ):
    """Envía el mensaje de bienvenida al conectarse."""
    await sio.emit(
        "response",
        "Bienvenido al asistente de capacitación de CECOM.\n"
        "Por favor ingresa tu DNI para continuar.",
        to=sid
    )
    await sio.emit("stage", "pedir_dni", to=sid)


@sio.event
async def message(sid, data):
    """Procesa el mensaje del usuario y emite los eventos de respuesta."""
    from chain import procesar_mensaje
    try:
        eventos = await procesar_mensaje(sid, str(data))
        for evento in eventos:
            await sio.emit(evento["tipo"], evento["contenido"], to=sid)
        from chain import sesiones
        if sid in sesiones:
            await sio.emit("stage", sesiones[sid]["etapa"], to=sid)
    except Exception as e:
        traceback.print_exc()
        await sio.emit(
            "response",
            "Ha ocurrido un error interno. Por favor recarga la página.",
            to=sid
        )


@sio.event
async def disconnect(sid):
    """Limpia la sesión al desconectarse el usuario."""
    from chain import limpiar_sesion
    limpiar_sesion(sid)
