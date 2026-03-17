"""Lógica conversacional y máquina de estados para el chatbot CECOM."""
import os
import re
import json
import unicodedata
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from dotenv import load_dotenv

from database import registrar_o_actualizar_usuario, registrar_actividad
from modules import MODULOS
from rag import buscar_contexto

load_dotenv()

# Cargar preguntas de quiz al iniciar (ruta absoluta relativa a este archivo)
_dir = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_dir, "quizzes.json"), "r", encoding="utf-8") as f:
    QUIZZES = json.load(f)

# Estado en memoria: clave = socket session id (sid)
sesiones = {}


# ── Detección de intención por palabras clave ─────────────────────

def _normalizar(texto: str) -> str:
    """Minúsculas, sin acentos, sin espacios extremos."""
    texto = texto.lower().strip()
    texto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


_MAPAS_INTENCION = {
    "menu_principal": {
        "1": "1",
        "capacitar": "1",
        "capacitarme": "1",
        "capacitacion": "1",
        "aprender": "1",
        "modulo": "1",
        "2": "2",
        "duda": "2",
        "pregunta": "2",
        "consulta": "2",
        "ayuda": "2",
    },
    "seleccionar_categoria": {
        "plataforma": "plataformas",
        "plataformas": "plataformas",
        "sistema": "plataformas",
        "software": "plataformas",
        "dispositivo": "dispositivos",
        "dispositivos": "dispositivos",
        "radio": "dispositivos",
        "bodycam": "dispositivos",
        "equipo": "dispositivos",
    },
    "ofrecer_quiz": {
        "si": "quiz_si",
        "quiz": "quiz_si",
        "hacer": "quiz_si",
        "quiero": "quiz_si",
        "no": "quiz_no",
        "omitir": "quiz_no",
        "saltar": "quiz_no",
        "paso": "quiz_no",
    },
    "continuar_o_salir": {
        "volver": "volver_menu",
        "menu": "volver_menu",
        "inicio": "volver_menu",
        "principal": "volver_menu",
        "ver": "ver_otro",
        "otro": "ver_otro",
        "salir": "salir",
        "chau": "salir",
        "adios": "salir",
    },
}


def _resolver_intencion(texto: str, mapa: dict) -> str | None:
    """
    Busca si alguna clave del mapa aparece como palabra completa en el texto.
    Normaliza texto y claves antes de comparar.
    El orden de las claves es significativo: la primera clave que coincide gana.
    """
    t = _normalizar(texto)
    for clave, valor in mapa.items():
        patron = r"\b" + re.escape(_normalizar(clave)) + r"\b"
        if re.search(patron, t):
            return valor
    return None


def _resolver_modulo(texto: str, modulos: list) -> dict:
    """
    Busca módulos que coincidan con el texto del usuario.

    Rutas:
    - A (input corto, ≤3 chars normalizados): coincidencia exacta con nombre normalizado.
    - B (al menos una palabra ≥4 chars): matching por word boundary en nombre normalizado.
    - C (ninguna condición cumplida): retorna ninguno.

    Retorna:
    - {"tipo": "unico", "modulo": {...}}
    - {"tipo": "ambiguo", "modulos": [...]}
    - {"tipo": "ninguno"}
    """
    t = _normalizar(texto)

    # Ruta A: input corto
    if len(t) <= 3:
        coincidentes = [m for m in modulos if _normalizar(m["nombre"]) == t]
        if len(coincidentes) == 1:
            return {"tipo": "unico", "modulo": coincidentes[0]}
        return {"tipo": "ninguno"}

    # Ruta B: palabras ≥4 chars
    palabras = [p for p in t.split() if len(p) >= 4]
    if not palabras:
        return {"tipo": "ninguno"}  # Ruta C

    coincidentes = []
    for modulo in modulos:
        nombre_norm = _normalizar(modulo["nombre"])
        if any(re.search(r"\b" + re.escape(p) + r"\b", nombre_norm) for p in palabras):
            coincidentes.append(modulo)

    if len(coincidentes) == 1:
        return {"tipo": "unico", "modulo": coincidentes[0]}
    if len(coincidentes) > 1:
        return {"tipo": "ambiguo", "modulos": coincidentes}
    return {"tipo": "ninguno"}

SYSTEM_PROMPT = (
    "Eres CECOM-bot, el asistente virtual de capacitación de CECOM (Centro de Comunicaciones Municipal). "
    "Si alguien te pregunta cómo te llamas o quién eres, responde que eres CECOM-bot. "
    "Tu rol es orientar al personal municipal sobre las herramientas tecnológicas institucionales "
    "y guiarlos hacia el módulo correcto para aprender en detalle.\n\n"

    "CÓMO RESPONDER:\n"
    "- Responde siempre en español, tono amigable, cercano y profesional.\n"
    "- Máximo 3 oraciones. Directo y claro.\n"
    "- Para preguntas generales sobre qué es CECOM, qué herramientas existen o para qué sirve "
    "cada área, responde con lo que sabes.\n"
    "- Si la pregunta es sobre el uso detallado o pasos específicos de una herramienta, "
    "redirige al módulo correspondiente con este mensaje: "
    "'Para aprender a usar [herramienta] en detalle, ve al módulo correspondiente "
    "en la sección Capacitarme. Ahí encontrarás el material completo y podrás "
    "hacer preguntas específicas sobre esa herramienta.'\n\n"

    "LO QUE NUNCA DEBES HACER:\n"
    "- No inventes pasos, funcionalidades ni procedimientos de ninguna herramienta.\n"
    "- No derives al área de sistemas. Tu rol es orientar, no escalar.\n"
    "- No respondas temas ajenos a CECOM.\n\n"

    "HERRAMIENTAS QUE CONOCES:\n"
    "Plataformas: App de Incidencias, Sistema de Validación, Sistema de Cazadores, "
    "Mapa CECOM (611 cámaras municipales), Gestionate, Centinela, "
    "Hikvision WebClient, HikCentral Professional, IVMS-4200, SmartPSS, PUC, Geosatelital.\n"
    "Dispositivos: Radio Dolphin, Bodycam.\n\n"

    "CATEGORÍAS DE PREGUNTAS Y CÓMO MANEJARLAS:\n"
    "- '¿Qué es el Mapa CECOM?' → responde brevemente y sugiere ir al módulo para más detalle.\n"
    "- '¿Cómo filtro cámaras LPR?' → redirige directamente al módulo Mapa CECOM.\n"
    "- '¿Para qué sirve la bodycam?' → responde brevemente y sugiere el módulo Bodycam.\n"
    "- '¿Qué herramientas debo aprender?' → Responde: 'Depende de tu área y las herramientas que uses en tu trabajo. Te recomiendo ir a Capacitarme, explorar las categorías y empezar por lo que más necesitas en tu día a día.\n"
    "- '¿Qué es CECOM?' → explica brevemente que es el Centro de Comunicaciones en San Juan de Lurigancho.\n"
)


def obtener_sesion(sid: str) -> dict:
    """Retorna la sesión existente o crea una nueva para el sid dado."""
    if sid not in sesiones:
        sesiones[sid] = {
            "dni": None,
            "etapa": "pedir_dni",
            "modulo_actual": None,
            "categoria_actual": None,
            "quiz_pregunta_actual": 0,
            "quiz_puntaje": 0,
            "historial_chat": []
        }
    return sesiones[sid]


def limpiar_sesion(sid: str) -> None:
    """Elimina la sesión al desconectarse el usuario."""
    sesiones.pop(sid, None)


def _btn(label: str, value: str) -> dict:
    return {"label": label, "value": value}


def _eventos_duda_libre() -> list:
    return [
        {"tipo": "response", "contenido": "Escribe tu pregunta y te ayudo a resolverla."},
        {"tipo": "buttons", "contenido": [
            _btn("¿Para qué sirve la bodycam?", "¿Para qué sirve la bodycam?"),
            _btn("¿Cuántas cámaras municipales hay?", "¿Cuántas cámaras municipales hay?"),
            _btn("¿Qué herramientas debo aprender primero?", "¿Qué herramientas debo aprender primero?"),
        ]}
    ]


def _eventos_menu_principal() -> list:
    return [
        {"tipo": "response", "contenido": "¿Qué deseas hacer hoy?"},
        {"tipo": "buttons", "contenido": [
            _btn("📚 Capacitarme", "1"),
            _btn("❓ Tengo una duda", "2")
        ]}
    ]


_BOTONES_DUDA = [
    _btn("✋ Sí, tengo una duda", "con_duda_modulo"),
    _btn("▶️ No, continuar", "sin_duda_modulo"),
]


def _eventos_duda_modulo(nombre_modulo: str) -> list:
    return [
        {"tipo": "response", "contenido": f"¿Tienes alguna duda sobre {nombre_modulo}?"},
        {"tipo": "buttons", "contenido": _BOTONES_DUDA}
    ]


def _eventos_otra_duda_modulo(nombre_modulo: str) -> list:
    return [
        {"tipo": "response", "contenido": f"¿Tienes otra duda sobre {nombre_modulo}?"},
        {"tipo": "buttons", "contenido": _BOTONES_DUDA}
    ]


def _eventos_continuar() -> list:
    return [
        {"tipo": "response", "contenido": "¿Qué deseas hacer ahora?"},
        {"tipo": "buttons", "contenido": [
            _btn("📖 Ver otro módulo", "ver_otro"),
            _btn("🏠 Volver al menú", "volver_menu"),
            _btn("👋 Salir", "salir")
        ]}
    ]


def _eventos_pregunta(pregunta: dict, numero: int) -> list:
    botones = [_btn(op, str(i)) for i, op in enumerate(pregunta["opciones"])]
    return [
        {"tipo": "response", "contenido": f"Pregunta {numero}: {pregunta['pregunta']}"},
        {"tipo": "buttons", "contenido": botones}
    ]


async def generar_bienvenida_nuevo_usuario(dni: str) -> str:
    """Genera bienvenida personalizada para nuevo usuario usando IA."""
    prompt = (
        "Eres CECOM-Bot, asistente virtual de capacitación del Centro de Monitoreo "
        "y Videovigilancia (CECOM) de la Municipalidad Distrital de San Juan de "
        "Lurigancho. Apoyas al personal operativo y administrativo — operadores de "
        "monitoreo, serenazgo, transporte, fiscalización y administrativos — a "
        "aprender a usar las herramientas tecnológicas institucionales.\n\n"
        f"Un nuevo agente del personal municipal de CECOM acaba de registrarse "
        f"con DNI terminado en {dni[-4:]}. "
        "Genera un mensaje de bienvenida cálido, profesional y motivador de 2 oraciones cortas"
        "para invitarlo a empezar su capacitación"
    )
    return await obtener_respuesta_ia([], prompt)


async def obtener_respuesta_ia(historial: list, mensaje: str) -> str:
    """
    Llama a la IA. Intenta Groq primero, fallback automático a Mistral.

    Args:
        historial: lista de dicts {role, content} de mensajes anteriores.
        mensaje: mensaje actual del usuario.

    Returns:
        Respuesta de texto de la IA.
    """
    mensajes = [SystemMessage(content=SYSTEM_PROMPT)]
    for entrada in historial:
        if entrada["role"] == "user":
            mensajes.append(HumanMessage(content=entrada["content"]))
        else:
            mensajes.append(AIMessage(content=entrada["content"]))
    mensajes.append(HumanMessage(content=mensaje))

    try:
        from langchain_groq import ChatGroq
        llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=os.getenv("GROQ_API_KEY")
        )
        respuesta = await llm.ainvoke(mensajes)
        return respuesta.content
    except Exception:
        pass

    try:
        from langchain_mistralai import ChatMistralAI
        llm = ChatMistralAI(
            model="mistral-small-latest",
            api_key=os.getenv("MISTRAL_API_KEY")
        )
        respuesta = await llm.ainvoke(mensajes)
        return respuesta.content
    except Exception:
        return (
            "Lo siento, el servicio de IA no está disponible en este momento. "
            "Por favor intenta más tarde."
        )


_RESPUESTA_SIN_INFO = (
    "Esa información no está disponible aún en este módulo. "
    "Consulta el PDF o video para más detalle."
)

# Memoria conversacional por sesión+módulo. Clave: f'{sid}:{nombre_modulo}'
historial_sesiones: dict[str, list] = {}


def limpiar_historial_modulo(session_id: str, nombre_modulo: str) -> None:
    """Elimina el historial conversacional de un módulo para una sesión."""
    historial_sesiones.pop(f"{session_id}:{nombre_modulo}", None)


async def obtener_respuesta_modulo(
    pregunta: str, session_id: str, nombre_modulo: str
) -> str:
    """Responde una pregunta buscando contexto en pgvector, con memoria conversacional."""
    clave = f"{session_id}:{nombre_modulo}"
    historial = historial_sesiones.get(clave, [])

    # buscar_contexto is imported at module level (from rag import buscar_contexto)
    contexto = buscar_contexto(pregunta, nombre_modulo)

    if not contexto:
        historial.append(HumanMessage(content=pregunta))
        historial.append(AIMessage(content=_RESPUESTA_SIN_INFO))
        if len(historial) > 20:
            historial = historial[-20:]
        historial_sesiones[clave] = historial
        return _RESPUESTA_SIN_INFO

    system = (
        "Eres CECOM-Bot, asistente virtual de capacitación del Centro de Monitoreo "
        "y Videovigilancia (CECOM) de la Municipalidad Distrital de San Juan de "
        "Lurigancho. Apoyas al personal operativo y administrativo a "
        "aprender a usar las herramientas tecnológicas institucionales.\n\n"
        f"CONTENIDO DEL MÓDULO:\n{contexto}\n\n"
        "REGLA DE RESPUESTA — aplica en este orden estricto:\n"
        "0. SOLO redirige si la pregunta es explícitamente sobre tu nombre, "
        "identidad, o un tema completamente ajeno a CECOM como deportes, "
        "cocina, geografía. Para CUALQUIER otra pregunta, incluyendo las "
        "ambiguas como 'cómo empiezo', 'por dónde comienzo', 'qué hago', "
        "busca la respuesta en el contenido del módulo y responde con esa "
        "información directamente.\n"
        "1. Si la respuesta está en el contenido del módulo: responde con esa "
        "información. Es tu fuente principal y siempre tiene prioridad.\n"
        "2. Si la pregunta es sobre conceptos generales de la tecnología del módulo "
        "(qué es, para qué sirve, cómo funciona en términos generales): puedes "
        "complementar brevemente con conocimiento general.\n"
        "3. Para cualquier otro caso — procedimientos específicos, errores, soporte "
        "técnico, configuración — que no esté en el contenido del módulo: responde "
        f"exactamente esto y nada más: '{_RESPUESTA_SIN_INFO}'\n\n"
        "FORMATO:\n"
        "- Procedimientos o pasos: númeralos. Máximo 7 pasos.\n"
        "- Múltiples opciones o elementos: usa guiones.\n"
        "- Explicaciones: máximo 3 oraciones.\n"
        "- NUNCA uses negritas, markdown ni texto en corrido para procedimientos.\n"
        "- NUNCA inventes pasos, funcionalidades ni procedimientos que no estén "
        "en el contenido del módulo.\n\n"
        "TONO: amigable, directo y profesional. Responde siempre en español."
    )
    mensajes = [SystemMessage(content=system), *historial, HumanMessage(content=pregunta)]

    respuesta_texto = None
    try:
        from langchain_groq import ChatGroq
        llm = ChatGroq(model="llama-3.3-70b-versatile", api_key=os.getenv("GROQ_API_KEY"))
        respuesta = await llm.ainvoke(mensajes)
        respuesta_texto = respuesta.content
    except Exception:
        pass

    if respuesta_texto is None:
        try:
            from langchain_mistralai import ChatMistralAI
            llm = ChatMistralAI(model="mistral-small-latest", api_key=os.getenv("MISTRAL_API_KEY"))
            respuesta = await llm.ainvoke(mensajes)
            respuesta_texto = respuesta.content
        except Exception:
            respuesta_texto = _RESPUESTA_SIN_INFO

    historial.append(HumanMessage(content=pregunta))
    historial.append(AIMessage(content=respuesta_texto))
    if len(historial) > 20:
        historial = historial[-20:]
    historial_sesiones[clave] = historial

    return respuesta_texto


async def procesar_mensaje(sid: str, texto: str) -> list:
    """
    Procesa el mensaje del usuario según la etapa actual de la sesión.

    Args:
        sid: ID de sesión del socket.
        texto: Mensaje o valor enviado por el usuario.

    Returns:
        Lista de eventos [{tipo, contenido}] para emitir al cliente.
    """
    sesion = obtener_sesion(sid)
    etapa = sesion["etapa"]
    texto = texto.strip()

    # ── Navegación global: botón Inicio ──────────────────────────
    if texto == "volver_menu" and etapa != "pedir_dni":
        sesion["etapa"] = "menu_principal"
        return _eventos_menu_principal()

    # ── ETAPA 1: Pedir y validar DNI ──────────────────────────────
    if etapa == "pedir_dni":
        if not texto.isdigit() or len(texto) != 8:
            return [{"tipo": "response", "contenido":
                     "⚠️ Por favor ingresa un DNI válido (8 dígitos numéricos)."}]
        try:
            resultado = registrar_o_actualizar_usuario(texto)
        except RuntimeError as e:
            print(f"[DB ERROR] {e}", flush=True)
            return [{"tipo": "response", "contenido":
                     "⚠️ No se pudo conectar a la base de datos. Por favor intenta más tarde."}]

        sesion["dni"] = texto
        sesion["etapa"] = "menu_principal"
        eventos = []

        if resultado["es_nuevo"]:
            bienvenida = await generar_bienvenida_nuevo_usuario(texto)
            eventos.append({"tipo": "response", "contenido": bienvenida})
        else:
            fecha = resultado["ultimo_acceso"].strftime("%d/%m/%Y a las %H:%M")
            eventos.append({"tipo": "response", "contenido":
                            f"¡Bienvenido de nuevo! La última vez que ingresaste fue el {fecha}."})

        eventos.extend(_eventos_menu_principal())
        return eventos

    # ── ETAPA 2: Menú principal ───────────────────────────────────
    elif etapa == "menu_principal":
        if texto == "1":
            sesion["etapa"] = "seleccionar_categoria"
            return [
                {"tipo": "response", "contenido": "¿Qué categoría te interesa?"},
                {"tipo": "buttons", "contenido": [
                    _btn("🖥️ Plataformas", "plataformas"),
                    _btn("📡 Dispositivos", "dispositivos")
                ]}
            ]
        elif texto == "2":
            sesion["etapa"] = "duda_libre"
            return _eventos_duda_libre()
        resuelto = _resolver_intencion(texto, _MAPAS_INTENCION["menu_principal"])
        if resuelto == "1":
            sesion["etapa"] = "seleccionar_categoria"
            return [
                {"tipo": "response", "contenido": "¿Qué categoría te interesa?"},
                {"tipo": "buttons", "contenido": [
                    _btn("🖥️ Plataformas", "plataformas"),
                    _btn("📡 Dispositivos", "dispositivos")
                ]}
            ]
        elif resuelto == "2":
            sesion["etapa"] = "duda_libre"
            return _eventos_duda_libre()
        return [
            {"tipo": "response", "contenido":
             "⚠️ No entendí tu selección. Por favor elige una de las opciones disponibles."},
            *_eventos_menu_principal()
        ]

    # ── ETAPA 3: Seleccionar categoría ───────────────────────────
    elif etapa == "seleccionar_categoria":
        resuelto = _resolver_intencion(texto, _MAPAS_INTENCION["seleccionar_categoria"])
        if resuelto is not None:
            texto = resuelto
        if texto not in MODULOS:
            return [
                {"tipo": "response", "contenido": "Por favor elige una categoría."},
                {"tipo": "buttons", "contenido": [
                    _btn("🖥️ Plataformas", "plataformas"),
                    _btn("📡 Dispositivos", "dispositivos")
                ]}
            ]
        sesion["categoria_actual"] = texto
        sesion["etapa"] = "seleccionar_modulo"
        nombre_cat = "Plataformas" if texto == "plataformas" else "Dispositivos"
        botones = [_btn(m["nombre"], m["nombre"]) for m in MODULOS[texto]]
        return [
            {"tipo": "response", "contenido": f"Módulos de {nombre_cat}:"},
            {"tipo": "buttons", "contenido": botones}
        ]

    # ── ETAPA 4: Seleccionar módulo ───────────────────────────────
    elif etapa == "seleccionar_modulo":
        categoria = sesion["categoria_actual"]
        # Primero: coincidencia exacta por nombre (botón)
        modulo = next((m for m in MODULOS[categoria] if m["nombre"] == texto), None)
        if modulo is None:
            # Segundo: matching por palabras clave
            resultado = _resolver_modulo(texto, MODULOS[categoria])
            if resultado["tipo"] == "unico":
                modulo = resultado["modulo"]
            elif resultado["tipo"] == "ambiguo":
                botones = [_btn(m["nombre"], m["nombre"]) for m in resultado["modulos"]]
                return [
                    {"tipo": "response",
                     "contenido": "Encontré varios módulos que podrían coincidir. ¿Cuál quisiste decir?"},
                    {"tipo": "buttons", "contenido": botones}
                ]
            else:
                botones = [_btn(m["nombre"], m["nombre"]) for m in MODULOS[categoria]]
                return [
                    {"tipo": "response", "contenido": "Por favor elige un módulo de la lista."},
                    {"tipo": "buttons", "contenido": botones}
                ]
        sesion["modulo_actual"] = modulo
        sesion["etapa"] = "duda_modulo"
        return [
            {"tipo": "card", "contenido": modulo},
            *_eventos_duda_modulo(modulo["nombre"])
        ]

    # ── ETAPA 5: Ofrecer quiz ─────────────────────────────────────
    elif etapa == "ofrecer_quiz":
        modulo = sesion["modulo_actual"]
        if texto == "quiz_si":
            preguntas = QUIZZES.get(modulo["nombre"], {}).get("preguntas", [])
            if not preguntas:
                registrar_actividad(sesion["dni"], modulo["nombre"],
                                    sesion["categoria_actual"], False, None)
                sesion["etapa"] = "continuar_o_salir"
                return [
                    {"tipo": "response", "contenido": "No hay preguntas disponibles para este módulo aún."},
                    *_eventos_continuar()
                ]
            sesion["quiz_pregunta_actual"] = 0
            sesion["quiz_puntaje"] = 0
            sesion["etapa"] = "quiz_en_curso"
            return _eventos_pregunta(preguntas[0], 1)

        elif texto == "quiz_no":
            registrar_actividad(sesion["dni"], modulo["nombre"],
                                sesion["categoria_actual"], False, None)
            sesion["etapa"] = "continuar_o_salir"
            return _eventos_continuar()

        resuelto = _resolver_intencion(texto, _MAPAS_INTENCION["ofrecer_quiz"])
        if resuelto is not None:
            texto = resuelto
            if texto == "quiz_si":
                preguntas = QUIZZES.get(modulo["nombre"], {}).get("preguntas", [])
                if not preguntas:
                    registrar_actividad(sesion["dni"], modulo["nombre"],
                                        sesion["categoria_actual"], False, None)
                    sesion["etapa"] = "continuar_o_salir"
                    return [
                        {"tipo": "response", "contenido": "No hay preguntas disponibles para este módulo aún."},
                        *_eventos_continuar()
                    ]
                sesion["quiz_pregunta_actual"] = 0
                sesion["quiz_puntaje"] = 0
                sesion["etapa"] = "quiz_en_curso"
                return _eventos_pregunta(preguntas[0], 1)
            elif texto == "quiz_no":
                registrar_actividad(sesion["dni"], modulo["nombre"],
                                    sesion["categoria_actual"], False, None)
                sesion["etapa"] = "continuar_o_salir"
                return _eventos_continuar()

        return [
            {"tipo": "response", "contenido": "Por favor elige una de las opciones."},
            {"tipo": "buttons", "contenido": [
                _btn("✅ Sí, hacer quiz", "quiz_si"),
                _btn("⏭️ Omitir", "quiz_no")
            ]}
        ]

    # ── ETAPA 6: Quiz en curso ────────────────────────────────────
    elif etapa == "quiz_en_curso":
        modulo = sesion["modulo_actual"]
        preguntas = QUIZZES[modulo["nombre"]]["preguntas"]
        idx = sesion["quiz_pregunta_actual"]
        pregunta = preguntas[idx]

        try:
            respuesta = int(texto)
            if respuesta < 0 or respuesta >= len(pregunta["opciones"]):
                raise ValueError
        except (ValueError, TypeError):
            return [
                {"tipo": "response", "contenido": "Por favor selecciona una de las opciones."},
                *_eventos_pregunta(pregunta, idx + 1)
            ]

        eventos = []
        if respuesta == pregunta["correcta"]:
            sesion["quiz_puntaje"] += 1
            eventos.append({"tipo": "response", "contenido": "✓ ¡Correcto!"})
        else:
            eventos.append({"tipo": "response",
                            "contenido": f"✗ Incorrecto — {pregunta['explicacion']}"})

        siguiente_idx = idx + 1
        if siguiente_idx < len(preguntas):
            sesion["quiz_pregunta_actual"] = siguiente_idx
            eventos.extend(_eventos_pregunta(preguntas[siguiente_idx], siguiente_idx + 1))
        else:
            puntaje = sesion["quiz_puntaje"]
            total = len(preguntas)
            registrar_actividad(sesion["dni"], modulo["nombre"],
                                sesion["categoria_actual"], True, puntaje)
            sesion["etapa"] = "continuar_o_salir"
            eventos.append({"tipo": "response", "contenido": f"🎯 Obtuviste {puntaje}/{total}"})
            eventos.extend(_eventos_continuar())

        return eventos

    # ── ETAPA 7: Duda libre ───────────────────────────────────────
    elif etapa == "duda_libre":
        nav_resuelto = _resolver_intencion(texto, {
            "menu": "volver_menu",
            "volver": "volver_menu",
            "regresar": "volver_menu",
            "inicio": "volver_menu",
            "salir": "salir",
        })
        if nav_resuelto == "volver_menu":
            sesion["etapa"] = "menu_principal"
            return _eventos_menu_principal()
        if nav_resuelto == "salir":
            sesion["etapa"] = "pedir_dni"
            sesion["dni"] = None
            return [{"tipo": "response", "contenido":
                     "¡Hasta pronto! Vuelve cuando quieras seguir capacitándote. 👋"}]
        respuesta = await obtener_respuesta_ia(sesion["historial_chat"], texto)
        sesion["historial_chat"].append({"role": "user", "content": texto})
        sesion["historial_chat"].append({"role": "assistant", "content": respuesta})
        sesion["etapa"] = "menu_principal"
        return [
            {"tipo": "response", "contenido": respuesta},
            *_eventos_menu_principal()
        ]

    # ── ETAPA 8: Preguntar si tiene dudas sobre el módulo ────────
    elif etapa == "duda_modulo":
        modulo = sesion["modulo_actual"]
        if texto == "con_duda_modulo":
            sesion["etapa"] = "escribir_duda_modulo"
            return [{"tipo": "response",
                     "contenido": f"Escribe tu pregunta para ayudarte:"}]
        if texto == "sin_duda_modulo":
            limpiar_historial_modulo(sid, modulo["nombre"])
            sesion["etapa"] = "ofrecer_quiz"
            return [
                {"tipo": "response",
                 "contenido": "¡Muy bien! ¿Quieres poner a prueba lo que aprendiste con un quiz rápido de 2 preguntas?"},
                {"tipo": "buttons", "contenido": [
                    _btn("✅ Sí, hacer quiz", "quiz_si"),
                    _btn("⏭️ Omitir", "quiz_no")
                ]}
            ]
        nav_resuelto = _resolver_intencion(texto, {
            "menu": "volver_menu",
            "volver": "volver_menu",
            "regresar": "volver_menu",
            "inicio": "volver_menu",
            "salir": "salir",
            "continuar": "sin_duda_modulo",
            "siguiente": "sin_duda_modulo",
            "duda": "con_duda_modulo",
        })
        if nav_resuelto == "volver_menu":
            sesion["etapa"] = "menu_principal"
            return _eventos_menu_principal()
        if nav_resuelto == "salir":
            sesion["etapa"] = "pedir_dni"
            sesion["dni"] = None
            return [{"tipo": "response", "contenido":
                     "¡Hasta pronto! Vuelve cuando quieras seguir capacitándote. 👋"}]
        if nav_resuelto == "con_duda_modulo":
            sesion["etapa"] = "escribir_duda_modulo"
            return [{"tipo": "response",
                     "contenido": f"Escribí tu pregunta sobre {modulo['nombre']}:"}]
        if nav_resuelto == "sin_duda_modulo":
            limpiar_historial_modulo(sid, modulo["nombre"])
            sesion["etapa"] = "ofrecer_quiz"
            return [
                {"tipo": "response",
                 "contenido": "¡Muy bien! ¿Quieres poner a prueba lo que aprendiste con un quiz rápido de 2 preguntas?"},
                {"tipo": "buttons", "contenido": [
                    _btn("✅ Sí, hacer quiz", "quiz_si"),
                    _btn("⏭️ Omitir", "quiz_no")
                ]}
            ]
        return _eventos_duda_modulo(modulo["nombre"])

    # ── ETAPA 8b: Recibir la pregunta del módulo ──────────────────
    elif etapa == "escribir_duda_modulo":
        modulo = sesion["modulo_actual"]
        nav_resuelto = _resolver_intencion(texto, {
            "menu": "volver_menu",
            "volver": "volver_menu",
            "regresar": "volver_menu",
            "inicio": "volver_menu",
            "salir": "salir",
        })
        if nav_resuelto == "volver_menu":
            sesion["etapa"] = "menu_principal"
            return _eventos_menu_principal()
        if nav_resuelto == "salir":
            sesion["etapa"] = "pedir_dni"
            sesion["dni"] = None
            return [{"tipo": "response", "contenido":
                     "¡Hasta pronto! Vuelve cuando quieras seguir capacitándote. 👋"}]

        # Material del módulo → re-mostrar la tarjeta (REGLA 1: vuelve a duda_modulo)
        if _resolver_intencion(texto, {
            "pdf": "material", "video": "material", "ver": "material",
            "material": "material", "mostrar": "material",
        }):
            sesion["etapa"] = "duda_modulo"
            return [
                {"tipo": "card", "contenido": modulo},
                *_eventos_otra_duda_modulo(modulo["nombre"])
            ]

        # Toda pregunta (válida o fuera de tema) → responder con contexto del módulo (REGLA 1 + REGLA 3)
        respuesta = await obtener_respuesta_modulo(
            texto, sid, modulo["nombre"]
        )
        sesion["etapa"] = "duda_modulo"
        return [
            {"tipo": "response", "contenido": respuesta},
            *_eventos_otra_duda_modulo(modulo["nombre"])
        ]

    # ── ETAPA 9: Continuar o salir ────────────────────────────────
    elif etapa == "continuar_o_salir":
        if texto == "ver_otro":
            sesion["etapa"] = "seleccionar_categoria"
            sesion["modulo_actual"] = None
            return [
                {"tipo": "response", "contenido": "¿Qué categoría te interesa?"},
                {"tipo": "buttons", "contenido": [
                    _btn("🖥️ Plataformas", "plataformas"),
                    _btn("📡 Dispositivos", "dispositivos")
                ]}
            ]
        elif texto == "volver_menu":
            sesion["etapa"] = "menu_principal"
            return _eventos_menu_principal()
        elif texto == "salir":
            sesion["etapa"] = "pedir_dni"
            sesion["dni"] = None
            return [{"tipo": "response", "contenido":
                     "¡Hasta pronto! Vuelve cuando quieras seguir capacitándote. 👋"}]
        resuelto = _resolver_intencion(texto, _MAPAS_INTENCION["continuar_o_salir"])
        if resuelto is not None:
            texto = resuelto
            if texto == "ver_otro":
                sesion["etapa"] = "seleccionar_categoria"
                sesion["modulo_actual"] = None
                return [
                    {"tipo": "response", "contenido": "¿Qué categoría te interesa?"},
                    {"tipo": "buttons", "contenido": [
                        _btn("🖥️ Plataformas", "plataformas"),
                        _btn("📡 Dispositivos", "dispositivos")
                    ]}
                ]
            elif texto == "volver_menu":
                sesion["etapa"] = "menu_principal"
                return _eventos_menu_principal()
            elif texto == "salir":
                sesion["etapa"] = "pedir_dni"
                sesion["dni"] = None
                return [{"tipo": "response", "contenido":
                         "¡Hasta pronto! Vuelve cuando quieras seguir capacitándote. 👋"}]
        return _eventos_continuar()

    return [{"tipo": "response", "contenido":
             "Ha ocurrido un error inesperado. Por favor recarga la página."}]
