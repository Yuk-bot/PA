"""
Gmail Service — Inbox Intelligence Agent

Wraps the Gmail API. Reuses the existing Google OAuth credentials already
stored in Firestore under users/{uid}/integrations/google_calendar.

The Gmail scope (gmail.readonly) is expected to be added to the existing
OAuth flow (calender/oauth_handler.py). This service does NOT perform any
new authentication — it reads, refreshes, and updates tokens via the exact
same Firestore path used by GoogleCalendarClient.

Supports incremental sync via Gmail History API to avoid reprocessing.
"""

from __future__ import annotations

import base64
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from email import policy as email_policy
from email.parser import BytesParser
from typing import Any, Dict, List, Optional, Tuple

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from agents.inbox.schemas import InboxSyncState, RawEmail
from calender.oauth_handler import get_stored_credentials
from calender.utils import encrypt_token
from db.firebase import firebase_db

logger = logging.getLogger("agents.inbox.gmail_service")

# Gmail scopes required by this agent
GMAIL_READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
CALENDAR_READONLY_SCOPE = "https://www.googleapis.com/auth/calendar.readonly"

# Number of emails to fetch per incremental sync (caps LLM spend)
DEFAULT_BATCH_SIZE: int = int(os.getenv("INBOX_BATCH_SIZE", "25"))
DEEP_SYNC_BATCH_SIZE: int = int(os.getenv("INBOX_DEEP_SYNC_BATCH_SIZE", "100"))



# ---------------------------------------------------------------------------
# Credential helper
# ---------------------------------------------------------------------------

def _build_gmail_credentials(uid: str) -> Optional[Credentials]:
    """
    Builds a Google OAuth Credentials object from tokens stored in Firestore.
    Refreshes expired tokens automatically and persists the refreshed tokens.

    Returns None if no credentials are found or if they are invalid.
    """
    creds_model = get_stored_credentials(uid)
    if not creds_model:
        print(f"GMAIL SERVICE: No stored credentials found for user {uid}")
        return None
    if not creds_model.connected:
        print(f"GMAIL SERVICE: Credentials not marked as connected for user {uid}")
        return None

    creds = Credentials(
        token=creds_model.access_token,
        refresh_token=creds_model.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.getenv("OAUTH_CLIENT_ID"),
        client_secret=os.getenv("CLIENT_SECRET"),
        # Include both scopes — the same credential covers calendar + gmail
        scopes=[CALENDAR_READONLY_SCOPE, GMAIL_READONLY_SCOPE],
        expiry=datetime.fromtimestamp(creds_model.expires_at, tz=timezone.utc).replace(tzinfo=None),
    )

    if creds.expired and creds.refresh_token:
        logger.info("Google OAuth token expired for user '%s' — refreshing.", uid)
        try:
            creds.refresh(Request())
            _persist_refreshed_tokens(uid, creds)
        except Exception as exc:
            logger.error("Token refresh failed for user '%s': %s", uid, exc)
            print(f"GMAIL SERVICE: Token refresh failed for user {uid}: {exc}")
            return None

    return creds


def _persist_refreshed_tokens(uid: str, creds: Credentials) -> None:
    """Writes refreshed tokens back to Firestore (same path as calendar client)."""
    try:
        expires_at = (
            int(creds.expiry.timestamp())
            if creds.expiry
            else int((datetime.utcnow() + timedelta(hours=1)).timestamp())
        )
        firebase_db.collection("users").document(uid).collection("integrations").document(
            "google_calendar"
        ).update({
            "access_token": encrypt_token(creds.token),
            "refresh_token": encrypt_token(creds.refresh_token or ""),
            "expires_at": expires_at,
            "updated_at": int(datetime.utcnow().timestamp()),
        })
        logger.debug("Refreshed tokens persisted for user '%s'.", uid)
    except Exception as exc:
        logger.warning("Could not persist refreshed tokens for user '%s': %s", uid, exc)


# ---------------------------------------------------------------------------
# Service factory
# ---------------------------------------------------------------------------

def get_gmail_service(uid: str) -> Optional[Any]:
    """
    Builds and returns an authenticated Gmail API service client.
    Returns None if credentials are unavailable or invalid.
    """
    creds = _build_gmail_credentials(uid)
    if not creds:
        print(f"GMAIL SERVICE: Credentials build failed for user {uid}")
        return None
    try:
        service = build("gmail", "v1", credentials=creds)
        logger.debug("Gmail service built successfully for user '%s'.", uid)
        return service
    except Exception as exc:
        logger.error("Failed to build Gmail service for user '%s': %s", uid, exc)
        print(f"GMAIL SERVICE: API client build failed for user {uid}: {exc}")
        return None


# ---------------------------------------------------------------------------
# Sync state persistence
# ---------------------------------------------------------------------------

def load_sync_state(uid: str) -> InboxSyncState:
    """
    Loads persisted inbox sync state from Firestore.
    Returns a fresh InboxSyncState if none exists yet.
    """
    doc_ref = (
        firebase_db.collection("users")
        .document(uid)
        .collection("agent_state")
        .document("inbox_intelligence")
    )
    doc = doc_ref.get()
    if doc.exists:
        data = doc.to_dict()
        return InboxSyncState(**data)
    return InboxSyncState()


def save_sync_state(uid: str, state: InboxSyncState) -> None:
    """Persists inbox sync state to Firestore."""
    doc_ref = (
        firebase_db.collection("users")
        .document(uid)
        .collection("agent_state")
        .document("inbox_intelligence")
    )
    payload = state.model_dump()
    payload["last_run_at"] = datetime.utcnow().timestamp()
    doc_ref.set(payload)
    logger.debug("Inbox sync state saved for user '%s'.", uid)


# ---------------------------------------------------------------------------
# Email body extraction
# ---------------------------------------------------------------------------

def _decode_body_part(part: Dict[str, Any]) -> str:
    """Decodes a single MIME body part from base64url to plain text."""
    data = part.get("body", {}).get("data", "")
    if not data:
        return ""
    try:
        decoded = base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
        return decoded
    except Exception:
        return ""


def _extract_body(payload: Dict[str, Any]) -> str:
    """
    Recursively extracts the best readable body from a Gmail message payload.
    Prefers text/plain; falls back to text/html (stripped of tags).
    """
    mime_type = payload.get("mimeType", "")
    parts = payload.get("parts", [])

    if mime_type == "text/plain":
        return _decode_body_part(payload)

    if mime_type == "text/html":
        raw_html = _decode_body_part(payload)
        # Strip HTML tags for readability
        return re.sub(r"<[^>]+>", " ", raw_html).strip()

    # Multipart: recurse into parts
    plain_text = ""
    html_text = ""
    for part in parts:
        part_mime = part.get("mimeType", "")
        if part_mime == "text/plain":
            plain_text = _decode_body_part(part)
        elif part_mime == "text/html":
            raw_html = _decode_body_part(part)
            html_text = re.sub(r"<[^>]+>", " ", raw_html).strip()
        elif part_mime.startswith("multipart/"):
            nested = _extract_body(part)
            if nested:
                plain_text = nested
    return plain_text or html_text


def _parse_sender(sender_header: str) -> Tuple[str, str]:
    """
    Parses a 'From' header like 'John Doe <john@example.com>'
    Returns (display_name, email_address).
    """
    match = re.match(r"^(.*?)\s*<([^>]+)>$", sender_header.strip())
    if match:
        return match.group(1).strip().strip('"'), match.group(2).strip()
    # Raw email address
    return sender_header.strip(), sender_header.strip()


def _build_raw_email(message: Dict[str, Any]) -> Optional[RawEmail]:
    """Converts a Gmail API message dict into a normalised RawEmail."""
    try:
        message_id = message.get("id", "")
        thread_id = message.get("threadId", "")
        payload = message.get("payload", {})
        headers = {h["name"].lower(): h["value"] for h in payload.get("headers", [])}

        subject = headers.get("subject", "(no subject)")
        from_header = headers.get("from", "")
        to_header = headers.get("to", "")
        date_header = headers.get("date", "")

        sender_name, sender_email = _parse_sender(from_header)

        # Parse date
        date: Optional[datetime] = None
        if date_header:
            try:
                from email.utils import parsedate_to_datetime
                date = parsedate_to_datetime(date_header)
            except Exception:
                date = None

        body = _extract_body(payload)
        snippet = message.get("snippet", "")[:300]
        labels = message.get("labelIds", [])
        has_attachments = any(
            p.get("filename") for p in payload.get("parts", []) if p.get("filename")
        )

        return RawEmail(
            message_id=message_id,
            thread_id=thread_id,
            subject=subject,
            body=body,
            snippet=snippet,
            sender=sender_name,
            sender_email=sender_email,
            recipient=to_header,
            date=date,
            labels=labels,
            has_attachments=has_attachments,
        )
    except Exception as exc:
        logger.warning("Failed to parse message '%s': %s", message.get("id"), exc)
        return None


# ---------------------------------------------------------------------------
# Email fetching
# ---------------------------------------------------------------------------

def fetch_single_message(service: Any, message_id: str) -> Optional[Dict[str, Any]]:
    """Fetches a single Gmail message in full format."""
    try:
        return service.users().messages().get(
            userId="me",
            id=message_id,
            format="full"
        ).execute()
    except HttpError as exc:
        logger.warning("Gmail API error fetching message '%s': %s", message_id, exc)
        return None


def fetch_incremental_emails(
    uid: str,
    sync_state: InboxSyncState,
    batch_size: int = DEFAULT_BATCH_SIZE,
    deep_sync: bool = False,
) -> Tuple[List[RawEmail], str]:
    """
    Fetches new/modified emails since the last successful sync.

    Strategy:
    - If history_id is available and not deep_sync: use Gmail History API (most efficient).
    - Otherwise: use messages.list with `after:` search query.

    Returns:
    - emails: list of normalised RawEmail objects
    - new_history_id: the latest historyId to persist for next run
    """
    service = get_gmail_service(uid)
    if not service:
        logger.error("Cannot fetch emails: Gmail service unavailable for user '%s'.", uid)
        return [], sync_state.history_id or ""

    processed_ids: set = set(sync_state.processed_message_ids)
    raw_emails: List[RawEmail] = []
    new_history_id = sync_state.history_id or ""

    try:
        if sync_state.history_id and not deep_sync:
         
            try:
                logger.info(
                    "Incremental Gmail sync for user '%s' from history_id=%s.",
                    uid, sync_state.history_id
                )
                history_response = service.users().history().list(
                    userId="me",
                    startHistoryId=sync_state.history_id,
                    historyTypes=["messageAdded"],
                    maxResults=batch_size,
                ).execute()

                histories = history_response.get("history", [])
                new_history_id = history_response.get("historyId", new_history_id)
                message_ids_to_fetch: List[str] = []

                for history_item in histories:
                    for msg_added in history_item.get("messagesAdded", []):
                        msg_id = msg_added.get("message", {}).get("id", "")
                        if msg_id and msg_id not in processed_ids:
                            message_ids_to_fetch.append(msg_id)

                logger.info(
                    "History API returned %d new message(s) for user '%s'.",
                    len(message_ids_to_fetch), uid
                )
                for msg_id in message_ids_to_fetch[:batch_size]:
                    msg = fetch_single_message(service, msg_id)
                    if msg:
                        email = _build_raw_email(msg)
                        if email:
                            print(f"GMAIL SYNC: Fetched message ID '{msg_id}', Subject: '{email.subject}', Sender: '{email.sender}'")
                            raw_emails.append(email)
            except HttpError as hist_exc:
                status_code = hist_exc.resp.status if hist_exc.resp else 0
                if status_code in (400, 404):
                    logger.warning("Gmail history ID expired or invalid for user '%s'. Falling back to deep sync.", uid)
                    print(f"GMAIL SYNC: History ID {sync_state.history_id} expired. Falling back to full sync.")
                    profile = service.users().getProfile(userId="me").execute()
                    new_history_id = profile.get("historyId", "")
                    after_ts = int((datetime.utcnow() - timedelta(days=7)).timestamp())
                    query = f"after:{after_ts} -label:SENT"
                    list_response = service.users().messages().list(
                        userId="me",
                        q=query,
                        maxResults=batch_size,
                    ).execute()
                    messages = list_response.get("messages", [])
                    for msg_stub in messages:
                        msg_id = msg_stub.get("id", "")
                        if msg_id and msg_id not in processed_ids:
                            msg = fetch_single_message(service, msg_id)
                            if msg:
                                email = _build_raw_email(msg)
                                if email:
                                    raw_emails.append(email)
                else:
                    raise

        else:
            # --- First-time or Deep sync: fetch recent emails ---
            if deep_sync:
                logger.info("Deep Gmail sync for user '%s'.", uid)
            else:
                logger.info("First-time Gmail sync for user '%s'.", uid)
            # Get profile to obtain current historyId baseline
            profile = service.users().getProfile(userId="me").execute()
            new_history_id = profile.get("historyId", "")

            # Fetch recent emails (last 7 days to limit scope)
            after_ts = int(
                (datetime.utcnow() - timedelta(days=7)).timestamp()
            )
            query = f"after:{after_ts} -label:SENT"
            limit = DEEP_SYNC_BATCH_SIZE if deep_sync else batch_size
            list_response = service.users().messages().list(
                userId="me",
                q=query,
                maxResults=limit,
            ).execute()

            messages = list_response.get("messages", [])
            logger.info(
                "Sync: %d messages found for user '%s'.", len(messages), uid
            )

            skipped_count = 0
            for msg_stub in messages:
                msg_id = msg_stub.get("id", "")
                if msg_id in processed_ids:
                    skipped_count += 1
                    continue
                if msg_id:
                    msg = fetch_single_message(service, msg_id)
                    if msg:
                        email = _build_raw_email(msg)
                        if email:
                            raw_emails.append(email)

    except HttpError as exc:
        status_code = exc.resp.status if exc.resp else 0
        if status_code == 401:
            logger.error("Gmail auth error for user '%s': token invalid or missing scope.", uid)
        elif status_code == 429:
            logger.warning("Gmail rate limit hit for user '%s'.", uid)
        else:
            logger.error("Gmail API error for user '%s': %s", uid, exc)
    except Exception as exc:
        logger.error("Unexpected error during Gmail sync for user '%s': %s", uid, exc)

    logger.info(
        "Gmail sync complete for user '%s': %d email(s) fetched.", uid, len(raw_emails)
    )
    return raw_emails, new_history_id
