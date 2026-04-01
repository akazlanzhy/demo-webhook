# Functional Specification: HTTP Server

- **Roadmap Item:** HTTP Server (FastAPI/Flask) — `POST /webhooks`, `GET /health`
- **Status:** Draft
- **Author:** Artem Kazlanzhy

---

## 1. Overview and Rationale (The "Why")

The demo-webhook service currently operates as a Python library with no network interface. Users must import and call functions directly, which makes it unusable as a standalone service in CI/CD pipelines or event-driven architectures.

Adding an HTTP server is the first item on the Phase 2 (Production Readiness) roadmap. It exposes the existing webhook processing, deduplication, and rate-limiting logic over HTTP so that external systems (GitHub, GitLab, etc.) can deliver events to a running service.

**Problem:** There is no way to receive webhook payloads over the network. Integration requires embedding the library in custom code.

**Desired Outcome:** A lightweight HTTP server that accepts webhook payloads via POST, validates and processes them through the existing pipeline, and exposes a health-check endpoint for orchestrators and load balancers.

**Success Metrics:**
- < 50ms p99 latency for webhook processing (inherited from product definition).
- Health endpoint responds within 5 ms under normal load.
- Service starts and is ready to accept traffic in under 2 seconds.
- All existing unit tests continue to pass (no regressions).

---

## 2. Functional Requirements (The "What")

### 2.1 Webhook Ingestion Endpoint

- **As a** DevOps engineer, **I want to** send a POST request with a JSON webhook payload to the service, **so that** events are processed, deduplicated, and rate-limited automatically.
  - **Acceptance Criteria:**
    - [ ] `POST /webhooks` accepts a JSON body containing a webhook payload.
    - [ ] The endpoint passes the payload through `process_webhook()` (parse → rate-limit → deduplicate → store).
    - [ ] On success, the endpoint returns HTTP 200 with a JSON body containing the event ID and status.
    - [ ] If the payload is not valid JSON, the endpoint returns HTTP 400 with an error message.
    - [ ] If the client is rate-limited, the endpoint returns HTTP 429 with a `Retry-After` header.
    - [ ] If the event is a duplicate (within the dedup window), the endpoint returns HTTP 200 with a status indicating the event was deduplicated.

### 2.2 Health-Check Endpoint

- **As a** platform engineer, **I want to** query a health endpoint, **so that** load balancers and container orchestrators can determine whether the service is ready to accept traffic.
  - **Acceptance Criteria:**
    - [ ] `GET /health` returns HTTP 200 with a JSON body `{"status": "healthy"}` when the service is running.
    - [ ] The health endpoint does not require authentication.
    - [ ] The response includes the current server uptime in seconds.

### 2.3 Server Configuration

- The server must be configurable via environment variables:
  - **Acceptance Criteria:**
    - [ ] `HOST` — bind address (default `0.0.0.0`).
    - [ ] `PORT` — listen port (default `8000`).
    - [ ] Environment variables override defaults; no config file is required.

### 2.4 Startup and Shutdown

- **As a** DevOps engineer, **I want** the service to start and stop cleanly, **so that** deployments and restarts do not lose in-flight requests.
  - **Acceptance Criteria:**
    - [ ] The server can be started with `python -m webhook_server` (or an equivalent single command).
    - [ ] On SIGTERM / SIGINT the server completes in-flight requests before exiting.
    - [ ] Startup logs the bound host, port, and a "ready" message to stdout.

---

## 3. Scope and Boundaries

### In-Scope

- A minimal HTTP server exposing `POST /webhooks` and `GET /health`.
- JSON request/response handling.
- Integration with the existing `process_webhook()`, `EventStore`, and `RateLimiter`.
- Server configuration via environment variables (host, port).
- Graceful shutdown on termination signals.
- Structured logging for requests (method, path, status code, latency).

### Out-of-Scope

- Webhook signature verification (HMAC-SHA256) — separate Phase 2 roadmap item.
- Persistent storage (Redis/PostgreSQL) — separate Phase 2 roadmap item.
- Retry queue / dead-letter queue — separate Phase 2 roadmap item.
- Authentication or API keys.
- TLS termination (expected to be handled by a reverse proxy).
- Docker image or deployment manifests.
- UI or dashboard.
