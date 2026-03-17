#!/usr/bin/env python
"""
Ingesta de PDFs de módulos CECOM en pgvector.

Uso:
    python procesar_pdf.py "Nombre del Módulo" ruta/al/manual.pdf

Ejemplos:
    python procesar_pdf.py "Mapa CECOM" manuales/mapa_cecom.pdf
    python procesar_pdf.py "Radio Dolphin" manuales/radio_dolphin.pdf

Requisitos del sistema:
    - poppler instalado y en PATH (Windows: descarga de
      https://github.com/oschwartz10612/poppler-windows/releases)
    - ANTHROPIC_API_KEY en .env
    - pgvector habilitado en PostgreSQL (el script lo habilita automáticamente)
"""
import sys
import os
import base64
import io
from dotenv import load_dotenv

load_dotenv()


# Mapeo de categoría MODULOS → tipo de prompt
_CATEGORIA_A_TIPO = {"plataformas": "plataforma", "dispositivos": "dispositivo"}


def _obtener_tipo_modulo(nombre_modulo: str) -> str:
    """Busca el módulo en modules.py y retorna su tipo ('plataforma' o 'dispositivo')."""
    from modules import MODULOS
    for categoria, modulos in MODULOS.items():
        if any(m["nombre"] == nombre_modulo for m in modulos):
            return _CATEGORIA_A_TIPO[categoria]
    nombres_disponibles = [m["nombre"] for modulos in MODULOS.values() for m in modulos]
    raise ValueError(
        f"Módulo {nombre_modulo!r} no encontrado en modules.py. "
        f"Nombres disponibles: {nombres_disponibles}"
    )


_PROMPTS = {
    "plataforma": (
        "Eres un experto en capacitación para personal municipal y en organización "
        "de contenido técnico para sistemas de búsqueda semántica. "
        "Esta imagen pertenece al manual de una plataforma de software "
        "usada por el personal operativo y administrativo de CECOM "
        "(Centro de Monitoreo y Videovigilancia) de la Municipalidad "
        "de San Juan de Lurigancho, Lima, Perú. El personal incluye "
        "operadores de monitoreo, serenazgo, transporte, fiscalización "
        "y administrativos. "
        "Interpreta la imagen como si explicaras el software a un "
        "operador que nunca lo ha usado. Describe qué muestra la "
        "pantalla, qué debe hacer el operador paso a paso, "
        "qué significa cada botón o flecha visible, y los datos exactos "
        "que aparecen como nombres, fechas o ubicaciones. "
        "ESTRUCTURA OBLIGATORIA: organiza el contenido en secciones temáticas. "
        "Cada sección debe comenzar con un título descriptivo en MAYÚSCULAS "
        "que indique exactamente el tema tratado. "
        "Agrupa en la misma sección todo el contenido relacionado a un mismo "
        "procedimiento o función. No mezcles temas distintos en una misma sección. "
        "Cada sección debe poder leerse de forma independiente sin necesitar "
        "contexto de las demás secciones. "
        "Escribe en español, sin markdown, sin símbolos # ni asteriscos, "
        "sin guiones dobles. Sé específico y usa los datos exactos que ves en la imagen."
    ),
    "dispositivo": (
        "Eres un experto en capacitación para personal municipal. "
        "Esta imagen pertenece al manual de un dispositivo físico usado por personal operativo "
        "de CECOM (Centro de Monitoreo y Videovigilancia) de la Municipalidad de San Juan de Lurigancho, Lima, Perú. "
        "El personal incluye serenazgo, transporte y fiscalización. "
        "Describe cómo se usa el dispositivo, qué hace cada botón o componente visible, "
        "los modos de operación disponibles, y qué debe hacer el operador en cada situación. "
        "Si hay instrucciones de uso o advertencias visibles, descríbelas. "
        "Escribe en español, en párrafos continuos, sin markdown, sin símbolos # ni asteriscos, "
        "sin guiones dobles."
    ),
}


def _extraer_texto_pagina(imagen_pil, tipo_modulo: str) -> str:
    """Envía una página (imagen PIL) a Claude Vision y devuelve el texto extraído."""
    if tipo_modulo not in _PROMPTS:
        raise ValueError(
            f"tipo_modulo debe ser 'plataforma' o 'dispositivo', recibido: {tipo_modulo!r}"
        )
    import anthropic
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    buffer = io.BytesIO()
    imagen_pil.save(buffer, format="PNG")
    imagen_b64 = base64.standard_b64encode(buffer.getvalue()).decode("utf-8")

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": imagen_b64,
                    },
                },
                {
                    "type": "text",
                    "text": _PROMPTS[tipo_modulo],
                },
            ],
        }],
    )
    if not response.content or response.content[0].type != "text":
        raise ValueError(f"Respuesta inesperada de la API: {response.content}")
    return response.content[0].text


def procesar_pdf(nombre_modulo: str, ruta_pdf: str) -> None:
    """Pipeline completo: PDF → imágenes → texto → chunks → pgvector."""
    tipo_modulo = _obtener_tipo_modulo(nombre_modulo)
    print(f"      Tipo detectado: {tipo_modulo} (desde modules.py).")
    from pdf2image import convert_from_path
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from rag import init_extension, eliminar_chunks_modulo, guardar_chunks

    if not os.path.exists(ruta_pdf):
        print(f"❌ No se encontró el archivo: {ruta_pdf}")
        sys.exit(1)

    print(f"[1/4] Inicializando extensión pgvector...")
    init_extension()

    print(f"[2/4] Convirtiendo PDF a imágenes: {ruta_pdf}")
    paginas = convert_from_path(ruta_pdf)
    print(f"      {len(paginas)} página(s) encontrada(s).")

    # Archivo temporal: si ya existe (de una ejecución anterior fallida),
    # reutilizar el texto sin volver a llamar a la API.
    nombre_seguro = nombre_modulo.replace(" ", "_").replace("/", "-")
    ruta_texto = os.path.join(os.path.dirname(ruta_pdf), f"{nombre_seguro}_texto.txt")

    if os.path.exists(ruta_texto):
        print(f"[3/4] Texto ya extraído — reutilizando {ruta_texto} (borra el archivo para forzar re-extracción).")
        with open(ruta_texto, "r", encoding="utf-8") as f:
            texto_completo = f.read()
    else:
        print(f"[3/4] Extrayendo texto con Claude Vision (claude-sonnet-4-6)...")
        texto_completo = ""
        for i, pagina in enumerate(paginas, 1):
            print(f"      Página {i}/{len(paginas)}...", end=" ", flush=True)
            texto_pagina = _extraer_texto_pagina(pagina, tipo_modulo)
            texto_completo += texto_pagina + "\n\n"
            print("OK")
        with open(ruta_texto, "w", encoding="utf-8") as f:
            f.write(texto_completo)
        print(f"      Texto guardado en {ruta_texto}.")

    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
    chunks = splitter.split_text(texto_completo)
    print(f"      {len(chunks)} chunk(s) generado(s).")

    print(f"[4/4] Guardando en pgvector (módulo: {nombre_modulo!r})...")
    eliminar_chunks_modulo(nombre_modulo)
    guardar_chunks(nombre_modulo, chunks)

    print(f"\n✅ Listo. {len(chunks)} chunks guardados para '{nombre_modulo}'.")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python procesar_pdf.py <nombre_modulo> <ruta_pdf>")
        print('Ejemplo: python procesar_pdf.py "Mapa CECOM" manuales/mapa.pdf')
        print('Ejemplo: python procesar_pdf.py "Radio Dolphin" manuales/radio.pdf')
        sys.exit(1)
    procesar_pdf(sys.argv[1], sys.argv[2])
