"""Tests for webhook server."""

import time

from webhook_server import (
    EventStore,
    RateLimitConfig,
    RateLimiter,
    WebhookEvent,
    generate_event_id,
    process_webhook,
)


def test_event_store_deduplication():
    """Events received within the dedup window should be detected as duplicates."""
    store = EventStore(dedup_window_seconds=300)
    event = WebhookEvent(
        event_id="abc123",
        event_type="push",
        payload={"ref": "main"},
        received_at=time.time(),
    )
    store.store(event)

    # Same event ID within the window should be a duplicate
    assert store.is_duplicate("abc123") is True

    # Unknown event ID should not be a duplicate
    assert store.is_duplicate("xyz789") is False


def test_event_store_dedup_expired():
    """Events outside the dedup window should NOT be detected as duplicates."""
    store = EventStore(dedup_window_seconds=300)
    old_event = WebhookEvent(
        event_id="old123",
        event_type="push",
        payload={"ref": "main"},
        received_at=time.time() - 600,  # 10 minutes ago, outside 5-min window
    )
    store.store(old_event)

    # Old event should not be duplicate (expired from dedup window)
    assert store.is_duplicate("old123") is False


def test_rate_limiter_allows_within_limit():
    config = RateLimitConfig(max_requests=5, window_seconds=60, burst_limit=3, burst_window_seconds=10)
    limiter = RateLimiter(config)

    assert limiter.is_allowed("client1") is True
    limiter.record_request("client1")
    assert limiter.is_allowed("client1") is True


def test_rate_limiter_blocks_over_burst():
    config = RateLimitConfig(max_requests=100, window_seconds=60, burst_limit=2, burst_window_seconds=10)
    limiter = RateLimiter(config)

    limiter.record_request("client1")
    limiter.record_request("client1")
    assert limiter.is_allowed("client1") is False


def test_generate_event_id_deterministic():
    payload = {"action": "opened", "repo": "test"}
    id1 = generate_event_id(payload)
    id2 = generate_event_id(payload)
    assert id1 == id2


def test_generate_event_id_different_payloads():
    id1 = generate_event_id({"action": "opened"})
    id2 = generate_event_id({"action": "closed"})
    assert id1 != id2


def test_process_webhook_success():
    store = EventStore()
    limiter = RateLimiter()
    result = process_webhook(
        payload={"action": "opened", "repo": "test"},
        event_type="pull_request",
        client_id="client1",
        event_store=store,
        rate_limiter=limiter,
    )
    assert result["status"] == "accepted"
    assert "event_id" in result


def test_process_webhook_duplicate():
    store = EventStore()
    limiter = RateLimiter()
    payload = {"action": "opened", "repo": "test"}

    # First request
    result1 = process_webhook(payload, "push", "client1", store, limiter)
    assert result1["status"] == "accepted"

    # Same payload again
    result2 = process_webhook(payload, "push", "client1", store, limiter)
    assert result2["status"] == "duplicate"


def test_event_store_mark_processed():
    store = EventStore()
    event = WebhookEvent(
        event_id="proc123",
        event_type="push",
        payload={},
        received_at=time.time(),
    )
    store.store(event)

    assert store.mark_processed("proc123") is True
    assert store.mark_processed("nonexistent") is False
    assert store.get_unprocessed() == []


def test_event_store_cleanup():
    store = EventStore()
    old_event = WebhookEvent(
        event_id="old1",
        event_type="push",
        payload={},
        received_at=time.time() - 100000,
    )
    new_event = WebhookEvent(
        event_id="new1",
        event_type="push",
        payload={},
        received_at=time.time(),
    )
    store.store(old_event)
    store.store(new_event)

    removed = store.cleanup_old_events(max_age_seconds=86400)
    assert removed == 1
    assert "new1" in store._events
    assert "old1" not in store._events
