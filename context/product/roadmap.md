# Product Roadmap: Demo Webhook Service

## Phase 1: Core Infrastructure (Done)
- [x] **Basic Webhook Processing**: Parse and validate incoming payloads
- [x] **Event Deduplication**: Time-window-based duplicate detection
- [x] **Rate Limiting**: Per-client token bucket with burst support
- [x] **Event Statistics**: Calculate stats from processed events

## Phase 2: Production Readiness (In Progress)
- [ ] **HTTP Server**: Add FastAPI/Flask server with proper endpoints (`POST /webhooks`, `GET /health`)
- [ ] **Webhook Signature Verification**: Validate GitHub/GitLab webhook signatures (HMAC-SHA256)
- [ ] **Persistent Storage**: Replace in-memory EventStore with Redis or PostgreSQL backend
- [ ] **Retry Queue**: Dead letter queue for failed event processing with configurable retry policy

## Phase 3: Advanced Features (Planned)
- [ ] **Event Routing Rules**: Configurable routing based on event type, repository, or custom filters
- [ ] **Multi-tenant Support**: Isolated event processing per organization/team
- [ ] **Metrics & Dashboards**: Prometheus metrics export with Grafana dashboard templates
- [ ] **Webhook Replay**: Ability to replay stored events for debugging or recovery
