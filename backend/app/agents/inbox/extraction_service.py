"""
LLM Extraction Service — Inbox Intelligence Agent

Uses Google Gemini (same SDK already in LlmEvaluator) to extract structured
task information from filtered emails. Only filtered emails reach this service.

Behaviour:
- Sends a structured prompt requesting JSON output.
- Validates extracted JSON against ExtractedTask schema.
- Rejects extractions below the runtime confidence threshold.
- Returns None for unextractable emails — never raises exceptions.

Falls back to mock extraction when GEMINI_API_KEY is not set (same pattern
as LlmEvaluator — safe for local development and testing).
"""

from __future__ import annotations

import json
import logging
import os
import textwrap
from typing import Any, Dict, Optional

from agents.inbox.schemas import ExtractedTask, RawEmail
from agent_runtime.config import settings

logger = logging.getLogger("agents.inbox.extraction_service")

# Maximum email body length sent to LLM (controls token spend)
MAX_BODY_CHARS: int = int(os.getenv("INBOX_MAX_BODY_CHARS", "2000"))

# The Gemini model to use for extraction
_EXTRACTION_MODEL: str = os.getenv("INBOX_EXTRACTION_MODEL", settings.DEFAULT_MODEL)


# ---------------------------------------------------------------------------
# Gemini client (lazy singleton)
# ---------------------------------------------------------------------------

_client: Optional[Any] = None


def _get_client() -> Optional[Any]:
    """Returns the Gemini client, building it lazily on first use."""
    global _client
    if _client is not None:
        return _client

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.warning("GEMINI_API_KEY not set — using mock extraction.")
        return None

    try:
        from google import genai
        _client = genai.Client(api_key=api_key)
        logger.info("Gemini client initialised for inbox extraction.")
        return _client
    except Exception as exc:
        logger.error("Failed to initialise Gemini client: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

_EXTRACTION_SYSTEM_PROMPT = textwrap.dedent("""
    You are an email-to-task extraction assistant.

    Your ONLY job is to determine whether an email contains a **clearly actionable task**
    for the recipient, and if so, extract structured information about that task.

    Rules:
    1. Only extract a task if the email clearly requires the recipient to DO something.
    2. If the email is purely informational (no action needed), return confidence < 0.5.
    3. NEVER invent information not present in the email.
    4. Dates/times MUST come directly from the email text. If none are mentioned, leave them null.
    5. Return ONLY valid JSON — no markdown, no explanations.

    Output schema (JSON):
    {
        "title": "Short, clear task title (max 80 chars)",
        "confidence": 0.0 to 1.0,
        "deadline": "YYYY-MM-DD HH:MM or descriptive string from email, or null",
        "due_date": "YYYY-MM-DD or null",
        "due_time": "HH:MM or null",
        "location": "physical location or null",
        "meeting_link": "URL if present or null",
        "sender": "display name of sender or null",
        "task_category": "Meeting|Submission|Presentation|Interview|Review|Follow-up|Other or null",
        "urgency": "high|medium|low or null",
        "description": "1-2 sentence summary of what needs to be done, or null"
    }

    Confidence guidelines:
    - 0.95-1.0: Explicit deadline, clear action, sender expecting a response
    - 0.80-0.94: Clear action needed, date implied or mentioned
    - 0.60-0.79: Action likely needed but details are vague
    - 0.40-0.59: Might require action but mostly informational
    - 0.0-0.39: No clear action — informational email
""").strip()


def _build_extraction_prompt(email: RawEmail) -> str:
    """Builds the user-turn prompt for a specific email."""
    body_excerpt = (email.body or email.snippet or "")[:MAX_BODY_CHARS]
    return textwrap.dedent(f"""
        Extract a task from the following email.

        ---
        FROM: {email.sender} <{email.sender_email}>
        SUBJECT: {email.subject}
        DATE: {email.date.isoformat() if email.date else "unknown"}
        ---
        BODY:
        {body_excerpt}
        ---
    """).strip()


# ---------------------------------------------------------------------------
# Mock extraction (no API key)
# ---------------------------------------------------------------------------

def _mock_extract(email: RawEmail) -> Optional[ExtractedTask]:
    """
    Deterministic mock extractor used when GEMINI_API_KEY is absent.
    Returns a plausible low-confidence suggestion so tests work end-to-end.
    """
    # Keywords that suggest the email is actionable
    actionable_kw = [
        "meeting", "submit", "deadline", "present", "review", "confirm",
        "interview", "schedule", "due", "urgent", "attend", "join"
    ]
    combined = (email.subject + " " + email.snippet).lower()
    is_actionable = any(kw in combined for kw in actionable_kw)
    confidence = 0.78 if is_actionable else 0.30

    if confidence < settings.EVALUATION_CONFIDENCE_THRESHOLD:
        return None

    return ExtractedTask(
        title=email.subject[:80] or "Task from email",
        confidence=confidence,
        description=email.snippet[:200] if email.snippet else None,
        sender=email.sender or None,
        task_category="Other",
        urgency="medium",
        source_message_id=email.message_id,
        source_subject=email.subject,
        source_sender_email=email.sender_email,
    )


# ---------------------------------------------------------------------------
# Core extraction function
# ---------------------------------------------------------------------------

def extract_task_from_email(
    email: RawEmail,
    confidence_threshold: Optional[float] = None,
) -> Optional[ExtractedTask]:
    """
    Extracts a structured task from a single email using Gemini.

    Args:
        email: A filtered, potentially actionable email.
        confidence_threshold: Minimum confidence to accept. Defaults to
            settings.EVALUATION_CONFIDENCE_THRESHOLD.

    Returns:
        ExtractedTask if extraction succeeded and confidence >= threshold.
        None if the email is not actionable or extraction failed.
    """
    threshold = confidence_threshold if confidence_threshold is not None else settings.EVALUATION_CONFIDENCE_THRESHOLD
    client = _get_client()

    # --- Mock path ---
    if not client:
        result = _mock_extract(email)
        print(f"MOCK PARSED RESULT JSON: {result.model_dump_json() if result else 'None'}")
        if result and result.confidence >= threshold:
            logger.debug(
                "Mock extraction for '%s': title='%s', confidence=%.2f",
                email.message_id, result.title, result.confidence
            )
            return result
        logger.debug(
            "Mock extraction rejected email '%s': confidence below threshold.", email.message_id
        )
        return None

    # --- Real Gemini path ---
    prompt = _build_extraction_prompt(email)
    try:
        response = client.models.generate_content(
            model=_EXTRACTION_MODEL,
            contents=[
                {"role": "user", "parts": [
                    {"text": _EXTRACTION_SYSTEM_PROMPT + "\n\n" + prompt}
                ]}
            ],
            config={"response_mime_type": "application/json"},
        )
        raw_text = response.text.strip()
    except Exception as exc:
        logger.warning(
            "Gemini API call failed for email '%s': %s — skipping.", email.message_id, exc
        )
        return None

    # Parse and validate JSON
    try:
        data: Dict[str, Any] = json.loads(raw_text)
        print(f"GEMINI PARSED RESULT JSON: {raw_text}")
    except json.JSONDecodeError as exc:
        logger.warning(
            "Gemini returned non-JSON for email '%s': %s", email.message_id, exc
        )
        return None

    # Confidence threshold check
    confidence = float(data.get("confidence", 0.0))
    if confidence < threshold:
        logger.debug(
            "Extraction rejected for email '%s': confidence %.2f < threshold %.2f.",
            email.message_id, confidence, threshold
        )
        return None

    # Construct and validate ExtractedTask
    try:
        task = ExtractedTask(
            title=str(data.get("title", email.subject))[:80],
            confidence=confidence,
            deadline=data.get("deadline"),
            due_date=data.get("due_date"),
            due_time=data.get("due_time"),
            location=data.get("location"),
            meeting_link=data.get("meeting_link"),
            sender=data.get("sender") or email.sender or None,
            task_category=data.get("task_category"),
            urgency=data.get("urgency"),
            description=data.get("description"),
            source_message_id=email.message_id,
            source_subject=email.subject,
            source_sender_email=email.sender_email,
        )
        logger.info(
            "Extracted task from email '%s': title='%s', confidence=%.2f",
            email.message_id, task.title, task.confidence
        )
        return task

    except Exception as exc:
        logger.warning(
            "ExtractedTask validation failed for email '%s': %s", email.message_id, exc
        )
        return None
