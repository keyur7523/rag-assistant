"""Input / output / tool guardrails for the Northwind support agent.

These run *outside* the model loop so a prompt injection or a "just send
it" request cannot talk the agent into skipping human review. Soft prompt
rules still matter; this layer is the hard stop.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


MAX_MESSAGE_CHARS = 4000

# Patterns that try to override system instructions or exfiltrate them.
_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions",
    r"disregard\s+(your|the)\s+(system|prior)\s+(prompt|instructions)",
    r"you\s+are\s+now\s+(dan|unrestricted|jailbroken)",
    r"reveal\s+(your|the)\s+(system\s+)?prompt",
    r"print\s+(your|the)\s+(system\s+)?prompt",
]

# Asks that would skip the human-review draft step.
_AUTO_SEND_PATTERNS = [
    r"\bsend\s+(the\s+)?(email|reply|message)\s+(now|directly|immediately)\b",
    r"\bemail\s+the\s+customer\s+(now|directly|immediately)\b",
    r"\bdon'?t\s+(bother\s+with\s+)?(human\s+)?review\b",
    r"\bskip\s+(human\s+)?review\b",
    r"\bauto[- ]?send\b",
]

# Internal / PII fishing that tools cannot answer.
_OFF_POLICY_PATTERNS = [
    r"\b(ceo|cfo|cto|home\s+address|ssn|social\s+security)\b",
    r"\b(salary|payroll|employee\s+roster|internal\s+slack)\b",
    r"\bcredit\s+card\s+(number|cvv)\b",
]


@dataclass(frozen=True)
class GuardrailHit:
    reason: str
    message: str


def _matches(patterns: list[str], text: str) -> str | None:
    lowered = text.lower()
    for pattern in patterns:
        if re.search(pattern, lowered):
            return pattern
    return None


def check_input(user_message: str) -> GuardrailHit | None:
    """Return a hit to short-circuit the agent, or None to proceed."""
    if user_message is None or not user_message.strip():
        return GuardrailHit(
            reason="empty_input",
            message="Please send a customer question or support request.",
        )

    if len(user_message) > MAX_MESSAGE_CHARS:
        return GuardrailHit(
            reason="oversized_input",
            message=(
                f"Message is too long ({len(user_message)} chars). "
                f"Please keep requests under {MAX_MESSAGE_CHARS} characters."
            ),
        )

    if _matches(_INJECTION_PATTERNS, user_message):
        return GuardrailHit(
            reason="prompt_injection",
            message=(
                "I can't follow instructions that try to override my system "
                "rules. Rephrase as a normal customer-support request."
            ),
        )

    if _matches(_AUTO_SEND_PATTERNS, user_message):
        return GuardrailHit(
            reason="auto_send_blocked",
            message=(
                "I can draft a reply for a human to review, but I never send "
                "email directly. Ask me to draft a reply instead."
            ),
        )

    if _matches(_OFF_POLICY_PATTERNS, user_message):
        return GuardrailHit(
            reason="off_policy",
            message=(
                "I don't have access to internal employee or payment data. "
                "I can help with orders, shipping, returns, refunds, and warranties."
            ),
        )

    return None


def check_tool_call(tool_name: str, tool_input: dict) -> GuardrailHit | None:
    """Block tool calls that would bypass policy, even if the model asks."""
    allowed = {"get_order_status", "search_policies", "draft_reply", "escalate_to_human"}
    if tool_name not in allowed:
        return GuardrailHit(
            reason="unknown_tool",
            message=f"Blocked unknown tool: {tool_name}",
        )

    if tool_name == "draft_reply":
        message = (tool_input or {}).get("message", "")
        if _matches(_AUTO_SEND_PATTERNS, message):
            return GuardrailHit(
                reason="draft_claims_sent",
                message=(
                    "Draft text claimed the email was already sent. "
                    "Rewrite as a draft for human review only."
                ),
            )

    return None


def check_output(answer: str, tools_used: list) -> tuple[str, list[str]]:
    """Light post-checks. Returns (possibly adjusted answer, flag names)."""
    flags: list[str] = []
    if not answer or not answer.strip():
        flags.append("empty_answer")
        return (
            "I couldn't produce an answer. Please escalate to a human agent.",
            flags,
        )

    lowered = answer.lower()
    if re.search(r"\b(email (has been|was) sent|i('ve| have) sent the (email|reply))\b", lowered):
        flags.append("claimed_auto_send")
        answer = (
            answer.rstrip()
            + "\n\nNote: no email was sent. Drafts are saved for human review only."
        )

    return answer, flags