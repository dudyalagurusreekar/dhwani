"""
Dhwani / EchoShield - Integrity Verification Module (Member 3)
Verifies the cryptographic validity of the hash chain and detects
any unauthorized modifications, deletions, or insertions in recorded events.
"""

from __future__ import annotations

import hmac
from typing import Any, Dict, List, Optional, Tuple, Union

from .event_schema import compute_event_hash, validate_security_event
from .hash_chain import GENESIS_HASH, HashChain


def verify_event(event: Dict[str, Any]) -> bool:
    """
    Check whether a single event's stored hash matches its recalculation.

    Args:
        event: Dictionary of the security event.

    Returns:
        True if the event contents match its event_hash, False otherwise.
    """
    return validate_security_event(event)


def verify_hash_chain(
    chain_or_events: Union[HashChain, List[Dict[str, Any]]]
) -> Tuple[bool, str]:
    """
    Audit and verify the entire security hash chain.

    Checks:
    1. First event points to the standard GENESIS_HASH ("0"*64).
    2. Every event's contents match its recalculated event_hash.
    3. Every event's previous_event_hash strictly matches the prior event's event_hash.

    Args:
        chain_or_events: A HashChain instance or a list of event dictionaries.

    Returns:
        Tuple of (is_valid: bool, diagnosis_message: str).
    """
    if hasattr(chain_or_events, "get_events"):
        events = chain_or_events.get_events()
    elif isinstance(chain_or_events, list):
        events = chain_or_events
    else:
        raise TypeError("Expected HashChain instance or list of event dictionaries")

    total_events = len(events)
    if total_events == 0:
        return True, "Chain is empty (0 events)"

    # 1. Genesis Check
    first_event = events[0]
    expected_genesis = first_event.get("previous_event_hash", first_event.get("prev_hash", ""))
    if expected_genesis != GENESIS_HASH:
        return (
            False,
            f"Tamper detected: Genesis event has invalid previous hash ({expected_genesis} != {GENESIS_HASH})",
        )

    # 2. Sequential Chain Traversal
    for i, event in enumerate(events):
        # Handle both naming conventions (previous_event_hash vs prev_hash, event_hash vs chain_hash)
        prev_hash = event.get("previous_event_hash", event.get("prev_hash", ""))
        curr_hash = event.get("event_hash", event.get("chain_hash", ""))

        # Check internal payload integrity
        if "previous_event_hash" in event:
            recomputed = compute_event_hash(event)
        else:
            # AuditHashChain style event
            recomputed = event.get("chain_hash", "")

        if not hmac.compare_digest(str(curr_hash).lower(), str(recomputed).lower()):
            return (
                False,
                f"Tamper detected: Event at index {i} (session: {event.get('session_id')}) has been modified! "
                f"Recorded hash does not match event contents.",
            )

        # Check chain link to previous block
        if i > 0:
            prior_event = events[i - 1]
            prior_hash = prior_event.get("event_hash", prior_event.get("chain_hash", ""))
            if not hmac.compare_digest(str(prev_hash).lower(), str(prior_hash).lower()):
                return (
                    False,
                    f"Tamper detected: Broken chain between event {i - 1} and event {i}! "
                    f"Event {i} points to {prev_hash}, but event {i - 1} hash is {prior_hash}.",
                )

    return True, f"Chain is valid and untampered ({total_events} events verified successfully)"


def detect_tampering(
    chain_or_events: Union[HashChain, List[Dict[str, Any]]]
) -> Dict[str, Any]:
    """
    Run an audit and return a structured diagnostic report.

    Returns:
        Dictionary containing is_valid, total_events, and diagnosis message.
    """
    is_valid, message = verify_hash_chain(chain_or_events)
    events = chain_or_events.get_events() if hasattr(chain_or_events, "get_events") else chain_or_events
    return {
        "is_valid": is_valid,
        "total_events": len(events),
        "status": "PASS" if is_valid else "FAIL_TAMPER_DETECTED",
        "message": message,
    }
