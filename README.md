# CECOM-BOT — Chatbot de Capacitación

Asistente institucional del Centro de Comunicaciones Municipal (CECOM).
Capacita al personal en las herramientas tecnológicas de su trabajo diario mediante conversación guiada, RAG sobre manuales PDF y quizzes por módulo.

---

## Características

- **Bienvenida personalizada por IA** — saludo motivador para usuarios nuevos; muestra fecha de último acceso para recurrentes
- **Conversación mixta** — navega por botones o texto libre en cualquier etapa
- **14 módulos de capacitación** — 12 plataformas + 2 dispositivos
- **Memoria contextual por sesión** — el agente recuerda el hilo de preguntas durante la conversación; se reinicia al cerrar el chat
- **RAG sobre manuales PDF** — responde dudas usando únicamente el contenido del módulo, sin inventar información
- **Quiz opcional** — 2 preguntas por módulo con feedback inmediato por respuesta
- **Registro de actividad** — guarda por DNI: módulo visto, categoría, fecha, resultado del quiz
- **Botón Inicio** — visible en el header durante toda la sesión para volver al menú sin perder el DNI

---

## Stack

| Capa | Tecnología |
|---|---|
| Backend | Python 3.10 · FastAPI · python-socketio (ASGI) |
| IA | LangChain · Groq `llama-3.3-70b` · Mistral (fallback automático) |
| RAG | pgvector · LangChain PGVector · HuggingFace `paraphrase-multilingual-MiniLM-L12-v2` |
| PDF processing | Claude Vision (Anthropic) via `procesar_pdf.py` |
| Base de datos | PostgreSQL · psycopg2 |
| Frontend | HTML · CSS · JS vanilla · Socket.IO client |

---

## Requisitos previos

- **Python 3.10+**
- **PostgreSQL** con extensión [pgvector](https://github.com/pgvector/pgvector) instalada
- **Poppler** — necesario para ingestar PDFs. Verificar con `pdftoppm -v`.
  Si no está instalado, descargarlo desde [poppler-windows](https://github.com/oschwartz10612/poppler-windows/releases) y agregarlo al PATH del sistema.

---

## Instalación

**1. Dependencias**

```bash
pip install -r requirements.txt
```

**2. Variables de entorno**

```bash
cp .env.example .env
```

Completar `.env`:

```env
GROQ_API_KEY=
MISTRAL_API_KEY=
ANTHROPIC_API_KEY=        # para procesar_pdf.py (Claude Vision)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=cecom_chatbot
DB_USER=
DB_PASSWORD=
```

**3. Base de datos**

```sql
CREATE DATABASE cecom_chatbot;
\c cecom_chatbot

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS usuarios (
    dni VARCHAR(8) PRIMARY KEY,
    primer_acceso TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ultimo_acceso TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS actividad (
    id SERIAL PRIMARY KEY,
    dni VARCHAR(8) NOT NULL,
    modulo VARCHAR(100) NOT NULL,
    categoria VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    hizo_quiz BOOLEAN DEFAULT FALSE,
    puntaje_quiz INTEGER DEFAULT NULL
);
```

**4. Iniciar servidor**

```bash
uvicorn main:socket_app --reload --port 8000
```

Acceder en `http://localhost:8000`

---

## Ingestar un PDF

> `static/` no está en el repositorio. Antes de ingestar, crear manualmente la carpeta del módulo:
> ```
> static/modulos/{slug}/
> ```

Colocar el PDF dentro y ejecutar:

```bash
python procesar_pdf.py "Nombre del Módulo" static/modulos/{slug}/manual.pdf
```

El tipo de módulo se detecta automáticamente desde `modules.py`. Genera un `{Nombre_Modulo}_texto.txt` en la misma carpeta como respaldo — si el proceso se interrumpe, en la siguiente ejecución reutiliza ese archivo sin volver a llamar a la API.

Una vez procesado, actualizar los campos del módulo en `modules.py`:

```python
"pdf":     "/static/modulos/{slug}/manual.pdf",
"preview": "/static/modulos/{slug}/preview.jpg", # o None
```

---

## Tests

```bash
pytest tests/ -v
```

---

## Estructura

```
chatbot-capacitacion/
├── main.py              # FastAPI + Socket.IO
├── chain.py             # Máquina de estados conversacional
├── rag.py               # Búsqueda y carga de chunks (pgvector)
├── database.py          # Operaciones PostgreSQL
├── modules.py           # 14 módulos de capacitación
├── procesar_pdf.py      # CLI de ingesta PDF → pgvector
├── quizzes.json         # 2 preguntas por módulo
├── chat.html            # Interfaz web
├── static/modulos/      # PDFs, videos y previews por módulo
├── requirements.txt
├── .env.example
└── tests/
    ├── test_chain.py        # 15 tests — máquina de estados
    ├── test_database.py     # 6 tests — operaciones DB
    └── test_rag.py          # RAG (búsqueda y chunks)
```

---

## Flujo conversacional

```
Ingreso DNI
    └── Bienvenida personalizada (IA)
         │
         ├── Capacitarme
         │    └── Elegir categoría (Plataformas / Dispositivos)
         │         └── Elegir módulo
         │              └── Tarjeta: resumen + PDF + video
         │                   ├── Duda sobre el módulo → respuesta RAG → nueva duda o continuar
         │                   └── Quiz opcional (2 preguntas con feedback)
         │                        └── ¿Ver otro módulo / Volver al menú / Salir?
         │
         └── Tengo una duda
              └── 3 sugerencias clicables + campo libre
                   └── Respuesta RAG → vuelve al menú
```
