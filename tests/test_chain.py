"""Tests de la máquina de estados en chain.py."""
import pytest
from unittest.mock import patch, AsyncMock
from datetime import datetime


@pytest.fixture(autouse=True)
def limpiar_sesiones():
    """Limpia todas las sesiones antes y después de cada test."""
    import chain
    chain.sesiones.clear()
    yield
    chain.sesiones.clear()


def _sesion_en(sid, etapa, **kwargs):
    """Inserta una sesión directamente en el estado dado."""
    import chain
    chain.sesiones[sid] = {
        "dni": kwargs.get("dni", "12345678"),
        "etapa": etapa,
        "modulo_actual": kwargs.get("modulo_actual", None),
        "categoria_actual": kwargs.get("categoria_actual", None),
        "quiz_pregunta_actual": kwargs.get("quiz_pregunta_actual", 0),
        "quiz_puntaje": kwargs.get("quiz_puntaje", 0),
        "historial_chat": kwargs.get("historial_chat", [])
    }


# ── pedir_dni ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dni_invalido_letras():
    import chain
    eventos = await chain.procesar_mensaje("s1", "abc12345")
    assert eventos[0]["tipo"] == "response"
    texto = eventos[0]["contenido"].lower()
    assert "válido" in texto or "dígito" in texto or "numérico" in texto


@pytest.mark.asyncio
async def test_dni_invalido_corto():
    import chain
    eventos = await chain.procesar_mensaje("s2", "1234")
    assert eventos[0]["tipo"] == "response"


@pytest.mark.asyncio
async def test_dni_valido_nuevo_usuario():
    import chain
    with patch("chain.registrar_o_actualizar_usuario", return_value={"es_nuevo": True, "ultimo_acceso": None}):
        with patch("chain.generar_bienvenida_nuevo_usuario", new=AsyncMock(return_value="¡Bienvenido!")):
            eventos = await chain.procesar_mensaje("s3", "12345678")

    tipos = [e["tipo"] for e in eventos]
    assert "response" in tipos
    assert "buttons" in tipos
    assert chain.sesiones["s3"]["etapa"] == "menu_principal"


@pytest.mark.asyncio
async def test_dni_valido_usuario_existente():
    import chain
    fecha = datetime(2025, 10, 5, 14, 30)
    with patch("chain.registrar_o_actualizar_usuario", return_value={"es_nuevo": False, "ultimo_acceso": fecha}):
        eventos = await chain.procesar_mensaje("s4", "12345678")

    texto = next(e["contenido"] for e in eventos if e["tipo"] == "response")
    assert "2025" in texto or "05/10" in texto or "bienvenido" in texto.lower()


# ── menu_principal ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_menu_opcion_1():
    import chain
    _sesion_en("s5", "menu_principal")
    eventos = await chain.procesar_mensaje("s5", "1")

    assert chain.sesiones["s5"]["etapa"] == "seleccionar_categoria"
    botones = next(e for e in eventos if e["tipo"] == "buttons")
    valores = [b["value"] for b in botones["contenido"]]
    assert "plataformas" in valores
    assert "dispositivos" in valores


@pytest.mark.asyncio
async def test_menu_opcion_2():
    import chain
    _sesion_en("s6", "menu_principal")
    eventos = await chain.procesar_mensaje("s6", "2")

    assert chain.sesiones["s6"]["etapa"] == "duda_libre"


# ── seleccionar_categoria ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_categoria_plataformas_lista_12():
    import chain
    _sesion_en("s7", "seleccionar_categoria")
    eventos = await chain.procesar_mensaje("s7", "plataformas")

    assert chain.sesiones["s7"]["etapa"] == "seleccionar_modulo"
    botones = next(e for e in eventos if e["tipo"] == "buttons")
    assert len(botones["contenido"]) == 12


@pytest.mark.asyncio
async def test_categoria_dispositivos_lista_2():
    import chain
    _sesion_en("s8", "seleccionar_categoria")
    eventos = await chain.procesar_mensaje("s8", "dispositivos")

    botones = next(e for e in eventos if e["tipo"] == "buttons")
    assert len(botones["contenido"]) == 2


# ── ofrecer_quiz ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_omitir_quiz_registra_y_continua():
    import chain
    modulo = {"nombre": "Centinela", "resumen": "...", "pdf": "", "video": ""}
    _sesion_en("s9", "ofrecer_quiz", modulo_actual=modulo, categoria_actual="plataformas")

    with patch("chain.registrar_actividad") as mock_reg:
        eventos = await chain.procesar_mensaje("s9", "quiz_no")

    assert chain.sesiones["s9"]["etapa"] == "continuar_o_salir"
    mock_reg.assert_called_once_with("12345678", "Centinela", "plataformas", False, None)
    botones = next(e for e in eventos if e["tipo"] == "buttons")
    valores = [b["value"] for b in botones["contenido"]]
    assert "ver_otro" in valores
    assert "salir" in valores


# ── duda_libre ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_duda_libre_llama_ia_y_vuelve_menu():
    import chain
    _sesion_en("s10", "duda_libre")

    with patch("chain.obtener_respuesta_ia", new=AsyncMock(return_value="Esta es la respuesta.")):
        eventos = await chain.procesar_mensaje("s10", "¿Cómo funciona el mapa?")

    assert chain.sesiones["s10"]["etapa"] == "menu_principal"
    respuestas = [e["contenido"] for e in eventos if e["tipo"] == "response"]
    assert "Esta es la respuesta." in respuestas


# ── seleccionar_modulo ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_seleccionar_modulo_emite_card():
    """Seleccionar un módulo válido debe emitir evento card y ofrecer quiz."""
    import chain
    _sesion_en("s11", "seleccionar_modulo", categoria_actual="plataformas")
    eventos = await chain.procesar_mensaje("s11", "Centinela")

    assert chain.sesiones["s11"]["etapa"] == "duda_modulo"
    tipos = [e["tipo"] for e in eventos]
    assert "card" in tipos
    assert "buttons" in tipos
    card = next(e for e in eventos if e["tipo"] == "card")
    assert card["contenido"]["nombre"] == "Centinela"
    botones = next(e for e in eventos if e["tipo"] == "buttons")
    valores = [b["value"] for b in botones["contenido"]]
    assert "con_duda_modulo" in valores
    assert "sin_duda_modulo" in valores


# ── quiz_en_curso ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_quiz_respuesta_correcta_avanza():
    """Respuesta correcta debe dar feedback positivo y avanzar a pregunta 2."""
    import chain
    modulo = {"nombre": "App de Incidencias", "resumen": "...", "pdf": "", "video": ""}
    _sesion_en("s12", "quiz_en_curso", modulo_actual=modulo,
               categoria_actual="plataformas", quiz_pregunta_actual=0, quiz_puntaje=0)

    # La respuesta correcta para pregunta 0 de "App de Incidencias" es índice 1
    eventos = await chain.procesar_mensaje("s12", "1")

    respuestas = [e["contenido"] for e in eventos if e["tipo"] == "response"]
    assert any("Correcto" in r or "correcto" in r for r in respuestas)
    assert chain.sesiones["s12"]["quiz_puntaje"] == 1
    # Debe mostrar pregunta 2
    assert chain.sesiones["s12"]["quiz_pregunta_actual"] == 1


@pytest.mark.asyncio
async def test_quiz_completo_registra_actividad():
    """Al completar el quiz (pregunta 2) debe llamar a registrar_actividad con puntaje."""
    import chain
    modulo = {"nombre": "App de Incidencias", "resumen": "...", "pdf": "", "video": ""}
    # Simulamos que ya respondió pregunta 0, ahora está en pregunta 1 (última)
    _sesion_en("s13", "quiz_en_curso", modulo_actual=modulo,
               categoria_actual="plataformas", quiz_pregunta_actual=1, quiz_puntaje=1)

    with patch("chain.registrar_actividad") as mock_reg:
        eventos = await chain.procesar_mensaje("s13", "2")  # índice 2 es correcta para pregunta 1

    assert chain.sesiones["s13"]["etapa"] == "continuar_o_salir"
    mock_reg.assert_called_once()
    call_args = mock_reg.call_args[0]
    assert call_args[3] is True  # hizo_quiz=True
    assert isinstance(call_args[4], int)  # puntaje es entero


# ── continuar_o_salir ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_continuar_ver_otro_vuelve_a_categorias():
    """'ver_otro' debe llevar de vuelta a seleccionar_categoria."""
    import chain
    _sesion_en("s14", "continuar_o_salir")
    eventos = await chain.procesar_mensaje("s14", "ver_otro")

    assert chain.sesiones["s14"]["etapa"] == "seleccionar_categoria"
    botones = next(e for e in eventos if e["tipo"] == "buttons")
    valores = [b["value"] for b in botones["contenido"]]
    assert "plataformas" in valores


@pytest.mark.asyncio
async def test_continuar_salir_reinicia_sesion():
    """'salir' debe limpiar el DNI y volver a pedir_dni."""
    import chain
    _sesion_en("s15", "continuar_o_salir", dni="12345678")
    eventos = await chain.procesar_mensaje("s15", "salir")

    assert chain.sesiones["s15"]["etapa"] == "pedir_dni"
    assert chain.sesiones["s15"]["dni"] is None
    assert any("pronto" in e["contenido"].lower() or "hasta" in e["contenido"].lower()
               for e in eventos if e["tipo"] == "response")


# ── helpers de intención ───────────────────────────────────────────

def test_normalizar_minusculas_y_sin_acentos():
    from chain import _normalizar
    assert _normalizar("Módulo") == "modulo"
    assert _normalizar("CECOM") == "cecom"
    assert _normalizar("  hola  ") == "hola"
    assert _normalizar("así") == "asi"


def test_resolver_intencion_exacta():
    from chain import _resolver_intencion
    mapa = {"capacitar": "1", "duda": "2"}
    assert _resolver_intencion("capacitar", mapa) == "1"
    assert _resolver_intencion("duda", mapa) == "2"


def test_resolver_intencion_dentro_de_frase():
    from chain import _resolver_intencion
    mapa = {"capacitar": "1", "duda": "2"}
    assert _resolver_intencion("quiero capacitarme", mapa) is None  # "capacitar" no es palabra completa dentro de "capacitarme"
    assert _resolver_intencion("tengo una duda", mapa) == "2"


def test_resolver_intencion_sin_match():
    from chain import _resolver_intencion
    mapa = {"capacitar": "1"}
    assert _resolver_intencion("otra cosa", mapa) is None


def test_resolver_intencion_word_boundary_no_substring():
    from chain import _resolver_intencion
    # "si" no debe matchear dentro de "asi"
    mapa = {"si": "quiz_si"}
    assert _resolver_intencion("así que no", mapa) is None
    assert _resolver_intencion("claro que si", mapa) == "quiz_si"


def test_resolver_intencion_normaliza_entrada():
    from chain import _resolver_intencion
    mapa = {"modulo": "1"}
    assert _resolver_intencion("MÓDULO", mapa) == "1"


# ── _resolver_modulo ───────────────────────────────────────────────

def test_resolver_modulo_coincidencia_unica():
    from chain import _resolver_modulo
    from modules import MODULOS
    resultado = _resolver_modulo("mapa", MODULOS["plataformas"])
    assert resultado["tipo"] == "unico"
    assert resultado["modulo"]["nombre"] == "Mapa CECOM"


def test_resolver_modulo_sin_coincidencia():
    from chain import _resolver_modulo
    from modules import MODULOS
    resultado = _resolver_modulo("helicoptero", MODULOS["plataformas"])
    assert resultado["tipo"] == "ninguno"


def test_resolver_modulo_ambiguedad():
    from chain import _resolver_modulo
    from modules import MODULOS
    resultado = _resolver_modulo("sistema", MODULOS["plataformas"])
    assert resultado["tipo"] == "ambiguo"
    nombres = [m["nombre"] for m in resultado["modulos"]]
    assert "Sistema de Validación" in nombres
    assert "Sistema de Cazadores" in nombres


def test_resolver_modulo_nombre_corto_puc():
    from chain import _resolver_modulo
    from modules import MODULOS
    resultado = _resolver_modulo("puc", MODULOS["plataformas"])
    assert resultado["tipo"] == "unico"
    assert resultado["modulo"]["nombre"] == "PUC"


def test_resolver_modulo_sin_palabras_largas_ni_cortas():
    from chain import _resolver_modulo
    from modules import MODULOS
    resultado = _resolver_modulo("no se", MODULOS["plataformas"])
    assert resultado["tipo"] == "ninguno"


# ── intención en menu_principal ────────────────────────────────────

@pytest.mark.asyncio
async def test_menu_intenta_capacitarme():
    import chain
    _sesion_en("si1", "menu_principal")
    await chain.procesar_mensaje("si1", "capacitarme")
    assert chain.sesiones["si1"]["etapa"] == "seleccionar_categoria"


@pytest.mark.asyncio
async def test_menu_intenta_duda():
    import chain
    _sesion_en("si2", "menu_principal")
    await chain.procesar_mensaje("si2", "tengo una duda")
    assert chain.sesiones["si2"]["etapa"] == "duda_libre"


@pytest.mark.asyncio
async def test_menu_texto_irreconocible_muestra_aviso():
    import chain
    _sesion_en("si3", "menu_principal")
    eventos = await chain.procesar_mensaje("si3", "xyz123")
    tipos = [e["tipo"] for e in eventos]
    assert "response" in tipos
    assert "buttons" in tipos
    texto = next(e["contenido"] for e in eventos if e["tipo"] == "response")
    assert "entend" in texto.lower() or "opcion" in texto.lower() or "opción" in texto.lower()


# ── intención en seleccionar_categoria ────────────────────────────

@pytest.mark.asyncio
async def test_categoria_intenta_plataforma():
    import chain
    _sesion_en("si4", "seleccionar_categoria")
    await chain.procesar_mensaje("si4", "quiero ver plataformas")
    assert chain.sesiones["si4"]["etapa"] == "seleccionar_modulo"


@pytest.mark.asyncio
async def test_categoria_intenta_dispositivo():
    import chain
    _sesion_en("si5", "seleccionar_categoria")
    await chain.procesar_mensaje("si5", "dispositivo")
    assert chain.sesiones["si5"]["etapa"] == "seleccionar_modulo"


# ── intención en seleccionar_modulo ───────────────────────────────

@pytest.mark.asyncio
async def test_modulo_intenta_mapa_cecom():
    import chain
    _sesion_en("si6", "seleccionar_modulo", categoria_actual="plataformas")
    eventos = await chain.procesar_mensaje("si6", "mapa")
    assert chain.sesiones["si6"]["etapa"] == "duda_modulo"
    card = next(e for e in eventos if e["tipo"] == "card")
    assert card["contenido"]["nombre"] == "Mapa CECOM"


@pytest.mark.asyncio
async def test_modulo_intenta_puc_corto():
    import chain
    _sesion_en("si7", "seleccionar_modulo", categoria_actual="plataformas")
    eventos = await chain.procesar_mensaje("si7", "puc")
    assert chain.sesiones["si7"]["etapa"] == "duda_modulo"
    card = next(e for e in eventos if e["tipo"] == "card")
    assert card["contenido"]["nombre"] == "PUC"


@pytest.mark.asyncio
async def test_modulo_ambiguo_muestra_opciones_reducidas():
    import chain
    _sesion_en("si8", "seleccionar_modulo", categoria_actual="plataformas")
    eventos = await chain.procesar_mensaje("si8", "sistema")
    assert chain.sesiones["si8"]["etapa"] == "seleccionar_modulo"
    botones = next(e for e in eventos if e["tipo"] == "buttons")
    nombres = [b["label"] for b in botones["contenido"]]
    assert len(nombres) == 2
    assert any("Validación" in n or "Validacion" in n for n in nombres)
    assert any("Cazadores" in n for n in nombres)


@pytest.mark.asyncio
async def test_modulo_sin_coincidencia_muestra_lista_completa():
    import chain
    _sesion_en("si9", "seleccionar_modulo", categoria_actual="plataformas")
    eventos = await chain.procesar_mensaje("si9", "helicoptero")
    assert chain.sesiones["si9"]["etapa"] == "seleccionar_modulo"
    botones = next(e for e in eventos if e["tipo"] == "buttons")
    assert len(botones["contenido"]) == 12


# ── intención en ofrecer_quiz ──────────────────────────────────────

@pytest.mark.asyncio
async def test_quiz_intenta_si_texto():
    import chain
    modulo = {"nombre": "Centinela", "resumen": "...", "pdf": "", "video": ""}
    _sesion_en("si10", "ofrecer_quiz", modulo_actual=modulo, categoria_actual="plataformas")
    with patch("chain.registrar_actividad"):
        await chain.procesar_mensaje("si10", "quiero hacerlo")
    assert chain.sesiones["si10"]["etapa"] == "quiz_en_curso"


@pytest.mark.asyncio
async def test_quiz_intenta_no_texto():
    import chain
    modulo = {"nombre": "Centinela", "resumen": "...", "pdf": "", "video": ""}
    _sesion_en("si11", "ofrecer_quiz", modulo_actual=modulo, categoria_actual="plataformas")
    with patch("chain.registrar_actividad"):
        await chain.procesar_mensaje("si11", "no gracias")
    assert chain.sesiones["si11"]["etapa"] == "continuar_o_salir"


@pytest.mark.asyncio
async def test_quiz_fallback_muestra_botones():
    import chain
    modulo = {"nombre": "Centinela", "resumen": "...", "pdf": "", "video": ""}
    _sesion_en("si12", "ofrecer_quiz", modulo_actual=modulo, categoria_actual="plataformas")
    eventos = await chain.procesar_mensaje("si12", "xyzxyz")
    tipos = [e["tipo"] for e in eventos]
    assert "buttons" in tipos
    botones = next(e for e in eventos if e["tipo"] == "buttons")
    valores = [b["value"] for b in botones["contenido"]]
    assert "quiz_si" in valores and "quiz_no" in valores


# ── intención en continuar_o_salir ────────────────────────────────

@pytest.mark.asyncio
async def test_continuar_intenta_volver_menu():
    import chain
    _sesion_en("si13", "continuar_o_salir")
    await chain.procesar_mensaje("si13", "quiero volver al menú")
    assert chain.sesiones["si13"]["etapa"] == "menu_principal"


@pytest.mark.asyncio
async def test_continuar_intenta_salir():
    import chain
    _sesion_en("si14", "continuar_o_salir")
    await chain.procesar_mensaje("si14", "chau")
    assert chain.sesiones["si14"]["etapa"] == "pedir_dni"


@pytest.mark.asyncio
async def test_continuar_volver_no_matchea_ver():
    """'volver' debe ir a menu_principal, no a ver_otro."""
    import chain
    _sesion_en("si15", "continuar_o_salir")
    await chain.procesar_mensaje("si15", "volver")
    assert chain.sesiones["si15"]["etapa"] == "menu_principal"


@pytest.mark.asyncio
async def test_obtener_respuesta_modulo_usa_rag():
    """obtener_respuesta_modulo debe llamar a buscar_contexto y pasar resultado al LLM."""
    from unittest.mock import patch, MagicMock, AsyncMock
    import chain
    chain.historial_sesiones.clear()
    with patch("chain.buscar_contexto", return_value="Contenido real del manual.") as mock_rag:
        # ChatGroq is imported lazily inside the function → patch at its source
        with patch("langchain_groq.ChatGroq") as MockGroq:
            mock_llm = AsyncMock()
            mock_llm.ainvoke.return_value = MagicMock(content="Respuesta del módulo.")
            MockGroq.return_value = mock_llm
            respuesta = await chain.obtener_respuesta_modulo(
                "¿Cómo crear un incidente?", "test_sid", "App de Incidencias"
            )
    assert respuesta == "Respuesta del módulo."
    mock_rag.assert_called_once_with("¿Cómo crear un incidente?", "App de Incidencias")


@pytest.mark.asyncio
async def test_obtener_respuesta_modulo_sin_contexto_devuelve_sin_info():
    """Cuando buscar_contexto devuelve '', devuelve _RESPUESTA_SIN_INFO SIN llamar al LLM."""
    from unittest.mock import patch
    import chain
    chain.historial_sesiones.clear()
    with patch("chain.buscar_contexto", return_value=""):
        with patch("langchain_groq.ChatGroq") as mock_groq:
            respuesta = await chain.obtener_respuesta_modulo(
                "Pregunta sin contenido", "test_sid", "Centinela"
            )
    assert respuesta == chain._RESPUESTA_SIN_INFO
    # Verifica que el LLM no fue invocado
    mock_groq.assert_not_called()
