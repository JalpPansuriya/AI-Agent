# AI Customer Support & Recommendation Engine

> Production-ready AI microservice for customer support with product recommendations, real-time streaming, and admin analytics.

---

## 🔗 Live Demo

| Service | URL |
|---------|-----|
| **Backend API** | https://ai-agent-401a.onrender.com |
| **Swagger Docs** | https://ai-agent-401a.onrender.com/docs |
| **ReDoc** | https://ai-agent-401a.onrender.com/redoc |
| **Frontend App** | *(Deployed on Vercel)* |

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                          │
│               React (Vite) Frontend on Vercel                │
│       REST  ──────────────────────  WebSocket (wss://)       │
└────────────────────────┬──────────────────────┬─────────────┘
                         │                      │
             ┌───────────▼──────────────────────▼──────────┐
             │              NGINX (Reverse Proxy)           │
             │            TLS Termination + Routing         │
             └───────────────────────┬─────────────────────┘
                                     │
             ┌───────────────────────▼─────────────────────┐
             │       FastAPI Application (Uvicorn)          │
             │                                              │
             │  ┌──────────┐ ┌────────┐ ┌───────────────┐  │
             │  │  Auth API │ │Chat API│ │ WebSocket API  │  │
             │  │  /api/v1/ │ │/api/v1/│ │  /api/v1/ws/  │  │
             │  └──────────┘ └────────┘ └───────────────┘  │
             │  ┌──────────────────────────────────────┐    │
             │  │   Products │ Recommendations │ Admin  │    │
             │  └──────────────────────────────────────┘    │
             │                                              │
             │  ┌─────────────────┐  ┌──────────────────┐  │
             │  │   Middleware     │  │    Services       │  │
             │  │ Request Logging  │  │  AI / Auth /      │  │
             │  │ JWT Auth Guard   │  │  Chat / Recs      │  │
             │  │ Rate Limiting    │  │  Analytics        │  │
             │  └─────────────────┘  └──────────────────┘  │
             └────────┬──────────────────────┬──────────────┘
                      │                      │
         ┌────────────▼───┐      ┌───────────▼──────────┐
         │  PostgreSQL DB  │      │    Redis Cache        │
         │ (Supabase Prod) │      │  Rate Limiting +      │
         │ SQLAlchemy ORM  │      │  Session Store        │
         └────────────────┘      └──────────────────────┘
                      │
         ┌────────────▼───────────────┐
         │        OpenAI API          │
         │  gpt-4o-mini (streaming)   │
         │  Chat + Recommendations    │
         └────────────────────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| **Framework** | FastAPI 0.100+ (async-first) |
| **Runtime** | Python 3.11, Uvicorn (ASGI) |
| **Database** | PostgreSQL 15 via SQLAlchemy (asyncpg) |
| **Cache / Rate Limiting** | Redis 7 |
| **AI Provider** | OpenAI `gpt-4o-mini` (streaming) |
| **Auth** | JWT (access + refresh tokens, bcrypt passwords) |
| **Real-time** | WebSocket (bidirectional streaming) |
| **Background Jobs** | Celery + Redis (dev), direct DB (prod) |
| **Monitoring** | Sentry SDK, Loguru (JSON logs) |
| **Containerisation** | Docker + Docker Compose |
| **Reverse Proxy** | Nginx (Alpine) |
| **Frontend** | React 18, Vite, Axios |
| **Deployment** | Render (backend), Vercel (frontend) |

---

## ⚡ Quick Start (Docker)

```bash
# 1. Clone the repo
git clone <repo-url>
cd project

# 2. Copy and fill environment variables
cp .env.example .env
# Edit .env with your DB/Redis/OpenAI credentials

# 3. Start all services
docker-compose up --build

# 4. API is live at
# http://localhost:8000/docs
```

> **Note**: The `db` and `redis` services start automatically. The `app` container will seed 12 demo products on first startup.

---

## 🌱 Seeding Products

To populate (or repopulate) products independently of the main app startup:

```bash
docker-compose exec app python scripts/seed_products.py
```

This inserts 15 products across **Laptops**, **Phones**, and **Accessories** if the table is empty (idempotent).

---

## 🔐 Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `APP_ENV` | ✅ | — | `development` or `production` |
| `SECRET_KEY` | ✅ | — | JWT signing secret (min 32 chars) |
| `DATABASE_URL` | ✅ | — | Async PostgreSQL URL (`postgresql+asyncpg://...`) |
| `REDIS_URL` | ✅ | — | Redis connection URL |
| `OPENAI_API_KEY` | ✅ | — | OpenAI API key |
| `OPENAI_MODEL` | — | `gpt-4o-mini` | OpenAI model name |
| `OPENAI_MAX_TOKENS` | — | `1000` | Max completion tokens |
| `AI_PROVIDER` | — | `openai` | `openai`, `gemini`, or `groq` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | — | `30` | JWT access token TTL |
| `REFRESH_TOKEN_EXPIRE_DAYS` | — | `7` | JWT refresh token TTL |
| `CHAT_HISTORY_LIMIT` | — | `20` | Messages loaded as context |
| `ALLOWED_ORIGINS` | — | `*` | CORS origins (comma-separated) |
| `SENTRY_DSN` | — | — | Sentry error tracking DSN |
| `CELERY_BROKER_URL` | — | — | Celery broker (dev only) |
| `CELERY_RESULT_BACKEND` | — | — | Celery backend (dev only) |
| `GEMINI_API_KEY` | — | — | Gemini API key (if `AI_PROVIDER=gemini`) |
| `GROQ_API_KEY` | — | — | Groq API key (if `AI_PROVIDER=groq`) |

---

## 📡 API Summary

### Authentication — `/api/v1/auth`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/auth/signup` | Register a new user |
| `POST` | `/auth/login` | Authenticate and receive tokens |
| `POST` | `/auth/refresh` | Rotate access + refresh tokens |
| `POST` | `/auth/logout` | Revoke refresh token |
| `GET` | `/auth/me` | Get current authenticated user |

### Chat — `/api/v1/chat`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/chat/sessions` | Create a new chat session |
| `GET` | `/chat/sessions` | List all user sessions |
| `GET` | `/chat/sessions/{id}` | Get session with message history |
| `GET` | `/chat/sessions/{id}/messages` | List messages in a session |
| `POST` | `/chat/sessions/{id}/messages` | Send a message (REST) |
| `PUT` | `/chat/sessions/{id}` | Rename a chat session |
| `DELETE` | `/chat/sessions/{id}` | Delete a chat session |

### WebSocket — `/api/v1/ws`

| Protocol | Endpoint | Description |
|----------|----------|-------------|
| `WS` | `/ws/chat/{session_id}?token=<jwt>` | Real-time streaming chat |

### Products — `/api/v1`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/products` | List active products (optional `?category=`) |
| `POST` | `/products` | Create product (admin only) |
| `PUT` | `/products/{id}` | Update product (admin only) |
| `DELETE` | `/products/{id}` | Soft-delete product (admin only) |

### Recommendations — `/api/v1`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/recommendations` | Recommend from most recent session |
| `GET` | `/recommendations/{session_id}` | Recommend for a specific session |

### Admin — `/api/v1/admin` *(admin role required)*

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/admin/analytics` | Platform-wide stats |
| `GET` | `/admin/analytics/users` | Per-user message & token stats |
| `GET` | `/admin/analytics/tokens` | Token counts & cumulative cost |
| `GET` | `/admin/logs` | Filterable request logs |
| `GET` | `/admin/users` | All registered users |

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET/HEAD` | `/` | Basic liveness probe |
| `GET` | `/health` | Deep health check (DB + Redis) |

---

## ✅ Running Tests

```bash
# Run full test suite with coverage inside the container
docker-compose exec app env PYTHONPATH=. pytest -o asyncio_mode=auto --cov=app --cov-report=term-missing

# Run locally (requires test DB/Redis)
PYTHONPATH=. pytest -o asyncio_mode=auto
```

> Tests use `fakeredis` for Redis mocking and override the DB dependency with a fresh in-memory SQLite-compatible session.

---

## 📁 Project Structure

```
project/
├── app/
│   ├── api/v1/          # Route handlers (auth, chat, ws, products, recs, admin)
│   ├── core/            # Config, database, middleware, security, redis
│   ├── models/          # SQLAlchemy ORM models
│   ├── repositories/    # DB query layer (CRUD)
│   ├── schemas/         # Pydantic request/response schemas
│   ├── services/        # Business logic (AI, auth, chat, analytics)
│   └── workers/         # Celery tasks (dev background logging)
├── frontend/            # React + Vite frontend
├── migrations/          # Alembic migration scripts
├── nginx/               # Nginx config
├── scripts/             # Standalone utility scripts
├── tests/               # Pytest test suite
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```
