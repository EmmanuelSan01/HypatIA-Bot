# HypatIA Bot - DeepLearning.AI

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12.3-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.116.1-green.svg" alt="FastAPI">
  <img src="https://img.shields.io/badge/Langroid-RAG-orange.svg" alt="Langroid">
  <img src="https://img.shields.io/badge/Qdrant-Vector_DB-crimson.svg" alt="Qdrant">
</p>

**Backend de asistente comercial con RAG**, integrado con WhatsApp y sistema multi-agente inteligente.

<details>
  <summary><b>Requerimientos del Proyecto</b></summary>

  # Requerimientos del Proyecto

  **Proyecto:** Asistente Comercial Omnicanal (Web \+ WhatsApp/Telegram)
  
  **Stack obligatorio:** Python 3.11+, FastAPI, Qdrant, Langroid, Frontend React \+ TypeScript.
  
  **Objetivo ejecutivo:** Entregar un asistente comercial con RAG sobre base de conocimiento en Qdrant, accesible por un chat web mínimo y al menos un canal de mensajería (WhatsApp Cloud o Telegram) totalmente funcional.
  
  ---
  
  ## 1\. Alcance (MVP)
  
  * **Conversación asistida por IA** (LLM) con grounding vía **RAG** sobre Qdrant.
  
  * **Canal de entrada**: **uno** operativo en producción (elegir y priorizar): **WhatsApp Cloud API** **o** **Telegram Bot API**.
  
  * **Interfaz web mínima** (React \+ TS) con una vista de **chat** para pruebas.
  
  * **Panel admin (solo lectura)**: vista para **ver el listado de chats** de usuarios (web/WA/TG), sin edición ni eliminación.
  
  * **Base de conocimiento (KB)**: **definida en código** (FAQ/Docs breves en archivos de configuración). **No hay subida de archivos ni endpoints de ingestión** en el MVP.
  
  **Fuera de alcance del MVP** (posible fase 2):
  
  * Subida/gestión de archivos, OCR, panel admin con edición/moderación, analytics avanzadas, integraciones CRM/ERP, multi-tenant.
  
  ---
  
  ## 2\. Entregables
  
  1. **Repositorio** con `/backend` (FastAPI) y `/frontend` (React+TS).
  
  2. **API** con endpoints:
  
     * `POST /chat` (chat por HTTP)
  
     * `GET /health` (salud)
  
     * **Canal elegido**:
  
       * WhatsApp: `GET /whatsapp/webhook` (verificación) y `POST /whatsapp/webhook` (mensajería).
  
       * Telegram: `POST /telegram/webhook`.
  
  3. **Qdrant**: colección creada automáticamente; **KB inicial** cargada desde archivos de configuración/código.
  
  4. **Frontend**:
  
     * **Chat mínimo** (Vite \+ React \+ TS) apuntando a `/chat`.
  
     * **Panel admin (solo lectura)** con listado de chats (paginación/búsqueda simple).
  
  5. **Documentación**: README principal (arranque, .env, pruebas), diagrama lógico y este documento de requisitos.
  
  6. **Pruebas**: batería mínima de unit/integration y guía de pruebas manuales E2E.
  
  ---
  
  ## 3\. Arquitectura y Tecnologías
  
  * **Backend**: FastAPI (ASGI), Python 3.11+, cliente Qdrant, Langroid para orquestación del agente y RAG.
  
  * **Vector DB**: Qdrant, colección `company_kb`.
  
  * **Embeddings**: por defecto **FastEmbed** (`intfloat/multilingual-e5-small`), opción **OpenAI Embeddings** vía flag.
  
  * **LLM**: por defecto **OpenAI** (configurable, fácilmente reemplazable).
  
  * **Mensajería**: WhatsApp Cloud **o** Telegram (webhook). Soporte para ambos por configuración (activar uno en MVP).
  
  * **Persistencia mínima de chats**: **SQLite** por defecto (puede migrar a PostgreSQL). Solo lectura desde panel admin.
  
  * **Frontend**: React 18 \+ TypeScript, Vite.
  
  **Diagrama lógico (texto):** Usuario ⇄ (Web/WhatsApp/Telegram) ⇄ Webhook/API FastAPI ⇄ Agente (Langroid) ⇄ Recuperación (Qdrant) ⇄ LLM ⇄ Respuesta ⇄ Usuario.
  
  ---
  
  ## 4\. Requisitos Funcionales (RF)
  
  ### RF1 – Chat HTTP
  
  * **Endpoint**: `POST /chat` con `{message: string}` → `{reply: string}`.
  
  * **Función**: Responder consultas usando RAG con la colección configurada.
  
  * **Criterios de aceptación**:
  
    * Responde a preguntas frecuentes definidas en la KB del repositorio.
  
    * Devuelve HTTP 200, JSON válido, y maneja errores (400/500) con mensajes claros.
  
  ### RF2 – Webhook WhatsApp (si se elige este canal)
  
  * **Endpoints**:
  
    * `GET /whatsapp/webhook` para verificación del **verify\_token**.
  
    * `POST /whatsapp/webhook` para recibir mensajes y responder con Graph API.
  
  * **Criterios**:
  
    * Verificación correcta del webhook.
  
    * Al recibir texto, el asistente responde en la misma conversación.
  
    * Manejo de reintentos y autenticación (Bearer). Logs por cada mensaje.
  
  ### RF3 – Webhook Telegram (si se elige este canal)
  
  * **Endpoint**: `POST /telegram/webhook`.
  
  * **Criterios**:
  
    * Recepción de mensajes `text` y respuesta con `sendMessage`.
  
    * Manejo básico de comandos `/start`.
  
  ### RF4 – Panel Admin (solo lectura)
  
  * **Vista**: listado de **chats de usuarios** (web/WA/TG).
  
  * **Campos mínimos**: `user_id/numero/chat_id`, `canal`, `último mensaje`, `actualizado_en`, `total_mensajes`.
  
  * **Funciones**: paginación, búsqueda por `user/id`/número, filtro por canal.
  
  * **Restricciones**: sin crear/editar/eliminar; solo lectura.
  
  ### RF5 – KB y Recuperación
  
  * **Función**: Buscar k-chunks relevantes (k configurable) en Qdrant y llevarlos al contexto del LLM.
  
  * **Criterios**:
  
    * Top-k por similitud (cosine), tamaño de vector según modelo.
  
    * Parámetros (`top_k`, `score_threshold`) en config.
  
  ### RF6 – Sesión y Contexto
  
  * **Función**: Mantener contexto corto por sesión (ID web / número WA / chat\_id TG) en memoria de proceso.
  
  * **Criterios**:
  
    * Máximo N turnos recientes (configurable) para reducir latencia y costo.
  
  ### RF7 – Prompting del Agente
  
  * **Función**: System prompt con identidad comercial, tono cordial colombiano, y reglas de conversación.
  
  * **Criterios**:
  
    * Presentación breve, resolución orientada a ventas/soporte.
  
    * Preguntas aclaratorias cuando falte info. Evitar alucinaciones.
  
  ### RF8 – Frontend mínimo
  
  * **Función**: UI simple con caja de texto y mensajes; vista adicional de **panel admin (solo lectura)** para listado de chats.
  
  * **Criterios**:
  
    * Funciona localmente con Vite y CORS habilitado.
  
  ---
  
  ## 5\. Requisitos No Funcionales (RNF)
  
  * **Rendimiento**: p95 \< 2.5 s (HTTP) con contexto corto; p95 \< 5 s en canales.
  
  * **Escalabilidad**: Stateless en API; estado conversacional efímero. Listo para contenedores.
  
  * **Disponibilidad**: 99% en demo; manejo de errores y timeouts con reintentos limitados.
  
  * **Seguridad**: Variables sensibles en `.env`; verificación webhook; CORS, rate limit básico (si es factible), sanitización de inputs.
  
  * **Observabilidad**: Logs JSON estructurados; trazas opcionales (OpenTelemetry) y métricas básicas (contadores por canal/errores).
  
  * **Calidad**: Tipado estricto (mypy opcional), lint (ruff), formateo (black), tests con pytest.
  
  ---
  
  ## 6\. Modelo de Datos (Qdrant)
  
  * **Colección**: `company_kb`
  
  * **Vector**: tamaño 384 (FastEmbed por defecto) o 1536+ (OpenAI) según configuración.
  
  * **Payload sugerido**:
  	```json
  	{
  	   "text": "string",
  	   "source": "faq|doc|pdf|web",
  	   "title": "string",
  	   "lang": "es",
  	   "tags": ["ventas","politicas"],
  	   "created_at": "ISO-8601"
  	}
  	```
  ---
  
  ## 7\. Contratos de API
  
  ### `POST /chat`
  
  * **Request**: `{ "message": "string" }`.
  
  * **Response 200**: `{ "reply": "string" }`.
  
  * **Errores**: 400 (input inválido), 500 (server error).
  
  ### `GET /whatsapp/webhook` (opcional)
  
  * **Query**: `hub.mode`, `hub.verify_token`, `hub.challenge`.
  
  * **Response 200**: `hub.challenge` (número).
  
  ### `POST /whatsapp/webhook` (opcional)
  
  * **Body**: payload de Graph API (Meta) con mensajes `text`.
  
  * **Response 200**: `{ "status": "sent" }`.
  
  ### `POST /telegram/webhook` (opcional)
  
  * **Body**: update con `message.text`.
  
  * **Response 200**: `{ "status": "sent" }`.
  
  ### `GET /admin/chats`
  
  * **Query**: `page`, `limit`, `search`, `channel?=web|wa|tg`.
  
  * **Response 200**:
  	```json
  	{
  	  "items": [
  	    {
  	      "user_id": "...",
  	      "channel": "wa",
  	      "last_message": "...",
  	      "updated_at": "...",
  	      "count": 3
  	    }
  	  ],
  	  "page": 1,
  	  "total": 23
  	}
  	```
  
  ### `GET /admin/chats/{id}`
  
  * **Response 200**:
  	```json
  	{
  	  "user_id": "...",
  	  "channel": "wa",
  	  "messages": [
  	    {
  	      "role": "user|assistant",
  	      "text": "...",
  	      "ts": "..."
  	    }
  	  ]
  	}
  	```
  
  ### `GET /health`
  
  * **Response 200**: `{ "status": "ok" }`.
  
  ---
  
  ## 8\. Configuración y Variables de Entorno
  ```env
  OPENAI_API_KEY=
  USE_OPENAI_EMBEDDINGS=false
  QDRANT_URL=http://qdrant:6333
  QDRANT_COLLECTION=company_kb
  EMBED_MODEL=intfloat/multilingual-e5-small
  FRONTEND_ORIGIN=http://localhost:5173
  # WhatsApp
  WHATSAPP_VERIFY_TOKEN=
  WHATSAPP_TOKEN=
  WHATSAPP_PHONE_ID=
  # Telegram
  TELEGRAM_BOT_TOKEN=
  PUBLIC_BASE_URL=
  ```
  ---
  
  ## 9\. Flujo Conversacional (Lineamientos)
  
  * **Rol**: Asistente comercial (presentación breve, útil, sin divagar, tono profesional cercano colombiano).
  
  * **Comportamiento**: preguntar para aclarar; usar información recuperada; si no hay evidencia, responder con transparencia y proponer alternativas.
  
  * **Desescalado**: si el usuario pide contacto humano, entregar instrucciones o correo genérico (configurable).
  
  **Prompt base (borrador):**
  
  * **Identidad**: asistente comercial de la empresa.
  
  * **Estilo**: claro, conciso, orientado a resolver y vender sin presionar.
  
  * **Reglas**: no inventar datos; basarse en KB; solicitar contexto faltante; español neutro Colombia.
  
  ---
  
  ## 10\. Estrategia de Pruebas
  
  * **Unitarias**: servicios de embeddings, Qdrant, formateo de prompts, validación de payloads.
  
  * **Integración**: `/chat` con Qdrant stub; webhooks con payloads reales de ejemplo (fixtures).
  
  * **E2E manual**: flujo completo en canal elegido \+ web.
  
  **Casos clave (mínimos):**
  
  ---
  
  **WBS resumido**
  
  1. Backend base (API, config, health)
  
  2. Qdrant \+ embeddings (KB en código)
  
  3. Agente Langroid \+ RAG
  
  4. Canal (WA o TG) webhook \+ envío de mensajes
  
  5. Front chat mínimo \+ **panel admin** (solo lectura)
  
  6. Pruebas (unit/integration/E2E)
  
  7. Observabilidad (logs), hardening básico
  
  8. Documentación y demo
  
  ---
  
  ## 12\. Definition of Done (DoD)
  
  **Backend**
  
  **Qdrant/RAG**
  
  **Canal (elegido)**
  
  **Frontend**
  
  **Calidad**
  
  **Entrega**
  
  ---
  
  ## 13\. Riesgos y Mitigación
  
  * **Latencia del LLM**: usar modelo económico/rápido y contexto breve; caché opcional.
  
  * **Cambios de API (WA/TG)**: abstraer cliente y centralizar configuración.
  
  * **Datos pobres en KB**: exigir ingesta mínima de FAQs/Docs antes de demo.
  
  * **Costo**: limitar tokens; logs de consumo.
  
  ---
  
  ## 15\. Estructura de Repositorio (sugerida)
  ```
  assist-mvp/  
  ├─ backend/  
  │  ├─ app/  
  │  │  ├─ main.py  
  │  │  ├─ config.py  
  │  │  ├─ routers/ (chat.py, whatsapp.py, telegram.py, ingest.py)  
  │  │  ├─ services/ (agent, qdrant, embeddings)  
  │  │  └─ models/  
  │  ├─ tests/  
  │  ├─ requirements.txt  
  │  └─ README.md  
  ├─ frontend/  
  │  ├─ src/ (App.tsx, main.tsx)  
  │  ├─ vite.config.ts  
  │  └─ package.json  
  ├─ docker-compose.yml  
  └─ README.md
  ```
  ---
  
  ## 16\. Notas Finales
  
  * “Langroid” se usará como nombre de la librería de agentes.
  
  * El equipo debe priorizar **WhatsApp** o **Telegram** primero, y dejar parametrizado el segundo para fase posterior.
  
  * Mantener el tono y guía de conversación orientados a un asistente comercial que **responde, guía y no inventa**.

---
</details>

## 🎯 Objetivo

Backend que proporciona:

- API REST con FastAPI para asistente comercial inteligente
- Sistema RAG (Retrieval-Augmented Generation) sobre base de conocimiento en Qdrant
- Integración con WhatsApp Cloud API y Telegram Bot API
- Sistema multi-agente con Langroid para coordinación de tareas especializadas
- CRUD completo para gestión de cursos, categorías y promociones

## 🏗️ Arquitectura

<div align="center">
  <strong>Usuario ⇄ WhatsApp ⇄ FastAPI ⇄ Langroid Agent ⇄ Qdrant ⇄ LLM ⇄ Respuesta</strong>
</div>

### Sistema Multi-Agente (Langroid)

#### `MainHypatiaAgent`
- **Función**: Orquestador principal del sistema
- **Responsabilidades**: Coordina la interacción entre agentes especializados

#### `KnowledgeAgent`
- **Función**: Búsqueda y recuperación de conocimiento
- **Herramientas**: `CourseSearchTool`, `PromotionSearchTool`
- **Capacidades**: Búsqueda semántica en catálogo de cursos

#### `SalesAgent`
- **Función**: Recomendaciones de ventas y validación
- **Herramientas**: `PhoneValidationTool`
- **Capacidades**: Validación de números telefónicos colombianos

#### `AnalyticsAgent`
- **Función**: Análisis de conversaciones
- **Capacidades**: Métricas de interacción, análisis de comportamiento

### Stack Tecnológico
- Python (3.12.3)
- FastAPI (ASGI)
- Qdrant (Vector Database)
- Langroid (Agent Orchestration & RAG)
- MySQL (Chat Persistence)
- FastEmbed (`intfloat/multilingual-e5-small`) por defecto
- OpenAI Embeddings (opcional)
- OpenAI LLM (configurable)

## 🚀 Inicio Rápido

### Prerrequisitos

- Python 3.12+
- MySQL 8.0+

### 1. Clonar el Repositorio

```bash
git clone https://github.com/EmmanuelSan01/HypatIA-Bot.git
cd HypatIA-Bot
```

### 2. Configuración del Entorno

```bash
# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
```

### 3. Variables de Entorno

Edita el archivo `.env`:

```env
# Database Configuration
DB_HOST=
DB_PORT=
DB_USER=
DB_PASSWORD=
DB_NAME=
CA_PATH=

# Qdrant Configuration
QDRANT_URL=
QDRANT_PORT=
QDRANT_API_KEY=
QDRANT_COLLECTION_NAME=
VECTOR_SIZE=

# WhatsApp API
APP_ID=
APP_SECRET=
ACCESS_TOKEN=
PHONE_ID=
VERIFY_TOKEN=
WEBHOOK=

# Redis Configuration
REDIS_HOST=
REDIS_PORT=
REDIS_PASSWORD=

# AI API Key
OPENAI_API_KEY=

# Basic settings
DEBUG=True
SECRET_KEY=

# Server configuration
HOST=0.0.0.0
PORT=8000
```

### 4. Verificar Instalación

- **API Health:** http://localhost:8000/health
- **Documentación:** http://localhost:8000/docs

## 📡 Configuración de Canales

### WhatsApp Cloud API

1. Configurar webhook en Meta for Developers:
  - URL: `https://tu-dominio.com/whatsapp/webhook`
  - Verify Token: valor de `WHATSAPP_VERIFY_TOKEN`

2. Probar verificación:  
```bash
curl "http://localhost:8000/whatsapp/webhook?hub.mode=subscribe&hub.challenge=123&hub.verify_token=tu_verify_token"
```

## 📊 API Endpoints

### Core

- `POST /chat` - Chat por HTTP
- `GET /health` - Estado del servicio
- `GET /admin/chats` - Listado de chats (solo lectura)
- `GET /admin/chats/{id}` - Detalle de chat

### Webhooks

- `GET /whatsapp/webhook` - Verificación WhatsApp
- `POST /whatsapp/webhook` - Mensajes WhatsApp
- `POST /telegram/webhook` - Mensajes Telegram

Ver documentación completa en: http://localhost:8000/docs

## 🗂️ Estructura del Proyecto

<details>
  <summary><b>Estructura de carpetas</b></summary>
  <pre><code>
HypatIA-Bot
├── app/
|   ├── agents/                        # Sistema Multi-Agente Langroid
|   |   ├── base_agents.py             # Implementación de agentes IA
|   |   └── config.py                  # Configuración y prompts de agentes
|   ├── controllers/                   # Lógica de negocio
|   |   ├── categoria/
|   |   |   └── CategoriaController.py 
|   |   ├── chat/
|   |   |   └── ChatController.py      # Controlador principal del chat
|   |   ├── ingest/
|   |   |   └── IngestController.py    # Ingesta de datos para RAG
|   |   ├── mensaje/
|   |   |   └── MensajeController.py
|   |   ├── curso/
|   |   |   └── CursoController.py
|   |   ├── promocion/
|   |   |   └── PromocionController.py
|   |   ├── telegram/
|   |   |   └── TelegramController.py
|   |   └── usuario/
|   |       └── UsuarioController.py
|   ├── models/                        # Modelos de datos Pydantic
|   |   ├── categoria/
|   |   |   └── CategoriaModel.py
|   |   ├── chat/
|   |   |   └── ChatModel.py
|   |   ├── ingest/
|   |   |   └── IngestModel.py
|   |   ├── mensaje/
|   |   |   └── MensajeModel.py
|   |   ├── curso/
|   |   |   └── CursoModel.py
|   |   ├── promocion/
|   |   |   └── PromocionModel.py
|   |   ├── telegram/
|   |   |   └── TelegramModel.py
|   |   └── usuario/
|   |       └── UsuarioModel.py
|   ├── routes/                        # Endpoints de la API
|   |   ├── categoria/
|   |   |   └── CategoriaRoutes.py
|   |   ├── chat/
|   |   |   └── ChatRoutes.py
|   |   ├── ingest/
|   |   |   └── IngestRoutes.py
|   |   ├── curso/
|   |   |   └── CursoRoutes.py
|   |   ├── promocion/
|   |   |   └── PromocionRoutes.py
|   |   ├── telegram/
|   |   |   └── TelegramRoutes.py
|   |   └── usuario/
|   |       └── UsuarioRoutes.py
|   ├── services/                      # Servicios principales
|   |   ├── agent.py                   # Servicio legacy (reemplazado)
|   |   ├── data_sync.py               # Sincronización de datos RAG
|   |   ├── embedding.py               # Servicio de embeddings
|   |   ├── langroid_service.py        # Servicio principal Langroid
|   |   └── qdrant.py                  # Servicio Vector Database
|   ├── config.py                      # Configuración unificada (Docker/Local)
|   └── database.py                    # Gestión de conexiones MySQL
├── main.py                            # Punto de entrada de la aplicación FastAPI
└── requirements.txt                   # Dependencias del proyecto
  </code></pre>
</details>

## 🔧 Componentes Clave

### 1. **main.py**
Punto de entrada de la aplicación FastAPI con:
- Configuración de rutas y middleware
- Inicialización de servicios
- Configuración CORS y documentación automática

### 2. **app/config.py**
Gestión unificada de configuración:
- Compatibilidad Docker/Local
- Variables de entorno
- Configuración de base de datos y servicios IA

### 3. **app/database.py**
Gestión de conexiones MySQL:
- Pool de conexiones asíncronas
- Manejo de transacciones
- Configuración aiomysql/PyMySQL

### 4. **app/services/langroid_service.py**
Servicio principal de IA:
- Integración del sistema multi-agente
- Procesamiento de consultas conversacionales
- Coordinación de herramientas especializadas

### 5. **app/controllers/chat/ChatController.py**
Controlador principal del chat:
- Integración con agentes Langroid
- Persistencia de conversaciones
- Manejo de contexto y historial

## 📋 Esquema de Base de Datos

### Tablas Principales
- **`categoria`**: Categorías de cursos
- **`curso`**: Catálogo con precios e inventario
- **`promocion`**: Promociones y descuentos activos
- **`usuario`**: Perfiles con números telefónicos
- **`chat`**: Sesiones de conversación
- **`mensaje`**: Mensajes individuales (usuario/bot)

### Relaciones
```sql
categoria (1) ←→ (N) curso
promocion (N) ←→ (N) curso
usuario (1) ←→ (N) chat
chat (1) ←→ (N) mensaje
```

## 🚀 Características Principales

1. **Sistema Multi-Agente Inteligente**: Framework Langroid con agentes especializados
2. **RAG Implementado**: Búsqueda semántica con Qdrant Vector Database
3. **CRUD Completo**: Gestión de cursos, categorías, promociones y usuarios
4. **Sistema de Chat Persistente**: Historial de conversaciones y análisis
5. **Integración Telegram**: Soporte para webhook de bot
6. **Validación Telefónica**: Validación y almacenamiento de números colombianos
7. **Sincronización de Datos**: Actualización automática de base de conocimiento
8. **Soporte Docker**: Configuración lista para contenedores

## 📋 Roadmap

### Fase 1 (MVP) ✅
- [x] Sistema multi-agente Langroid
- [x] RAG con Qdrant
- [x] CRUD completo
- [x] Integración WhatsApp
- [x] API REST completa
- [x] WebSocket para chat en tiempo real
- [x] Cache con Redis

### Fase 2 (Futuro)
- [ ] Subida de archivos y OCR
- [ ] Panel admin con edición
- [ ] Analytics avanzadas
- [ ] Integración CRM/ERP
- [ ] Multi-tenant
