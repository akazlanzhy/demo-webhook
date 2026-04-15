"""Webhook server with rate limiting and event deduplication."""

import hashlib
import time
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    max_requests: int = 100
    window_seconds: int = 3600
    burst_limit: int = 10
    burst_window_seconds: int = 60


@dataclass
class WebhookEvent:
    """Represents a processed webhook event."""

    event_id: str
    event_type: str
    payload: dict
    received_at: float
    processed: bool = False
    retry_count: int = 0


class EventStore:
    """In-memory store for webhook events with deduplication."""

    def __init__(self, dedup_window_seconds: int = 300):
        self._events: dict[str, WebhookEvent] = {}
        self._dedup_window = dedup_window_seconds

    def is_duplicate(self, event_id: str) -> bool:
        """Check if an event with this ID was already processed recently."""
        if event_id not in self._events:
            return False
        existing = self._events[event_id]
        if time.time() - existing.received_at < self._dedup_window:
            return True
        return False

    def store(self, event: WebhookEvent) -> None:
        """Store an event for deduplication tracking."""
        self._events[event.event_id] = event

    def get_unprocessed(self) -> list[WebhookEvent]:
        """Get all events that haven't been processed yet."""
        return [e for e in self._events.values() if not e.processed]

    def mark_processed(self, event_id: str) -> bool:
        """Mark an event as processed. Returns False if event not found."""
        if event_id not in self._events:
            return False
        self._events[event_id].processed = True
        return True

    def cleanup_old_events(self, max_age_seconds: int = 86400) -> int:
        """Remove events older than max_age. Returns count of removed events."""
        now = time.time()
        old_ids = [
            eid
            for eid, event in self._events.items()
            if now - event.received_at > max_age_seconds
        ]
        for eid in old_ids:
            del self._events[eid]
        return len(old_ids)


class RateLimiter:
    """Token bucket rate limiter with burst support."""

    def __init__(self, config: RateLimitConfig | None = None):
        self._config = config or RateLimitConfig()
        self._requests: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, client_id: str) -> bool:
        """Check if a request from this client is allowed."""
        now = time.time()
        timestamps = self._requests[client_id]

        # Clean old timestamps outside the main window
        self._requests[client_id] = [
            ts for ts in timestamps if now - ts < self._config.window_seconds
        ]
        timestamps = self._requests[client_id]

        # Check main rate limit
        if len(timestamps) >= self._config.max_requests:
            return False

        # Check burst limit
        recent = [ts for ts in timestamps if now - ts < self._config.burst_window_seconds]
        if len(recent) >= self._config.burst_limit:
            return False

        return True

    def record_request(self, client_id: str) -> None:
        """Record a request timestamp for the client."""
        self._requests[client_id].append(time.time())

    def get_remaining(self, client_id: str) -> dict:
        """Get remaining quota information for a client."""
        now = time.time()
        timestamps = self._requests.get(client_id, [])
        active = [ts for ts in timestamps if now - ts < self._config.window_seconds]
        recent = [ts for ts in active if now - ts < self._config.burst_window_seconds]

        return {
            "remaining": self._config.max_requests - len(active),
            "burst_remaining": self._config.burst_limit - len(recent),
            "reset_at": min(active) + self._config.window_seconds if active else now,
        }


def generate_event_id(payload: dict) -> str:
    """Generate a deterministic event ID from the payload.

    Uses SHA-256 hash of the payload content for deduplication.
    """
    content = str(sorted(payload.items()))
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def process_webhook(
    payload: dict,
    event_type: str,
    client_id: str,
    event_store: EventStore,
    rate_limiter: RateLimiter,
) -> dict:
    """Process an incoming webhook request.

    Returns a response dict with status and details.
    """
    # Rate limit check
    if not rate_limiter.is_allowed(client_id):
        remaining = rate_limiter.get_remaining(client_id)
        return {
            "status": "rate_limited",
            "retry_after": remaining["reset_at"] - time.time(),
        }

    rate_limiter.record_request(client_id)

    # Generate event ID and check for duplicates
    event_id = generate_event_id(payload)
    if event_store.is_duplicate(event_id):
        return {"status": "duplicate", "event_id": event_id}

    # Store and process the event
    event = WebhookEvent(
        event_id=event_id,
        event_type=event_type,
        payload=payload,
        received_at=time.time(),
    )
    event_store.store(event)

    return {
        "status": "accepted",
        "event_id": event_id,
        "event_type": event_type,
    }
