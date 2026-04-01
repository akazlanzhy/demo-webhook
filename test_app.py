"""Tests for webhook handler."""

from app import (
    calculate_event_stats,
    filter_events_by_repo,
    format_notification,
    parse_webhook_payload,
)


def test_parse_webhook_payload():
    raw = '{"action": "opened", "repository": {"full_name": "org/repo"}, "sender": {"login": "alice"}}'
    result = parse_webhook_payload(raw)
    assert result["event_type"] == "opened"
    assert result["repository"] == "org/repo"
    assert result["sender"] == "alice"
    assert "timestamp" in result


def test_format_notification():
    event = {
        "timestamp": "2026-01-01T00:00:00",
        "sender": "bob",
        "event_type": "closed",
        "repository": "org/repo",
    }
    msg = format_notification(event)
    assert "bob" in msg
    assert "closed" in msg
    assert "org/repo" in msg


def test_calculate_event_stats():
    events = [
        {"sender": "alice", "repository": "org/repo1", "event_type": "opened"},
        {"sender": "bob", "repository": "org/repo1", "event_type": "closed"},
        {"sender": "alice", "repository": "org/repo2", "event_type": "opened"},
    ]
    stats = calculate_event_stats(events)
    assert stats["total"] == 3
    assert stats["unique_senders"] == 2
    assert stats["unique_repos"] == 2
    assert stats["by_type"] == {"opened": 2, "closed": 1}


def test_calculate_event_stats_empty():
    stats = calculate_event_stats([])
    assert stats["total"] == 0
    assert stats["unique_senders"] == 0


def test_filter_events_by_repo():
    events = [
        {"sender": "alice", "repository": "org/repo1", "event_type": "opened"},
        {"sender": "bob", "repository": "org/repo2", "event_type": "closed"},
        {"sender": "carol", "repository": "org/repo1", "event_type": "merged"},
    ]
    filtered = filter_events_by_repo(events, "org/repo1")
    assert len(filtered) == 2
    assert all(e["repository"] == "org/repo1" for e in filtered)
