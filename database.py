"""Operaciones de base de datos para el chatbot CECOM."""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()


def _crear_conexion():
    """Crea y retorna una conexión a PostgreSQL usando variables de entorno."""
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "cecom_chatbot"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )


def registrar_o_actualizar_usuario(dni: str) -> dict:
    """
    Registra un nuevo usuario o actualiza su último acceso.

    Args:
        dni: DNI de 8 dígitos del usuario.

    Returns:
        dict con {es_nuevo: bool, ultimo_acceso: datetime | None}
    """
    try:
        conn = _crear_conexion()
    except Exception as e:
        raise RuntimeError(f"Error de conexión a la base de datos: {e}")
    cur = conn.cursor()
    try:
        cur.execute("SELECT ultimo_acceso FROM usuarios WHERE dni = %s", (dni,))
        fila = cur.fetchone()

        if fila is None:
            cur.execute("INSERT INTO usuarios (dni) VALUES (%s)", (dni,))
            conn.commit()
            return {"es_nuevo": True, "ultimo_acceso": None}
        else:
            ultimo_acceso = fila[0]
            cur.execute(
                "UPDATE usuarios SET ultimo_acceso = CURRENT_TIMESTAMP WHERE dni = %s",
                (dni,)
            )
            conn.commit()
            return {"es_nuevo": False, "ultimo_acceso": ultimo_acceso}
    except Exception as e:
        conn.rollback()
        raise RuntimeError(f"Error de base de datos: {e}")
    finally:
        cur.close()
        conn.close()


def registrar_actividad(
    dni: str,
    modulo: str,
    categoria: str,
    hizo_quiz: bool = False,
    puntaje_quiz: int | None = None
) -> None:
    """Registra la actividad de un usuario al revisar un módulo."""
    try:
        conn = _crear_conexion()
    except Exception as e:
        raise RuntimeError(f"Error de conexión a la base de datos: {e}")
    cur = conn.cursor()
    try:
        cur.execute(
            """INSERT INTO actividad (dni, modulo, categoria, hizo_quiz, puntaje_quiz)
               VALUES (%s, %s, %s, %s, %s)""",
            (dni, modulo, categoria, hizo_quiz, puntaje_quiz)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise RuntimeError(f"Error de base de datos: {e}")
    finally:
        cur.close()
        conn.close()


def obtener_historial(dni: str) -> list:
    """Retorna lista de nombres de módulos visitados por el usuario."""
    try:
        conn = _crear_conexion()
    except Exception as e:
        raise RuntimeError(f"Error de conexión a la base de datos: {e}")
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT DISTINCT modulo FROM actividad WHERE dni = %s ORDER BY modulo",
            (dni,)
        )
        return [fila[0] for fila in cur.fetchall()]
    except Exception as e:
        raise RuntimeError(f"Error de base de datos: {e}")
    finally:
        cur.close()
        conn.close()
