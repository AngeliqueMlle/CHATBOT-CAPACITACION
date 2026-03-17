"""Operaciones de búsqueda vectorial con PGVector para el chatbot CECOM."""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

_COLLECTION = "cecom_rag_chunks"
_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# Singleton cargado de forma lazy para no bloquear el arranque del servidor
_embeddings_cache = None


def _conn_string() -> str:
    return (
        f"postgresql+psycopg2://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
        f"@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}"
        f"/{os.getenv('DB_NAME')}"
    )


def _get_embeddings():
    global _embeddings_cache
    if _embeddings_cache is None:
        from langchain_huggingface import HuggingFaceEmbeddings
        _embeddings_cache = HuggingFaceEmbeddings(model_name=_MODEL_NAME)
    return _embeddings_cache


def init_extension() -> None:
    """Crea la extensión pgvector si no existe."""
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
        )
    except Exception as e:
        raise RuntimeError(f"Error de conexión a la base de datos: {e}") from e
    cur = conn.cursor()
    try:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise RuntimeError(f"Error al crear extensión pgvector: {e}") from e
    finally:
        cur.close()
        conn.close()


def buscar_contexto(
    pregunta: str, nombre_modulo: str, k: int = 5, _store=None
) -> str:
    """
    Busca los k chunks más relevantes para la pregunta en el módulo dado.

    Args:
        pregunta: Texto de la pregunta del usuario.
        nombre_modulo: Nombre exacto del módulo (ej. "Mapa CECOM").
        k: Cantidad de chunks a recuperar.
        _store: Inyección del vector store (solo para tests).

    Returns:
        Texto concatenado de los chunks encontrados, o "" si no hay resultados.
    """
    from langchain_community.vectorstores import PGVector
    store = _store or PGVector(
        collection_name=_COLLECTION,
        connection_string=_conn_string(),
        embedding_function=_get_embeddings(),
    )
    results = store.similarity_search(
        pregunta, k=k, filter={"modulo": nombre_modulo}
    )
    if not results:
        return ""
    return "\n\n".join(doc.page_content for doc in results)


def eliminar_chunks_modulo(nombre_modulo: str) -> None:
    """Elimina todos los vectores existentes de un módulo antes de reingestarlo."""
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
        )
    except Exception as e:
        raise RuntimeError(f"Error de conexión a la base de datos: {e}") from e
    cur = conn.cursor()
    try:
        # Verificar si la tabla existe antes de intentar el DELETE.
        # En la primera ejecución, PGVector aún no la ha creado.
        cur.execute(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'langchain_pg_embedding'
            )
            """
        )
        if cur.fetchone()[0]:
            cur.execute(
                """
                DELETE FROM langchain_pg_embedding
                WHERE cmetadata->>'modulo' = %s
                  AND collection_id = (
                      SELECT uuid FROM langchain_pg_collection WHERE name = %s
                  )
                """,
                (nombre_modulo, _COLLECTION),
            )
            conn.commit()
    except Exception as e:
        conn.rollback()
        raise RuntimeError(f"Error al eliminar chunks del módulo '{nombre_modulo}': {e}") from e
    finally:
        cur.close()
        conn.close()


def guardar_chunks(nombre_modulo: str, textos: list[str]) -> None:
    """
    Genera embeddings y guarda los chunks en pgvector.

    Args:
        nombre_modulo: Nombre del módulo para el filtrado posterior.
        textos: Lista de strings (chunks) a indexar.
    """
    from langchain_community.vectorstores import PGVector
    from langchain_core.documents import Document
    docs = [
        Document(page_content=t, metadata={"modulo": nombre_modulo})
        for t in textos
    ]
    PGVector.from_documents(
        documents=docs,
        embedding=_get_embeddings(),
        collection_name=_COLLECTION,
        connection_string=_conn_string(),
    )
