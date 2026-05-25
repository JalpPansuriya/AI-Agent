# AI Agent Execution Plan
## AI Customer Support & Recommendation Engine

> **How to use this file:** Execute each phase in order. Complete ALL tasks in a phase before moving to the next. Each task includes exact commands, files to create, and what "done" looks like.

---

## PHASE 1 — Project Scaffold & Docker Setup
**Goal:** Running containers, folder structure in place, nothing else.

### Step 1.1 — Create folder structure
```
mkdir -p app/api/v1 app/core app/services app/repositories app/models app/schemas app/workers
mkdir -p migrations/versions tests frontend/src nginx .github/workflows
touch app/__init__.py app/api/__init__.py app/api/v1/__init__.py
touch app/core/__init__.py app/services/__init__.py app/repositories/__init__.py
touch app/models/__init__.py app/schemas/__init__.py app/workers/__init__.py
```

### Step 1.2 — Create `requirements.txt`
Include:
- fastapi, uvicorn[standard], pydantic[email] (v2)
- sqlalchemy[asyncio], asyncpg, alembic
- python-jose[cryptography], passlib[bcrypt]
- openai, tenacity
- celery[redis], redis
- loguru, sentry-sdk
- httpx, pytest, pytest-asyncio
- ruff, python-dotenv

### Step 1.3 — Create `.env.example`
Copy all variables from Section 11 of the PRD. Do not fill real values.

### Step 1.4 — Create `Dockerfile`
- Base: `python:3.12-slim`
- Copy `requirements.txt`, run `pip install`
- Copy `app/` directory
- Default CMD: `uvicorn app.main:app --host 0.0.0.0 --port 8000`

### Step 1.5 — Create `docker-compose.yml` (local dev)
Services: `app`, `worker`, `nginx`, `db` (postgres:15), `redis` (redis:7-alpine)
- `app` depends on `db` and `redis`
- `worker` uses same image, entrypoint: `celery -A app.workers.celery_app worker`
- Mount `.env` file into both `app` and `worker`

### Step 1.6 — Create `nginx/nginx.conf`
- Reverse proxy to `app:8000`
- Listen on port 80 (HTTPS added later in production)

### Step 1.7 — Create `app/main.py` (skeleton only)
```python
from fastapi import FastAPI
app = FastAPI(title="AI Support Engine")

@app.get("/health")
async def health():
    return {"status": "healthy"}
```

### ✅ Phase 1 Done When:
```bash
docker-compose up --build
curl http://localhost:8000/health  # returns {"status": "healthy"}
```

---

## PHASE 2 — Configuration & Database Setup
**Goal:** PostgreSQL connected, all 6 tables created via Alembic.

### Step 2.1 — Create `app/core/config.py`
- Use `pydantic_settings.BaseSettings`
- Load all variables from `.env.example`
- Fields: `DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`, `OPENAI_API_KEY`, `OPENAI_MODEL`, `CHAT_HISTORY_LIMIT`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`, `RATE_LIMIT_CHAT`, `RATE_LIMIT_AUTH`, `ALLOWED_ORIGINS`, `SENTRY_DSN`

### Step 2.2 — Create `app/models/models.py`
Define all 6 SQLAlchemy async models exactly as in PRD Section 5:
- `User` — id, email, hashed_password, full_name, role, is_active, timestamps
- `Session` — id, user_id (FK→users), title, timestamps
- `Message` — id, session_id (FK→sessions), role, content, token fields, created_at
- `Product` — id, name, description, category, tags (ARRAY), price, is_active, created_at
- `RequestLog` — id, request_id, user_id, endpoint, method, status_code, duration_ms, tokens_used, error_message, created_at
- `RefreshToken` — id, user_id (FK→users), token, expires_at, is_revoked, created_at

### Step 2.3 — Set up Alembic
```bash
alembic init migrations
# Edit migrations/env.py to use async engine and import models
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

### Step 2.4 — Create async DB engine in `app/core/config.py` or `app/core/database.py`
- `create_async_engine(DATABASE_URL)`
- `AsyncSessionLocal` sessionmaker
- `get_db` dependency that yields a session

### Step 2.5 — Update `/health` endpoint
```python
@app.get("/health")
async def health(db=Depends(get_db)):
    # test DB query
    # test Redis ping
    return {"status": "healthy", "db": "connected", "redis": "connected"}
```

### ✅ Phase 2 Done When:
```bash
docker-compose exec app alembic upgrade head  # no errors
curl http://localhost:8000/health             # db and redis both "connected"
```

---

## PHASE 3 — Authentication System
**Goal:** Full JWT auth working. Users can sign up, log in, refresh, and logout.

### Step 3.1 — Create `app/core/security.py`
Functions:
- `hash_password(plain: str) -> str` — bcrypt, work factor 12
- `verify_password(plain: str, hashed: str) -> bool`
- `create_access_token(data: dict) -> str` — JWT, 30 min expiry
- `create_refresh_token() -> str` — opaque UUID
- `decode_access_token(token: str) -> dict` — raises on invalid/expired

### Step 3.2 — Create `app/schemas/auth.py`
Pydantic models:
- `SignupRequest` — email (validated), password (min 8, 1 uppercase, 1 number), full_name
- `LoginRequest` — email, password
- `TokenResponse` — access_token, refresh_token, token_type
- `UserResponse` — id, email, full_name, role, created_at
- `RefreshRequest` — refresh_token

### Step 3.3 — Create `app/repositories/user_repo.py`
Functions:
- `get_by_email(db, email) -> User | None`
- `get_by_id(db, user_id) -> User | None`
- `create_user(db, email, hashed_password, full_name) -> User`
- `create_refresh_token(db, user_id, token, expires_at) -> RefreshToken`
- `get_refresh_token(db, token) -> RefreshToken | None`
- `revoke_refresh_token(db, token_id)`

### Step 3.4 — Create `app/services/auth_service.py`
Functions:
- `signup(db, request: SignupRequest) -> UserResponse`
  - Check duplicate email → 409
  - Hash password
  - Insert user
- `login(db, request: LoginRequest) -> TokenResponse`
  - Fetch user → 401 if not found
  - Verify password → 401 if mismatch
  - Create access + refresh tokens
- `refresh(db, refresh_token: str) -> TokenResponse`
  - Lookup token, check revoked + expiry → 401
  - Issue new access token, rotate refresh token
- `logout(db, refresh_token: str)`
  - Revoke the refresh token

### Step 3.5 — Create `app/core/dependencies.py`
- `get_current_user` — extracts Bearer token, decodes JWT, fetches user, checks is_active → 401 if any step fails
- `get_current_admin` — calls `get_current_user` then checks `role == 'admin'` → 403 if not

### Step 3.6 — Create `app/api/v1/auth.py`
Register routes:
- `POST /auth/signup` → 201
- `POST /auth/login` → 200
- `POST /auth/refresh` → 200
- `POST /auth/logout` → 204
- `GET /auth/me` → 200 (protected)

### Step 3.7 — Register router in `app/main.py`
```python
from app.api.v1 import auth
app.include_router(auth.router, prefix="/api/v1")
```

### Step 3.8 — Write `tests/test_auth.py`
Test cases:
- Signup success → 201
- Signup duplicate email → 409
- Signup weak password → 422
- Login success → tokens returned
- Login wrong password → 401
- Refresh token rotation works
- Protected route with no token → 401
- Protected route with valid token → 200

### ✅ Phase 3 Done When:
```bash
pytest tests/test_auth.py  # all pass
```

---

## PHASE 4 — Chat Sessions & Message Storage
**Goal:** Users can create sessions, send messages (no AI yet), retrieve history.

### Step 4.1 — Create `app/schemas/chat.py`
- `SessionCreate` — title (optional)
- `SessionResponse` — id, user_id, title, created_at
- `MessageCreate` — content
- `MessageResponse` — id, session_id, role, content, token fields, created_at

### Step 4.2 — Create `app/repositories/session_repo.py`
- `create_session(db, user_id, title) -> Session`
- `get_sessions_by_user(db, user_id) -> list[Session]`
- `get_session(db, session_id, user_id) -> Session | None` — user-scoped, returns None if not owner
- `delete_session(db, session_id, user_id)`

### Step 4.3 — Create `app/repositories/message_repo.py`
- `save_message(db, session_id, role, content, tokens) -> Message`
- `get_messages(db, session_id, limit) -> list[Message]` — ordered by created_at ASC

### Step 4.4 — Create `app/services/chat_service.py` (stub, no AI yet)
- `create_session(db, user_id, title)`
- `list_sessions(db, user_id)`
- `get_session_with_history(db, session_id, user_id)` — returns session + messages, 403 if not owner
- `delete_session(db, session_id, user_id)`
- `send_message(db, session_id, user_id, content)` — saves user message, returns placeholder assistant message for now

### Step 4.5 — Create `app/api/v1/chat.py`
Register routes:
- `POST /chat/sessions`
- `GET /chat/sessions`
- `GET /chat/sessions/{session_id}`
- `DELETE /chat/sessions/{session_id}`
- `POST /chat/sessions/{session_id}/messages`

### Step 4.6 — Write `tests/test_chat.py`
- Create session → 201
- List sessions → only own sessions returned
- Access another user's session → 403
- Send message → stored in DB
- History returns messages in order

### ✅ Phase 4 Done When:
```bash
pytest tests/test_chat.py  # all pass
```

---

## PHASE 5 — AI Orchestrator (OpenAI Integration)
**Goal:** Real AI responses with retry, streaming, and prompt injection guard.

### Step 5.1 — Create `app/services/ai_service.py`

**Prompt guard function:**
```python
INJECTION_PATTERNS = [
    "ignore previous instructions",
    "you are now",
    "pretend you are",
    "forget everything",
    "system prompt",
    "as an ai with no restrictions",
]
def check_prompt_injection(content: str) -> bool:
    # returns True if injection detected
```

**AI orchestrator function:**
```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    retry=retry_if_exception_type((RateLimitError, APITimeoutError, APIConnectionError))
)
async def call_openai(messages: list[dict]) -> tuple[str, dict]:
    # returns (response_text, token_usage)
```

**Streaming function:**
```python
async def stream_openai(messages: list[dict]) -> AsyncGenerator[str, None]:
    # yields chunks
```

### Step 5.2 — Update `app/services/chat_service.py`
Replace placeholder in `send_message`:
1. Load last `CHAT_HISTORY_LIMIT` messages from DB
2. Run prompt guard → raise `400` if injection detected
3. Check Redis cache: key = `SHA256(system_prompt + last 5 messages)`
4. On cache miss → call `ai_service.call_openai()`
5. On cache hit → return cached response
6. Save AI response + token counts to DB
7. Set cache with 1-hour TTL
8. Return full `MessageResponse` with token data

### Step 5.3 — Create `app/api/v1/websocket.py`
```python
@router.websocket("/ws/chat/{session_id}")
async def websocket_chat(websocket, session_id, token: str = Query(...)):
    # 1. Authenticate token from query param
    # 2. Accept connection
    # 3. Loop: receive JSON → stream OpenAI chunks → send {"chunk": "..."}
    # 4. On completion send {"done": true, "total_tokens": N}
```

### Step 5.4 — Write `tests/test_chat.py` (add AI tests)
Mock OpenAI using `unittest.mock.AsyncMock`:
- Message triggers AI call → response saved
- Prompt injection detected → 400 returned
- OpenAI fails → retry fires → success on 3rd attempt
- Cache hit → OpenAI not called second time

### ✅ Phase 5 Done When:
```bash
pytest tests/test_chat.py  # all pass including AI tests
# Manual: send a real message, get a real AI response
```

---

## PHASE 6 — Rate Limiting & Token Tracking
**Goal:** Redis rate limiting active, token usage recorded in request_logs.

### Step 6.1 — Create `app/services/rate_limiter.py`
Sliding window implementation:
```python
async def check_rate_limit(redis_client, key: str, limit: int, window_seconds: int = 60):
    # Uses Redis INCR + EXPIRE
    # Returns (is_allowed: bool, remaining: int, reset_timestamp: int)
```

### Step 6.2 — Create `app/core/middleware.py`

**Request ID middleware:**
```python
# On every request:
# 1. Generate UUID → store in request.state.request_id
# 2. Record start time in request.state.start_time
# 3. On response: add X-Request-ID header
```

**Rate limit middleware (or dependency):**
```python
# Check rate limit per endpoint group per user/IP
# On exceed: return 429 with headers:
#   X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset
```

### Step 6.3 — Add rate limiting to routes
- Auth routes: 10/min per IP
- Chat message route: 30/min per user
- Recommendation routes: 20/min per user
- Admin routes: 60/min per user

### Step 6.4 — Create `app/repositories/log_repo.py`
```python
async def create_request_log(db, request_id, user_id, endpoint, method, status_code, duration_ms, tokens_used, error_message)
```

### Step 6.5 — Write `tests/test_rate_limiter.py`
- 30 requests → all succeed
- 31st request → 429 returned
- `X-RateLimit-Remaining` decrements correctly
- `retry_after` in response body is accurate

### ✅ Phase 6 Done When:
```bash
pytest tests/test_rate_limiter.py  # all pass
```

---

## PHASE 7 — Recommendation Engine
**Goal:** Product recommendations automatically returned with every AI response.

### Step 7.1 — Create `app/repositories/product_repo.py`
```python
async def get_products_by_interests(db, interests: list[str], limit=5) -> list[Product]
# Query: WHERE tags && ARRAY[interests] OR category = ANY(interests)
# Ordered by relevance

async def get_recent_products(db, limit=5) -> list[Product]
# Fallback: 5 most recent active products
```

### Step 7.2 — Create `app/services/recommendation_service.py`
```python
async def get_recommendations(db, session_id: str, user_id: str) -> list[Product]:
    # 1. Load last 5 user messages from session
    # 2. Send to OpenAI with extraction prompt:
    #    "Extract top 3 product categories or products the user is interested in.
    #     Return ONLY JSON: { 'interests': ['cat1', 'cat2', 'product_name'] }"
    # 3. Parse JSON response
    # 4. Query products table with interests
    # 5. If empty/error → fallback to recent products
```

### Step 7.3 — Create `app/schemas/recommendation.py`
- `RecommendationResponse` — list of products with id, name, category, price

### Step 7.4 — Create `app/api/v1/recommendations.py`
- `GET /recommendations` — uses most recent session
- `GET /recommendations/{session_id}` — specific session

### Step 7.5 — Update chat message response
Attach recommendations to `MessageResponse` after every AI reply (call recommendation_service inline or via background task).

### Step 7.6 — Seed test products in DB
Create a migration or seed script with 10–20 products across categories (laptops, phones, accessories, etc.) for testing.

### Step 7.7 — Write `tests/test_recommendations.py`
- Recommendation returns products matching conversation context
- Empty DB → fallback to recent products
- Invalid session → 403

### ✅ Phase 7 Done When:
```bash
pytest tests/test_recommendations.py  # all pass
# Manual: chat about laptops → recommendations contain laptop products
```

---

## PHASE 8 — Celery Background Tasks & Structured Logging
**Goal:** Non-blocking logging, scheduled tasks, Loguru JSON logs.

### Step 8.1 — Create `app/workers/celery_app.py`
```python
from celery import Celery
celery_app = Celery("worker", broker=settings.CELERY_BROKER_URL, backend=settings.CELERY_RESULT_BACKEND)
celery_app.conf.timezone = "UTC"
# Register beat schedule for aggregate_daily_stats and cleanup_expired_tokens
```

### Step 8.2 — Create `app/workers/tasks.py`
Three tasks:

**`log_request`** (called after every response):
```python
@celery_app.task
def log_request(request_id, user_id, endpoint, method, status_code, duration_ms, tokens_used, error_message):
    # Write to request_logs table
```

**`aggregate_daily_stats`** (daily via Celery Beat):
```python
@celery_app.task
def aggregate_daily_stats():
    # Compute per-user token totals for yesterday
    # Store in aggregates table (or update users table)
```

**`cleanup_expired_tokens`** (hourly via Celery Beat):
```python
@celery_app.task
def cleanup_expired_tokens():
    # DELETE FROM refresh_tokens WHERE is_revoked=true OR expires_at < now()
```

### Step 8.3 — Fire `log_request` after every API response
In `app/core/middleware.py` response handler:
```python
log_request.delay(request_id, user_id, endpoint, method, status_code, duration_ms, tokens_used, error)
```

### Step 8.4 — Configure Loguru in `app/main.py`
```python
from loguru import logger
logger.remove()
logger.add(sys.stdout, format="{message}", serialize=True)  # JSON output
```

Every log entry must include: `timestamp`, `level`, `request_id`, `user_id`, `method`, `endpoint`, `status_code`, `duration_ms`, `tokens_used`, `error`.

### Step 8.5 — Add Sentry
```python
import sentry_sdk
sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.APP_ENV)
```

### ✅ Phase 8 Done When:
```bash
docker-compose up  # worker container starts without errors
# Send a message → check logs → JSON log entry appears
# Check DB → request_logs row inserted by Celery worker
```

---

## PHASE 9 — Admin Analytics Endpoints
**Goal:** Admin dashboard endpoints return accurate platform stats.

### Step 9.1 — Create `app/services/analytics_service.py`
```python
async def get_platform_stats(db, redis) -> dict:
    # total_users: COUNT(*) FROM users
    # active_sessions_today: COUNT DISTINCT session_id FROM messages WHERE today
    # total_messages_today: COUNT FROM messages WHERE today
    # total_tokens_today: SUM(total_tokens) FROM messages WHERE today
    # estimated_cost_today_usd: formula from PRD Section 7.7
    # error_rate_percent: errors/total from request_logs today
    # avg_response_time_ms: AVG(duration_ms) from request_logs today

async def get_per_user_stats(db) -> list[dict]:
    # Per user: total_messages, total_tokens, last_active

async def get_recent_logs(db, filters) -> list[RequestLog]:
    # Filterable by endpoint, status_code, user_id
```

### Step 9.2 — Create `app/schemas/admin.py`
- `PlatformStatsResponse`
- `UserStatsResponse`
- `TokenStatsResponse`
- `LogResponse`

### Step 9.3 — Create `app/api/v1/admin.py`
All routes use `get_current_admin` dependency (role check):
- `GET /admin/analytics`
- `GET /admin/analytics/users`
- `GET /admin/analytics/tokens`
- `GET /admin/logs`
- `GET /admin/users`

### Step 9.4 — Create `app/api/v1/products.py`
- `GET /products` — public (bearer), optional category filter
- `POST /products` — admin only
- `PUT /products/{id}` — admin only
- `DELETE /products/{id}` — admin only (soft delete: `is_active=false`)

### Step 9.5 — Write `tests/test_admin.py`
- Non-admin hitting admin endpoint → 403
- Admin can access analytics
- Stats match seeded test data
- Non-admin cannot create/delete products

### ✅ Phase 9 Done When:
```bash
pytest tests/test_admin.py  # all pass
```

---

## PHASE 10 — Production Deployment
**Goal:** Live API accessible over HTTPS on Railway or Render.

### Step 10.1 — Create `docker-compose.prod.yml`
Same as dev but:
- No local `db` or `redis` services (use Supabase + Upstash)
- `app` and `worker` use image from Docker Hub
- Nginx includes SSL config

### Step 10.2 — SSL Setup (on VPS)
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```
Update `nginx/nginx.conf` to redirect HTTP→HTTPS and proxy to app.

### Step 10.3 — Fill production `.env`
- `DATABASE_URL` → Supabase connection string
- `REDIS_URL` → Upstash URL
- `SECRET_KEY` → generate with `openssl rand -hex 32`
- `OPENAI_API_KEY` → real key
- `SENTRY_DSN` → from Sentry project
- `ALLOWED_ORIGINS` → your real domain

### Step 10.4 — First production deploy
```bash
docker build -t yourdockerhubuser/ai-support-engine:latest .
docker push yourdockerhubuser/ai-support-engine:latest

# On VPS
docker-compose -f docker-compose.prod.yml up -d
docker-compose -f docker-compose.prod.yml exec app alembic upgrade head
```

### Step 10.5 — Verify health check
```bash
curl https://yourdomain.com/health
# → {"status": "healthy", "db": "connected", "redis": "connected"}
```

### ✅ Phase 10 Done When:
- API live at `https://yourdomain.com/api/v1`
- Swagger available at `https://yourdomain.com/docs`
- `/health` returns 200

---

## PHASE 11 — CI/CD Pipeline
**Goal:** Push to main auto-deploys after tests pass.

### Step 11.1 — Create `.github/workflows/deploy.yml`
Pipeline steps:
```yaml
on:
  push:
    branches: [main]

jobs:
  deploy:
    steps:
      - Checkout code
      - Set up Python 3.12
      - Install dependencies
      - Run ruff (linter)
      - Run pytest → STOP if fail
      - Build Docker image
      - Push to Docker Hub
      - SSH into VPS
      - Pull new image
      - docker-compose up -d
      - alembic upgrade head
```

### Step 11.2 — Add GitHub Secrets
In repo Settings → Secrets:
- `DOCKER_USERNAME`
- `DOCKER_PASSWORD`
- `VPS_HOST`
- `VPS_USER`
- `VPS_SSH_KEY`

### Step 11.3 — Test the pipeline
Push a small change to main → watch Actions tab → verify all steps green.

### ✅ Phase 11 Done When:
- Push to main → live site updated automatically
- Failing tests block deploy

---

## PHASE 12 — React Admin Dashboard (Minimal)
**Goal:** A working UI that shows admin analytics and recent logs.

### Step 12.1 — Bootstrap frontend
```bash
cd frontend
npm create vite@latest . -- --template react
npm install @shadcn/ui axios recharts
```

### Step 12.2 — Build pages
- **Login page** — calls `POST /auth/login`, stores access token
- **Dashboard page** — calls `GET /admin/analytics`, displays stats cards
- **Logs page** — calls `GET /admin/logs`, displays table with filters

### Step 12.3 — Proxy API in dev
In `vite.config.js`, proxy `/api` to `http://localhost:8000`.

### Step 12.4 — Build and serve via Nginx
```bash
npm run build
# Copy dist/ to nginx static folder or serve separately
```

### ✅ Phase 12 Done When:
- Admin can log in via UI
- Dashboard shows real token/user stats
- Logs table is visible and filterable

---

## PHASE 13 — Final QA & Documentation
**Goal:** 70% test coverage, full Swagger docs, Postman collection, README.

### Step 13.1 — Run full test suite with coverage
```bash
pytest --cov=app --cov-report=term-missing
# Target: ≥ 70% coverage
```
Add missing tests until target is met.

### Step 13.2 — Polish Swagger docs
Add to every route handler:
```python
@router.post("/auth/signup", response_model=UserResponse, status_code=201,
             summary="Register a new user",
             description="Creates a new user account. Returns user object without tokens.")
```

### Step 13.3 — Export Postman collection
- Import Swagger URL into Postman: `https://yourdomain.com/openapi.json`
- Add environment variables for `base_url` and `access_token`
- Export as `postman_collection.json` and commit to repo

### Step 13.4 — Write `README.md`
Sections:
- Project overview (2–3 sentences)
- Architecture diagram (ASCII or image)
- Quick start (docker-compose up)
- Environment variables table
- API endpoints summary
- Deployment guide link

### Step 13.5 — Write technical explanation document
File: `ARCHITECTURE.md`
Cover:
- Why FastAPI over Django/Flask
- Why stateless JWT + DB refresh tokens
- Why Redis for rate limiting (not in-memory)
- Why Celery for logging (non-blocking)
- Trade-offs made (no RAG, no multi-tenancy in v1)

### Step 13.6 — Record demo video (5–10 min)
Cover:
1. Signup and login
2. Create session, send messages, see AI response
3. Product recommendations appearing
4. Rate limit trigger (429 response)
5. Admin analytics dashboard
6. CI/CD pipeline green run

### ✅ Phase 13 Done When — Final Deliverables Checklist:
- [ ] GitHub repo with clean commits
- [ ] Live API URL
- [ ] `/docs` Swagger UI working
- [ ] `postman_collection.json` in repo
- [ ] `README.md` complete
- [ ] `ARCHITECTURE.md` complete
- [ ] Demo video uploaded
- [ ] `.env.example` committed
- [ ] `docker-compose.yml` tested locally
- [ ] ≥ 70% test coverage

---

## Quick Reference: Phase Order

| Phase | Focus | Days (est.) |
|---|---|---|
| 1 | Scaffold + Docker | 1–2 |
| 2 | Config + DB + Migrations | 2–3 |
| 3 | Auth system | 3–4 |
| 4 | Chat sessions + message storage | 5–6 |
| 5 | AI orchestrator + WebSocket | 7–8 |
| 6 | Rate limiting + token tracking | 9 |
| 7 | Recommendation engine | 11 |
| 8 | Celery + logging + Sentry | 12 |
| 9 | Admin analytics + products API | 13 |
| 10 | Production deployment | 14 |
| 11 | CI/CD pipeline | 15 |
| 12 | React admin dashboard | 16 |
| 13 | QA + docs + demo | 17–20 |

---

*Every phase must pass its ✅ Done When check before proceeding. No skipping.*
