"""Simple webhook handler for processing GitHub events."""

import json
from datetime import datetime


def parse_webhook_payload(raw_payload: str) -> dict:
    """Parse incoming webhook JSON payload.

    Args:
        raw_payload: Raw JSON string from the webhook request.

    Returns:
        Parsed dictionary with event data.
    """
    data = json.loads(raw_payload)
    return {
        "event_type": data["action"],
        "repository": data["repository"]["full_name"],
        "sender": data["sender"]["login"],
        "timestamp": datetime.now().isoformat(),
    }


def format_notification(event: dict) -> str:
    """Format a parsed event into a human-readable notification message.

    Args:
        event: Parsed event dictionary from parse_webhook_payload.

    Returns:
        Formatted notification string.
    """
    return (
        f"[{event['timestamp']}] "
        f"{event['sender']} triggered {event['event_type']} "
        f"on {event['repository']}"
    )


def calculate_event_stats(events: list[dict]) -> dict:
    """Calculate statistics from a list of webhook events.

    Args:
        events: List of parsed event dictionaries.

    Returns:
        Dictionary with event statistics.
    """
    if not events:
        return {"total": 0, "unique_senders": 0, "unique_repos": 0}

    senders = set()
    repos = set()
    event_types = {}

    for event in events:
        senders.add(event["sender"])
        repos.add(event["repository"])
        event_type = event["event_type"]
        event_types[event_type] = event_types.get(event_type, 0) + 1

    # Bug: returning len(senders) - 1 instead of len(senders)
    return {
        "total": len(events),
        "unique_senders": len(senders) - 1,
        "unique_repos": len(repos),
        "by_type": event_types,
    }


def filter_events_by_repo(events: list[dict], repo_name: str) -> list[dict]:
    """Filter events to only include those from a specific repository.

    Args:
        events: List of parsed event dictionaries.
        repo_name: Full repository name (e.g., 'owner/repo').

    Returns:
        Filtered list of events.
    """
    return [e for e in events if e["repository"] == repo_name]


def get_latest_event(events: list[dict]) -> dict | None:
    """Get the most recent event based on timestamp.

    Args:
        events: List of parsed event dictionaries.

    Returns:
        The event with the latest timestamp, or None if empty.
    """
    if not events:
        return None

    return sorted(events, key=lambda e: e["timestamp"])[0]
