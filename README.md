# SportBot - Taekwondo Baekho

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12.3-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.116.1-green.svg" alt="FastAPI">
  <img src="https://img.shields.io/badge/React-19.1.1-aqua.svg" alt="React">
  <img src="https://img.shields.io/badge/TypeScript-5.8.3-blue.svg" alt="TypeScript">
</p>

**MVP de asistente comercial con RAG**, integrado con WhatsApp/Telegram y una interfaz web minimalista.

<details>
  <summary><b>Requerimientos del Proyecto</b></summary>

  # Requerimientos del Proyecto

  **Proyecto:** Asistente Comercial Omnicanal (Web \+ WhatsApp/Telegram)
  
  **Stack obligatorio:** Python 3.11+, FastAPI, Qdrant, Langroid, Frontend React \+ TypeScript.
  
  **Objetivo ejecutivo:** Entregar un asistente comercial que responda e interactúe como IZA, con RAG sobre base de conocimiento en Qdrant, accesible por un chat web mínimo y al menos un canal de mensajería (WhatsApp Cloud o Telegram) totalmente funcional.
  
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
  	```
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
  	```
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
  	```
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
  ```
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

Entregar un asistente comercial inteligente que:

-   Responde consultas usando RAG sobre base de conocimiento en Qdrant
-   Opera en WhatsApp Cloud API **o** Telegram Bot API
-   Incluye interfaz web mínima para pruebas
-   Proporciona panel administrativo de solo lectura

## 🏗️ Arquitectura

`Usuario ⇄ (Web/WhatsApp/Telegram) ⇄ FastAPI ⇄ Langroid Agent ⇄ Qdrant ⇄ LLM ⇄ Respuesta`

### Stack Tecnológico

**Backend:**

-   Python (3.12.3)
-   FastAPI (ASGI)
-   Qdrant (Vector Database)
-   Langroid (Agent Orchestration & RAG)
-   MySQL (Chat Persistence)

**Frontend:**

-   React 19 + TypeScript
-   Vite (Build Tool)

**IA & Embeddings:**

-   FastEmbed (`intfloat/multilingual-e5-small`) por defecto
-   OpenAI Embeddings (opcional)
-   OpenAI LLM (configurable)

## 🚀 Inicio Rápido

### Prerrequisitos

-   Python 3.12+
-   Node.js 22.19+
-   Docker & Docker Compose (recomendado)

### 1. Clonar el Repositorio

```bash
git clone https://github.com/Brayanestiv1/SportBot_backend.git
cd SportBot_backend
```

### 2. Configuración del Backend

```bash
cd backend

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
# OpenAI (requerido)
OPENAI_API_KEY=sk-...

# Embeddings
USE_OPENAI_EMBEDDINGS=false
EMBED_MODEL=intfloat/multilingual-e5-small

# Qdrant
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=company_kb

# Frontend
FRONTEND_ORIGIN=http://localhost:5174

# WhatsApp (si se elige este canal)
WHATSAPP_VERIFY_TOKEN=tu_verify_token
WHATSAPP_TOKEN=tu_access_token
WHATSAPP_PHONE_ID=tu_phone_number_id

# Telegram (si se elige este canal)
TELEGRAM_BOT_TOKEN=tu_bot_token

# Base URL pública (para webhooks)
PUBLIC_BASE_URL=https://tu-dominio.com
```

### 4. Verificar Instalación

-   **API Health:** http://localhost:8000/health
-   **Docs API:** http://localhost:8000/docs
-   **Frontend:** http://localhost:5174

## 📡 Configuración de Canales

### WhatsApp Cloud API

1.  Configurar webhook en Meta for Developers:
    
    -   URL: `https://tu-dominio.com/whatsapp/webhook`
    -   Verify Token: el valor de `WHATSAPP_VERIFY_TOKEN`
2.  Probar verificación:
    

```bash
curl "http://localhost:8000/whatsapp/webhook?hub.mode=subscribe&hub.challenge=123&hub.verify_token=tu_verify_token"
```

### Telegram Bot

1.  Configurar webhook:

```bash
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://tu-dominio.com/telegram/webhook"}'
```

2.  Verificar webhook:

```bash
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"
```

## 📊 API Endpoints

### Core

-   `POST /chat` - Chat por HTTP
-   `GET /health` - Estado del servicio
-   `GET /admin/chats` - Listado de chats (solo lectura)
-   `GET /admin/chats/{id}` - Detalle de chat

### Webhooks

-   `GET /whatsapp/webhook` - Verificación WhatsApp
-   `POST /whatsapp/webhook` - Mensajes WhatsApp
-   `POST /telegram/webhook` - Mensajes Telegram

Ver documentación completa en: http://localhost:8000/docs

## 🗂️ Estructura del Proyecto

```
SportBot_backend
├── app/
|   ├── agents/
|   |   ├── base_agents.py
|   |   └── config.py
|   ├── controllers/
|   |   ├── categoria/
|   |   |   └── CategoriaController.py
|   |   ├── chat/
|   |   |   └── ChatController.py
|   |   ├── ingest/
|   |   |   └── IngestController.py
|   |   ├── mensaje/
|   |   |   └── MensajeController.py
|   |   ├── producto/
|   |   |   └── ProductoController.py
|   |   ├── promocion/
|   |   |   └── PromocionController.py
|   |   ├── telegram/
|   |   |   └── TelegramController.py
|   |   └── usuario/
|   |       └── UsuarioController.py
|   ├── models/
|   |   ├── categoria/
|   |   |   └── CategoriaModel.py
|   |   ├── chat/
|   |   |   └── ChatModel.py
|   |   ├── ingest/
|   |   |   └── IngestModel.py
|   |   ├── mensaje/
|   |   |   └── MensajeModel.py
|   |   ├── producto/
|   |   |   └── ProductoModel.py
|   |   ├── promocion/
|   |   |   └── PromocionModel.py
|   |   ├── telegram/
|   |   |   └── TelegramModel.py
|   |   └── usuario/
|   |       └── UsuarioModel.py
|   ├── routes/
|   |   ├── categoria/
|   |   |   └── CategoriaRoutes.py
|   |   ├── chat/
|   |   |   └── ChatRoutes.py
|   |   ├── ingest/
|   |   |   └── IngestRoutes.py
|   |   ├── producto/
|   |   |   └── ProductoRoutes.py
|   |   ├── promocion/
|   |   |   └── PromocionRoutes.py
|   |   ├── telegram/
|   |   |   └── TelegramRoutes.py
|   |   └── usuario/
|   |       └── UsuarioRoutes.py
|   ├── services/
|   |   ├── agent.py
|   |   ├── data_sync.py
|   |   ├── embedding.py
|   |   ├── langroid_service.py
|   |   └── qdrant.py
|   ├── config_example.py
|   ├── config.py
|   └── database.py
├── tests/
|   ├── test_api_chats.py
|   └── test_api.py
├── main.py
└── requirements.txt
```

## 📋 Roadmap

### Fase 1 (MVP) ✅

-   [x] Chat HTTP básico
-   [x] Canal Telegram
-   [x] RAG con Qdrant
-   [x] Frontend mínimo
-   [x] Panel admin (solo lectura)

### Fase 2 (Futuro)

-   [ ] Ambos canales (Telegram + WhatsApp)
-   [ ] Subida de archivos y OCR
-   [ ] Panel admin con edición
-   [ ] Analytics avanzadas
-   [ ] Integración CRM/ERP
-   [ ] Multi-tenant
