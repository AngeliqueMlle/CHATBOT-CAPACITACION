"""Tests para database.py — conexión a PostgreSQL mockeada."""
from unittest.mock import patch, MagicMock
from datetime import datetime
import pytest


def _make_mock_conn(fetchone_value=None, fetchall_value=None):
    """Crea un mock de conexión psycopg2 sin context managers."""
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = fetchone_value
    mock_cursor.fetchall.return_value = fetchall_value or []
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    return mock_conn, mock_cursor


def test_registrar_usuario_nuevo():
    """DNI inexistente debe insertarse y retornar es_nuevo=True."""
    mock_conn, mock_cursor = _make_mock_conn(fetchone_value=None)

    with patch("database._crear_conexion", return_value=mock_conn):
        import database
        resultado = database.registrar_o_actualizar_usuario("12345678")

    assert resultado["es_nuevo"] is True
    assert resultado["ultimo_acceso"] is None
    llamadas = [str(c) for c in mock_cursor.execute.call_args_list]
    assert any("INSERT" in c for c in llamadas)
    mock_conn.close.assert_called_once()
    mock_cursor.close.assert_called_once()


def test_registrar_usuario_existente():
    """DNI existente debe actualizar ultimo_acceso y retornar es_nuevo=False."""
    fecha = datetime(2025, 6, 10, 9, 0)
    mock_conn, mock_cursor = _make_mock_conn(fetchone_value=(fecha,))

    with patch("database._crear_conexion", return_value=mock_conn):
        import database
        resultado = database.registrar_o_actualizar_usuario("12345678")

    assert resultado["es_nuevo"] is False
    assert resultado["ultimo_acceso"] == fecha
    llamadas = [str(c) for c in mock_cursor.execute.call_args_list]
    assert any("UPDATE" in c for c in llamadas)
    mock_conn.close.assert_called_once()
    mock_cursor.close.assert_called_once()


def test_registrar_actividad_sin_quiz():
    """registrar_actividad sin quiz debe ejecutar INSERT con hizo_quiz=False."""
    mock_conn, mock_cursor = _make_mock_conn()

    with patch("database._crear_conexion", return_value=mock_conn):
        import database
        database.registrar_actividad("12345678", "App de Incidencias", "plataformas")

    mock_cursor.execute.assert_called_once()
    args = mock_cursor.execute.call_args[0]
    assert "INSERT" in args[0]
    assert False in args[1]
    mock_conn.close.assert_called_once()
    mock_cursor.close.assert_called_once()


def test_registrar_actividad_con_quiz():
    """registrar_actividad con quiz debe incluir puntaje."""
    mock_conn, mock_cursor = _make_mock_conn()

    with patch("database._crear_conexion", return_value=mock_conn):
        import database
        database.registrar_actividad("12345678", "Centinela", "plataformas", True, 2)

    args = mock_cursor.execute.call_args[0]
    assert True in args[1]
    assert 2 in args[1]
    mock_conn.close.assert_called_once()
    mock_cursor.close.assert_called_once()


def test_obtener_historial():
    """obtener_historial debe retornar lista de módulos del usuario."""
    mock_conn, mock_cursor = _make_mock_conn(
        fetchall_value=[("App de Incidencias",), ("Centinela",)]
    )

    with patch("database._crear_conexion", return_value=mock_conn):
        import database
        resultado = database.obtener_historial("12345678")

    assert resultado == ["App de Incidencias", "Centinela"]
    mock_conn.close.assert_called_once()
    mock_cursor.close.assert_called_once()


def test_obtener_historial_vacio():
    """Usuario sin actividad debe retornar lista vacía."""
    mock_conn, mock_cursor = _make_mock_conn(fetchall_value=[])

    with patch("database._crear_conexion", return_value=mock_conn):
        import database
        resultado = database.obtener_historial("99999999")

    assert resultado == []
    mock_conn.close.assert_called_once()
    mock_cursor.close.assert_called_once()
