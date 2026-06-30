

from __future__ import annotations

import logging
import re
from typing import List, Set

from agents.inbox.schemas import FilterResult, RawEmail

logger = logging.getLogger("agents.inbox.filter_service")

_BLOCKED_LABELS: Set[str] = {
    "CATEGORY_PROMOTIONS",
    "CATEGORY_SOCIAL",
    "CATEGORY_UPDATES",  # automated updates, not user-actionable
    "SPAM",
}

_BLOCKED_SUBJECT_PATTERNS: List[re.Pattern] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        # One-time passwords / verification
        r"\botp\b",
        r"one[- ]?time password",
        r"verification code",
        r"\bverify\b.{0,20}code",
        r"auth.{0,10}code",
        r"\bpin\b.{0,10}account",
        # Financial / transactional
        r"order (shipped|delivered|confirmed|placed|cancelled)",
        r"shipment (update|notification)",
        r"payment (received|confirmed|failed|due)",
        r"invoice #",
        r"receipt for",
        r"transaction (complete|failed)",
        r"refund (processed|initiated)",
        # Marketing / promotional
        r"\d+%\s*off",
        r"(limited|special|exclusive) offer",
        r"sale (ends|today|now)",
        r"deal of the (day|week)",
        r"promo(tion)? code",
        r"discount",
        r"(free|complimentary) (shipping|trial|gift)",
        r"flash sale",
        r"black friday",
        r"cyber monday",
        # Subscription / account management
        r"subscription (renewed|cancelled|expired|confirmation)",
        r"password (reset|changed)",
        r"account (created|suspended|verified|closed)",
        r"welcome to",                   # welcome/signup confirmation
        r"unsubscribe",
        r"newsletter",
        # Notifications / alerts
        r"(new|incoming) message",        # social message notifications
        r"liked your (post|photo|comment)",
        r"(followed|friended) you",
        r"tagged you",
        r"comment on your",
        # Shipping
        r"(your|your package|estimated) delivery",
        r"out for delivery",
        r"delivered to",
        r"tracking (number|update)",
    ]
]

# Known-spam / marketing sender domain patterns
_BLOCKED_SENDER_PATTERNS: List[re.Pattern] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"noreply@",
        r"no-reply@",
        r"donotreply@",
        r"mailer-daemon@",
        r"notifications?@",
        r"newsletter@",
        r"marketing@",
        r"promo@",
        r"deals@",
        r"offers@",
        r"info@.*\.(shopify|mailchimp|sendgrid|klaviyo|hubspot)\.com",
    ]
]

# Minimum non-whitespace body length — shorter than this is likely auto-generated
_MIN_BODY_LENGTH: int = 40

# Minimum subject length
_MIN_SUBJECT_LENGTH: int = 4


# ---------------------------------------------------------------------------
# Positive signals (override blocklist — these emails are almost always actionable)
# ---------------------------------------------------------------------------

_ACTIONABLE_SUBJECT_PATTERNS: List[re.Pattern] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\bmeeting\b",
        r"\binterview\b",
        r"\bsubmit(sion)?\b",
        r"\bdeadline\b",
        r"\bpresent(ation)?\b",
        r"\breview\b.{0,20}(by|before|due)",
        r"\bdue\b.{0,10}(date|by|on|at)",
        r"\burgent\b",
        r"\bimportant\b.{0,15}(action|response|reply)",
        r"\baction required\b",
        r"\bplease (review|confirm|respond|reply|submit|attend|join)\b",
        r"\bjoin\b.{0,20}(call|meeting|session|webinar)",
        r"\bschedule\b.{0,20}(call|meeting|session)",
        r"\binvite(d)?\b",
        r"\bproject\b.{0,20}(update|kickoff|status)",
        r"\bassignment\b",
        r"\b(weekly|daily|monthly) (sync|standup|report)\b",
    ]
]


# ---------------------------------------------------------------------------
# Core filter function
# ---------------------------------------------------------------------------

def filter_email(email: RawEmail) -> FilterResult:
    """
    Applies rule-based relevance filtering to a single email.

    Returns a FilterResult with is_relevant=True if the email SHOULD be
    passed to the LLM for task extraction.
    """
    msg_id = email.message_id

    # 1. Check Gmail labels first (most reliable signal)
    for label in email.labels:
        if label in _BLOCKED_LABELS:
            logger.debug("Email '%s' filtered: label=%s", msg_id, label)
            return FilterResult(
                message_id=msg_id,
                is_relevant=False,
                reason=f"Gmail label indicates non-actionable category: {label}",
            )

    # 2. Check for positive signals — if found, bypass blocklist checks
    subject_lower = email.subject.strip()
    for pattern in _ACTIONABLE_SUBJECT_PATTERNS:
        if pattern.search(subject_lower):
            logger.debug("Email '%s' fast-pass: actionable subject pattern.", msg_id)
            return FilterResult(
                message_id=msg_id,
                is_relevant=True,
                reason="Subject contains actionable signal.",
            )

    # 3. Sender domain / address blocklist
    for pattern in _BLOCKED_SENDER_PATTERNS:
        if pattern.search(email.sender_email):
            logger.debug("Email '%s' filtered: blocked sender=%s", msg_id, email.sender_email)
            return FilterResult(
                message_id=msg_id,
                is_relevant=False,
                reason=f"Sender matches marketing/automated pattern: {email.sender_email}",
            )

    # 4. Subject keyword blocklist
    for pattern in _BLOCKED_SUBJECT_PATTERNS:
        if pattern.search(email.subject):
            logger.debug(
                "Email '%s' filtered: blocked subject pattern '%s'.", msg_id, pattern.pattern
            )
            return FilterResult(
                message_id=msg_id,
                is_relevant=False,
                reason=f"Subject matches non-actionable pattern: '{email.subject[:80]}'",
            )

    # 5. Minimum body length guard
    effective_body = (email.body or email.snippet or "").strip()
    if len(effective_body) < _MIN_BODY_LENGTH:
        logger.debug("Email '%s' filtered: body too short (%d chars).", msg_id, len(effective_body))
        return FilterResult(
            message_id=msg_id,
            is_relevant=False,
            reason=f"Email body too short ({len(effective_body)} chars) — likely automated.",
        )

    # 6. Minimum subject length guard
    if len(email.subject.strip()) < _MIN_SUBJECT_LENGTH:
        logger.debug("Email '%s' filtered: subject too short.", msg_id)
        return FilterResult(
            message_id=msg_id,
            is_relevant=False,
            reason="Subject line is too short to be actionable.",
        )

    # Passed all filters
    logger.debug("Email '%s' passed filter — sending to LLM.", msg_id)
    return FilterResult(
        message_id=msg_id,
        is_relevant=True,
        reason="No blocklist match found — potentially actionable.",
    )


def filter_emails_batch(emails: List[RawEmail]) -> tuple[List[RawEmail], List[FilterResult]]:
    """
    Filters a batch of emails, returning two lists:
    - relevant: emails that should proceed to LLM extraction
    - all_results: all FilterResult objects (for event emission)
    """
    relevant: List[RawEmail] = []
    all_results: List[FilterResult] = []

    for email in emails:
        result = filter_email(email)
        all_results.append(result)
        if result.is_relevant:
            relevant.append(email)

    filtered_count = len(emails) - len(relevant)
    logger.info(
        "Email filter: %d/%d passed, %d filtered.", len(relevant), len(emails), filtered_count
    )
    return relevant, all_results
