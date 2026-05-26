# Architecture & Design Decisions

This document explains the key architectural choices made in the AI Customer Support & Recommendation Engine and the rationale behind each.

---

## 1. FastAPI (Async-First Framework)

**Decision**: Use FastAPI as the web framework with fully async route handlers.

**Rationale**:
- FastAPI is built on Starlette/ASGI, making it natively non-blocking. All I/O — database queries, Redis operations, OpenAI API calls — can be awaited without blocking the event loop.
- The automatic OpenAPI/Swagger UI generation (`/docs`) means every route is self-documenting with zero extra effort.
- Pydantic v2 integration provides strict request/response validation and serialization at near-zero cost.
- Dependency injection (`Depends(...)`) cleanly decouples concerns like auth, DB sessions, and rate limiting from handler logic.

**Trade-off**: FastAPI has a steeper learning curve than Flask/Django for developers unfamiliar with async Python. However, for an AI/streaming workload, the performance gains justify it.

---

## 2. PostgreSQL + SQLAlchemy (Async ORM)

**Decision**: Use PostgreSQL with `asyncpg` driver and SQLAlchemy 2.0 async sessions.

**Rationale**:
- PostgreSQL offers JSONB, full-text search, and robust transaction semantics — all useful for storing chat messages and product tags.
- SQLAlchemy's async engine (`create_async_engine`) combined with `asyncpg` provides true non-blocking DB access.
- The repository pattern (`repositories/`) abstracts all SQL from service and route layers, making queries swappable and testable.

**Production consideration**: Supabase (the production DB host) uses PgBouncer in transaction pooling mode. This requires `prepared_statement_cache_size=0` in the asyncpg connection args to avoid `prepared statement already exists` errors. Both the main engine and the migration engine are configured this way.

**Trade-off**: Async SQLAlchemy has more complexity around session lifecycle than synchronous Django ORM. The `AsyncSessionLocal` context manager is used everywhere to ensure sessions are properly closed.

---

## 3. JWT Authentication (Access + Refresh Token Rotation)

**Decision**: Stateless JWT authentication with short-lived access tokens (30 min) and rotating refresh tokens (7 days).

**Rationale**:
- Stateless JWTs eliminate server-side session storage, enabling horizontal scaling without sticky sessions.
- Refresh token rotation means a stolen refresh token is invalidated after one use. The `refresh_tokens` table tracks issued tokens to prevent replay.
- `passlib[bcrypt]` handles password hashing — bcrypt's work factor makes brute-force attacks impractical.

**Trade-off**: Access tokens cannot be revoked mid-TTL without a token blocklist (Redis). A 30-minute TTL is a deliberate balance between security and user friction. Refresh token revocation is supported via DB lookup.

---

## 4. Redis (Rate Limiting + Session Store)

**Decision**: Use Redis as the backend for the sliding-window rate limiter and as a Celery broker.

**Rationale**:
- Rate limiting is implemented with Redis INCR + EXPIREAT using a per-user/per-group key. This is O(1) per request and naturally expires without GC overhead.
- Redis is an excellent ephemeral store because reconnects are fast and state loss on restart is acceptable (limits simply reset).
- For development, `fakeredis` is used in tests so no real Redis instance is required.

**Trade-off**: Adding Redis as a required dependency increases operational complexity. If Redis is down, rate limiting degrades gracefully (limits are skipped, not enforced) — this is an explicit design choice to prioritise availability over strict limiting.

---

## 5. OpenAI Streaming via WebSocket

**Decision**: Real-time chat uses WebSocket (`/api/v1/ws/chat/{session_id}`) rather than HTTP long-polling.

**Rationale**:
- OpenAI's `stream=True` yields tokens progressively. WebSocket allows each token chunk to be forwarded to the client as it arrives, creating a smooth typing-cursor UX.
- A single persistent WebSocket connection eliminates the HTTP handshake overhead for every message in a session.
- The WS endpoint authenticates via a `?token=<jwt>` query parameter because browser WebSocket APIs do not support custom headers.

**Trade-off**: WebSocket connections are stateful and require careful resource cleanup on disconnect (`WebSocketDisconnect` exception). Each connection holds one DB session for its lifetime, which can be a bottleneck under high concurrency. Future mitigation: a connection manager with session pooling.

---

## 6. Recommendation Engine

**Decision**: Use OpenAI embeddings + tag matching to surface relevant products from the conversation context.

**Rationale**:
- Product tags stored as a PostgreSQL text array enable fast keyword-based matching without a vector DB.
- The LLM extracts product-related keywords from the conversation history, and those keywords are scored against product tags.
- This approach is simple, fast, and doesn't require a separate vector store (Pinecone/Weaviate) for MVP scale.

**Trade-off**: Tag-based matching is not true semantic search. A `pgvector` extension or dedicated vector store would improve recommendation quality significantly. This is the planned Phase 2 enhancement.

---

## 7. Middleware: Request Logging

**Decision**: Implement logging as ASGI middleware rather than route-level decorators.

**Rationale**:
- Middleware captures every request/response pair including those that never reach a route handler (e.g., 404s, CORS pre-flights).
- Logging in middleware keeps route handlers clean and ensures consistent log schema across all endpoints.
- `RequestLoggingMiddleware` records: request ID, user ID (if authenticated), endpoint, method, status code, duration (ms), tokens used, and error messages.

**Production logging**: In production (no Celery worker), logs are written directly to the `request_logs` table via an `AsyncSessionLocal` context. In development, they are offloaded to a Celery background task. This design ensures logs are never lost in either environment.

---

## 8. Production Deployment: Render + Vercel

**Decision**: Backend on Render (Docker container), frontend on Vercel (CDN).

**Rationale**:
- Render natively supports Docker deployments and provides a managed PostgreSQL add-on (or Supabase external DB).
- Vercel is optimal for Vite/React SPAs — instant global deployments with Edge CDN.
- The Vite proxy (`/api` → `http://localhost:8000`) is only used in development. In production, the frontend uses `VITE_API_URL` and `VITE_WS_URL` environment variables to call the Render backend directly.

**Trade-off**: The Render free tier spins down after 15 minutes of inactivity (cold starts ~30s). This is acceptable for demo purposes; a paid tier or an external uptime monitor would keep the server warm in production.

---

## 9. No Celery in Production (Single-Process Render)

**Decision**: Remove Celery dependency for production; use direct DB writes in middleware.

**Rationale**:
- Render's free/starter tier runs a single process. A second Celery worker process would require a separate Render service + Redis (cost and complexity).
- For the logging volume expected (hundreds of req/day in an MVP), synchronous DB writes in middleware add < 5ms per request — negligible.

**Trade-off**: Under very high traffic, logging could become a bottleneck. The Celery task scaffolding (`app/workers/tasks.py`) remains in place for easy re-enablement when scaling to multi-worker deployments.

---

## 10. Dependency Injection for Testing

**Decision**: Use FastAPI's `app.dependency_overrides` to swap real DB/Redis with fakes in tests.

**Rationale**:
- Tests override `get_db` with an in-memory SQLite-compatible async session and `get_redis` with `fakeredis`.
- No external services are required to run the test suite — CI/CD can run tests in a single container without sidecars.
- The middleware detects `get_db in app.dependency_overrides` and skips database logging in tests to avoid interference.

---

## Summary Table

| Component | Technology | Key Reason |
|-----------|-----------|------------|
| API Framework | FastAPI | Async-first, OpenAPI auto-docs |
| Database | PostgreSQL + asyncpg | JSONB, full-text, PgBouncer-compatible |
| ORM | SQLAlchemy 2.0 (async) | Repository pattern, testable |
| Auth | JWT + bcrypt | Stateless, scalable, secure |
| Cache | Redis 7 | Rate limiting, ephemeral state |
| AI | OpenAI gpt-4o-mini | Streaming, cost-effective |
| Real-time | WebSocket | Token-by-token streaming UX |
| Background Jobs | Celery (dev) / direct DB (prod) | Environment-appropriate logging |
| Monitoring | Sentry + Loguru | Error tracking + structured logs |
| Deployment | Render + Vercel | Managed, zero-config CI/CD |
