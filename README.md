# CECOM-BOT

Chatbot de capacitación para el personal de la Central de Comunicación y Videovigilancia (CECOM) de la Municipalidad de San Juan de Lurigancho. El chatbot Enseña a usar las plataformas y dispositivos que suele manejar diariamente, responde dudas sobre los manuales y toma un quiz corto al final de cada módulo.

El personal trabaja con 12 plataformas y dispositivos distintos, y la capacitación dependía de que alguien con experiencia se sentara al lado del nuevo a explicarle. Los manuales existían en PDF pero nadie los leía completos, y si querías saber una cosa puntual tenías que buscarla tú mismo. La idea fue que cada quien pueda capacitarse a su ritmo y preguntar lo que no entiende sin depender de que haya alguien disponible.

## Qué hace

Entras con tu DNI y eliges una categoría (plataforma o dispositivo) , y de ahí el módulo que quieras. Cada módulo abre con un resumen, el PDF y el video si tuviera.

Si tienes una duda la escribes y el bot responde usando solo el contenido de ese manual, no inventa. Recuerda el hilo de la conversación mientras no cierres el chat. Al final puedes dar un quiz de dos preguntas con feedback por cada respuesta.

Todo queda registrado por DNI: qué módulo vio, de qué categoría, cuándo y qué sacó en el quiz. Puedes navegar por botones o escribiendo, como prefieras.

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
```

## Cómo funciona

El backend es FastAPI con Socket.IO para el chat en tiempo real. La conversación está armada como máquina de estados en `chain.py`.

Los manuales en PDF se procesan con Claude Vision, se parten en chunks y se guardan como embeddings en PostgreSQL con pgvector. Cuando alguien pregunta algo, se busca en los chunks de ese módulo y la respuesta sale de ahí. El modelo es llama-3.3-70b por Groq, con Mistral de respaldo si falla.

Hay tests para la máquina de estados, las operaciones de base de datos y el RAG.

**Stack:** Python, FastAPI, Socket.IO, LangChain, PostgreSQL, pgvector, HuggingFace embeddings, HTML/CSS/JS.

## Instalar

Necesitas Python 3.10+, PostgreSQL con la extensión pgvector, y Poppler en el PATH para procesar los PDFs (`pdftoppm -v` para verificar).

```bash
pip install -r requirements.txt
cp .env.example .env
```

En `.env` van las llaves de Groq, Mistral y Anthropic, más los datos de conexión a Postgres.

Crear la base y las tablas:

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

Levantar el servidor:

```bash
uvicorn main:socket_app --reload --port 8000
```

Entra en `http://localhost:8000`.

## Agregar un módulo

La carpeta `static/modulos/{slug}` no está en el repo, así que primero hay que crearla:
