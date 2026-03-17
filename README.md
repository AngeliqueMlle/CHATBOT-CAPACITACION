# CECOM Chatbot de Capacitación

Chatbot institucional del Centro de Comunicaciones Municipal (CECOM).
Capacita al personal municipal en las herramientas tecnológicas de su trabajo diario.

## Stack

- Python 3.10 · FastAPI · python-socketio
- LangChain · Groq llama-3.3-70b · Mistral fallback automático
- PostgreSQL · psycopg2
- HTML/JS/CSS puro (sin frameworks)

---

## Instalación

### 1. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
```

Editar `.env` con tus credenciales reales:

```env
GROQ_API_KEY=tu_api_key_de_groq
MISTRAL_API_KEY=tu_api_key_de_mistral
DB_HOST=localhost
DB_PORT=5432
DB_NAME=cecom_chatbot
DB_USER=tu_usuario_postgres
DB_PASSWORD=tu_password_postgres
```

### 3. Crear la base de datos en PostgreSQL

Ejecutar en pgAdmin o psql:

```sql
CREATE DATABASE cecom_chatbot;

\c cecom_chatbot

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

### 4. Iniciar el servidor

```bash
uvicorn main:socket_app --reload --port 8000
```

> **Nota:** El comando usa `main:socket_app`, no `main:app`.

### 5. Abrir en el navegador

```
http://localhost:8000
```

---

## Tests

```bash
pytest tests/ -v
```

---

## Estructura del proyecto

```
chatbot-capacitacion/
├── main.py          # Servidor FastAPI + SocketIO
├── chain.py         # Máquina de estados y lógica conversacional
├── database.py      # Conexión y operaciones PostgreSQL
├── modules.py       # 14 módulos de capacitación
├── quizzes.json     # 2 preguntas por módulo
├── chat.html        # Interfaz web
├── requirements.txt
├── .env.example
└── tests/
    ├── test_database.py   # 6 tests (psycopg2 mockeado)
    └── test_chain.py      # 15 tests (máquina de estados)
```

---

## Flujo del chatbot

1. Usuario ingresa su DNI (8 dígitos)
2. **Nuevo usuario** → bienvenida personalizada generada por IA
3. **Usuario existente** → muestra fecha del último acceso
4. Menú principal: **Capacitarme** / **Tengo una duda**
5. **Capacitarme** → elige categoría → módulo → tarjeta con PDF y video → quiz opcional (2 preguntas)
6. **Tengo una duda** → pregunta libre → respuesta de IA → vuelve al menú
