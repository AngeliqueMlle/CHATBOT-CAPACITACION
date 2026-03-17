"""Tests para rag.py."""
import pytest
from unittest.mock import MagicMock
from langchain_core.documents import Document


def test_buscar_contexto_con_resultados():
    """Cuando hay chunks, devuelve texto concatenado."""
    from rag import buscar_contexto
    mock_store = MagicMock()
    mock_store.similarity_search.return_value = [
        Document(page_content="Paso 1: abrir la app."),
        Document(page_content="Paso 2: completar el formulario."),
    ]
    resultado = buscar_contexto(
        "¿cómo crear un incidente?", "App de Incidencias", k=3, _store=mock_store
    )
    assert "Paso 1: abrir la app." in resultado
    assert "Paso 2: completar el formulario." in resultado
    mock_store.similarity_search.assert_called_once_with(
        "¿cómo crear un incidente?", k=3, filter={"modulo": "App de Incidencias"}
    )


def test_buscar_contexto_sin_resultados():
    """Cuando no hay chunks, devuelve cadena vacía."""
    from rag import buscar_contexto
    mock_store = MagicMock()
    mock_store.similarity_search.return_value = []
    resultado = buscar_contexto("pregunta sin respuesta", "Centinela", _store=mock_store)
    assert resultado == ""


def test_buscar_contexto_concatena_con_doble_salto():
    """Los chunks deben ir separados por doble salto de línea."""
    from rag import buscar_contexto
    mock_store = MagicMock()
    mock_store.similarity_search.return_value = [
        Document(page_content="Bloque A"),
        Document(page_content="Bloque B"),
    ]
    resultado = buscar_contexto("pregunta", "Modulo X", _store=mock_store)
    assert resultado == "Bloque A\n\nBloque B"
