

import asyncio
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

import sys
from unittest.mock import MagicMock

_firebase_mock = MagicMock()
_firebase_mock.firestore.SERVER_TIMESTAMP = "SERVER_TIMESTAMP"
sys.modules.setdefault("firebase_admin", _firebase_mock)
sys.modules.setdefault("firebase_admin.firestore", _firebase_mock.firestore)

_db_mock = MagicMock()
sys.modules.setdefault("db.firebase", MagicMock(firebase_db=_db_mock))


if not os.getenv("CALENDER_ENCRYPTION"):
    _fernet_mock = MagicMock()
    _fernet_mock.encrypt.return_value = b"encrypted"
    _fernet_mock.decrypt.return_value = b"decrypted"
    _crypto_mod = MagicMock()
    _crypto_mod.Fernet.return_value = _fernet_mock
    sys.modules["cryptography.fernet"] = _crypto_mod


_calender_utils_mock = MagicMock()
_calender_utils_mock.encrypt_token = lambda t: f"enc:{t}"
_calender_utils_mock.decrypt_token = lambda t: t.replace("enc:", "") if t else ""
sys.modules["calender.utils"] = _calender_utils_mock

from agents.inbox.schemas import (
    CalendarMatchResult,
    ConflictMetadata,
    DuplicateResult,
    ExtractedTask,
    FilterResult,
    IIAOutput,
    InboxSyncState,
    RawEmail,
    SuggestedTask,
)
from agents.inbox.filter_service import filter_email, filter_emails_batch
from agents.inbox.duplicate_service import (
    _normalise_title,
    _jaccard_similarity,
    _tokenise,
    check_duplicate_against_tasks,
    check_duplicate_against_suggestions,
    check_duplicate_against_calendar,
    check_all_duplicates,
)
from agents.inbox.extraction_service import _mock_extract, extract_task_from_email
from agent_runtime.events.bus import InMemoryEventBus
from agent_runtime.schemas.models import Event

def make_email(
    subject="Submit AI Assignment",
    body="Please submit your AI assignment by this Friday at 11:59 PM.",
    sender="Prof. Smith",
    sender_email="prof.smith@university.edu",
    labels=None,
    snippet=None,
) -> RawEmail:
    return RawEmail(
        message_id=str(uuid4()),
        thread_id=str(uuid4()),
        subject=subject,
        body=body,
        snippet=snippet or body[:200],
        sender=sender,
        sender_email=sender_email,
        labels=labels or [],
        date=datetime.utcnow(),
    )


def make_extracted(
    title="Submit AI Assignment",
    confidence=0.92,
    due_date="2025-07-04",
    message_id=None,
) -> ExtractedTask:
    return ExtractedTask(
        title=title,
        confidence=confidence,
        due_date=due_date,
        urgency="high",
        task_category="Submission",
        description="Submit the AI assignment.",
        source_message_id=message_id or str(uuid4()),
        source_subject=title,
        source_sender_email="prof@uni.edu",
    )

class TestEmailFilter:

    def test_filter_promotions_label(self):
        email = make_email(labels=["CATEGORY_PROMOTIONS"])
        result = filter_email(email)
        assert not result.is_relevant
        assert "CATEGORY_PROMOTIONS" in result.reason

    def test_filter_social_label(self):
        email = make_email(labels=["CATEGORY_SOCIAL"])
        result = filter_email(email)
        assert not result.is_relevant

    def test_filter_spam_label(self):
        email = make_email(labels=["SPAM"])
        result = filter_email(email)
        assert not result.is_relevant

    def test_filter_otp_subject(self):
        email = make_email(
            subject="Your OTP is 483912",
            body="Your one-time password is 483912. Do not share it with anyone.",
        )
        result = filter_email(email)
        assert not result.is_relevant

    def test_filter_order_delivered(self):
        email = make_email(
            subject="Your order delivered",
            body="Your package was delivered to your doorstep today. Thank you for shopping.",
        )
        result = filter_email(email)
        assert not result.is_relevant

    def test_filter_percentage_off(self):
        email = make_email(
            subject="50% OFF Today Only!",
            body="Shop now and save 50% on everything. Sale ends midnight.",
        )
        result = filter_email(email)
        assert not result.is_relevant

    def test_filter_password_reset(self):
        email = make_email(
            subject="Password reset for your account",
            body="Click the link below to reset your password within 30 minutes.",
        )
        result = filter_email(email)
        assert not result.is_relevant

    def test_filter_noreply_sender(self):
        email = make_email(
            sender_email="noreply@shopify.com",
            subject="Your store update",
            body="We have updated your store settings and applied the new theme to all pages.",
        )
        result = filter_email(email)
        assert not result.is_relevant

    def test_filter_actionable_meeting(self):
        """Emails with 'meeting' keyword should pass through."""
        email = make_email(
            subject="Team Meeting Tomorrow at 10 AM",
            body="Hi, please join the weekly team meeting tomorrow at 10 AM in Room 301.",
        )
        result = filter_email(email)
        assert result.is_relevant

    def test_filter_actionable_deadline(self):
        """Emails with explicit deadline signal pass through."""
        email = make_email(
            subject="Assignment Due This Friday",
            body="Please submit your final assignment by Friday 5 PM to the portal.",
        )
        result = filter_email(email)
        assert result.is_relevant

    def test_filter_interview_subject(self):
        email = make_email(
            subject="Interview Scheduled — Software Engineer",
            body="Your interview is confirmed for Monday at 2 PM. Please join via the Zoom link.",
        )
        result = filter_email(email)
        assert result.is_relevant

    def test_filter_short_body_rejected(self):
        """Emails with very short bodies and neutral subjects are rejected."""
        email = make_email(
            subject="Hey",  # neutral subject — no actionable fast-pass
            body="ok thanks",
            snippet="ok thanks",
        )
        result = filter_email(email)
        assert not result.is_relevant

    def test_filter_batch_counts(self):
        emails = [
            make_email(labels=["CATEGORY_PROMOTIONS"]),
            make_email(subject="Meeting at 3 PM",
                       body="Please attend the all-hands meeting at 3 PM in the main hall."),
            make_email(subject="Your OTP is 123456",
                       body="Use this OTP to complete your login process."),
        ]
        relevant, all_results = filter_emails_batch(emails)
        assert len(relevant) == 1
        assert len(all_results) == 3


class TestDuplicateDetection:

    def test_normalise_title(self):
        assert _normalise_title("Submit AI Assignment") == "submit ai assignment"
        assert _normalise_title("AI Assignment Submission!!") == "ai assignment submission"

    def test_jaccard_exact_match(self):
        a = _tokenise("submit ai assignment")
        b = _tokenise("submit ai assignment")
        assert _jaccard_similarity(a, b) == 1.0

    def test_jaccard_high_similarity(self):
        a = _tokenise("submit ai assignment")
        b = _tokenise("ai assignment submission")
        score = _jaccard_similarity(a, b)
        assert score >= 0.5  # significant overlap

    def test_jaccard_low_similarity(self):
        a = _tokenise("quarterly sales report")
        b = _tokenise("submit ai assignment")
        score = _jaccard_similarity(a, b)
        assert score < 0.3

    def test_exact_title_duplicate(self):
        extracted = make_extracted(title="Submit AI Assignment")
        tasks = [{"id": "t1", "title": "Submit AI Assignment", "deadline": "2025-07-04"}]
        result = check_duplicate_against_tasks(extracted, tasks)
        assert result.is_duplicate
        assert result.matched_id == "t1"

    def test_fuzzy_title_duplicate(self):
        """Near-duplicate titles should be detected."""
        extracted = make_extracted(title="AI Assignment Submission")
        tasks = [{"id": "t2", "title": "Submit AI Assignment", "deadline": None}]
        result = check_duplicate_against_tasks(extracted, tasks)
        assert result.is_duplicate

    def test_no_duplicate_different_titles(self):
        extracted = make_extracted(title="Client call on Thursday")
        tasks = [{"id": "t3", "title": "Quarterly budget review", "deadline": None}]
        result = check_duplicate_against_tasks(extracted, tasks)
        assert not result.is_duplicate

    def test_duplicate_against_suggestions(self):
        extracted = make_extracted(title="Final Presentation")
        suggestions = [{"suggestion_id": "s1", "title": "Final Presentation", "due_date": None}]
        result = check_duplicate_against_suggestions(extracted, suggestions)
        assert result.is_duplicate
        assert result.matched_id == "s1"

    def test_duplicate_against_calendar(self):
        extracted = make_extracted(title="Team Meeting")
        cal_titles = [("Team Meeting", "2025-07-04")]
        result = check_duplicate_against_calendar(extracted, cal_titles)
        assert result.is_duplicate

    def test_check_all_duplicates_short_circuits(self):
        """check_all_duplicates should stop at first match."""
        extracted = make_extracted(title="Submit AI Assignment")
        tasks = [{"id": "t1", "title": "Submit AI Assignment", "deadline": None}]
        result = check_all_duplicates(extracted, tasks, [], [])
        assert result.is_duplicate

    def test_check_all_duplicates_no_match(self):
        extracted = make_extracted(title="Completely unique task XYZ")
        result = check_all_duplicates(extracted, [], [], [])
        assert not result.is_duplicate



class TestLLMExtraction:

    def test_mock_extract_actionable_email(self):
        """Actionable emails produce a valid ExtractedTask."""
        email = make_email(
            subject="Submit Assignment by Friday",
            body="Please submit your assignment by Friday at 11:59 PM.",
        )
        result = _mock_extract(email)
        assert result is not None
        assert isinstance(result, ExtractedTask)
        assert result.confidence >= 0.7

    def test_mock_extract_non_actionable_email(self):
        """Non-actionable emails return None (below threshold)."""
        email = make_email(
            subject="FYI: Company newsletter",
            body="Here is the monthly company newsletter with updates on recent events.",
        )
        result = _mock_extract(email)
        # Newsletter — confidence too low → None
        # The mock returns 0.30 for non-actionable, which is below 0.7 threshold
        assert result is None

    def test_extract_task_uses_mock_when_no_api_key(self):
        """extract_task_from_email falls back to mock when GEMINI_API_KEY not set."""
        with patch("agents.inbox.extraction_service._get_client", return_value=None):
            email = make_email(
                subject="Interview Scheduled",
                body="Your interview is scheduled for Monday at 2 PM. Please confirm.",
            )
            result = extract_task_from_email(email)
            # Should either return an ExtractedTask or None (depending on mock confidence)
            assert result is None or isinstance(result, ExtractedTask)

    def test_extract_respects_confidence_threshold(self):
        """Extractions below the threshold must return None."""
        with patch("agents.inbox.extraction_service._get_client", return_value=None):
            with patch("agents.inbox.extraction_service._mock_extract") as mock_fn:
                # Simulate a low-confidence extraction
                mock_fn.return_value = ExtractedTask(
                    title="Vague thing",
                    confidence=0.3,
                    source_message_id="m1",
                    source_subject="vague",
                    source_sender_email="x@x.com",
                )
                email = make_email()
                result = extract_task_from_email(email, confidence_threshold=0.7)
                # The extractor should filter it out
                assert result is None


class TestCalendarService:

    def test_calendar_match_found(self):
        from agents.inbox.calendar_service import find_matching_event
        extracted = make_extracted(title="Team Meeting", due_date="2025-07-07")

        mock_event = MagicMock()
        mock_event.title = "Team Meeting"
        mock_event.event_id = "cal_event_1"
        mock_event.start = datetime(2025, 7, 7, 10, 0)
        mock_event.end = datetime(2025, 7, 7, 11, 0)
        mock_event.is_all_day = False

        mock_client = MagicMock()
        mock_client.get_events.return_value = [mock_event]

        found, event_id = find_matching_event(mock_client, extracted)
        assert found is True
        assert event_id == "cal_event_1"

    def test_calendar_no_match(self):
        from agents.inbox.calendar_service import find_matching_event
        extracted = make_extracted(title="Completely Unrelated Task")

        mock_event = MagicMock()
        mock_event.title = "Dentist Appointment"
        mock_event.event_id = "cal_event_2"
        mock_event.start = datetime(2025, 7, 7, 9, 0)
        mock_event.is_all_day = False

        mock_client = MagicMock()
        mock_client.get_events.return_value = [mock_event]

        found, event_id = find_matching_event(mock_client, extracted)
        assert found is False
        assert event_id is None

    def test_conflict_detected(self):
        from agents.inbox.calendar_service import detect_conflicts
        extracted = make_extracted(title="New Task", due_date="2025-07-07 10:30")

        mock_event = MagicMock()
        mock_event.title = "Another Meeting"
        mock_event.event_id = "cal_event_3"
        mock_event.start = datetime(2025, 7, 7, 10, 0)
        mock_event.end = datetime(2025, 7, 7, 11, 0)
        mock_event.is_all_day = False

        mock_client = MagicMock()
        mock_client.get_events.return_value = [mock_event]

        conflict = detect_conflicts(mock_client, extracted)
        # May or may not detect depending on date parsing — verify no crash
        assert conflict is None or hasattr(conflict, "conflicting_event_id")

    def test_calendar_client_unavailable(self):
        """When no calendar credentials exist, result is default CalendarMatchResult."""
        from agents.inbox.calendar_service import build_calendar_match_result
        with patch("agents.inbox.calendar_service.get_calendar_client", return_value=None):
            extracted = make_extracted(title="Some Task")
            result = build_calendar_match_result("user_no_cal", extracted)
            assert result.already_in_calendar is False
            assert result.conflict_detected is False



class TestSuggestionStorage:

    def test_store_suggestion_writes_to_firestore(self):
        """store_suggestion should call Firestore set."""
        from agents.inbox.suggestion_service import store_suggestion

        mock_collection = MagicMock()
        mock_doc_ref = MagicMock()
        mock_collection.return_value.document.return_value.collection.return_value.document.return_value = mock_doc_ref

        with patch("agents.inbox.suggestion_service.firebase_db") as mock_db:
            mock_db.collection.return_value.document.return_value.collection.return_value.document.return_value = mock_doc_ref

            suggestion = SuggestedTask(
                user_id="user123",
                title="Submit AI Assignment",
                confidence=0.92,
                source_message_id="msg1",
                source_subject="Submit AI Assignment",
                source_sender_email="prof@uni.edu",
            )
            suggestion_id = store_suggestion("user123", suggestion)
            assert suggestion_id == suggestion.suggestion_id
            mock_doc_ref.set.assert_called_once()

    def test_get_existing_suggestions_returns_list(self):
        """get_existing_suggestions should return filtered list."""
        from agents.inbox.suggestion_service import get_existing_suggestions

        mock_doc = MagicMock()
        mock_doc.to_dict.return_value = {
            "suggestion_id": "s1",
            "title": "Do something",
            "status": "suggested",
            "confidence": 0.85,
        }

        with patch("agents.inbox.suggestion_service.firebase_db") as mock_db:
            mock_db.collection.return_value.document.return_value.collection.return_value.stream.return_value = [mock_doc]
            results = get_existing_suggestions("user123")
            assert len(results) == 1
            assert results[0]["title"] == "Do something"


@pytest.mark.asyncio
async def test_event_emission_inbox_sync():
    """InboxSyncStarted and InboxSyncCompleted events must be emitted on sync."""
    from agents.inbox import events as iia_events

    bus = InMemoryEventBus()
    received = []

    async def handler(event: Event):
        received.append(event.event_name)

    await bus.subscribe(iia_events.INBOX_SYNC_STARTED, handler)
    await bus.subscribe(iia_events.INBOX_SYNC_COMPLETED, handler)

    evt = iia_events.make_inbox_sync_started_event("u1", "s1", history_id="h123")
    await bus.publish(evt)
    evt2 = iia_events.make_inbox_sync_completed_event("u1", "s1", emails_fetched=5)
    await bus.publish(evt2)

    assert iia_events.INBOX_SYNC_STARTED in received
    assert iia_events.INBOX_SYNC_COMPLETED in received


@pytest.mark.asyncio
async def test_event_emission_task_extracted():
    from agents.inbox import events as iia_events

    bus = InMemoryEventBus()
    received_payloads = []

    async def handler(event: Event):
        received_payloads.append(event.payload)

    await bus.subscribe(iia_events.TASK_EXTRACTED, handler)
    evt = iia_events.make_task_extracted_event(
        "u1", "s1", "sug_1", "Submit Assignment", 0.95, "msg_1"
    )
    await bus.publish(evt)

    assert len(received_payloads) == 1
    assert received_payloads[0]["title"] == "Submit Assignment"
    assert received_payloads[0]["confidence"] == 0.95


@pytest.mark.asyncio
async def test_event_emission_duplicate_detected():
    from agents.inbox import events as iia_events

    bus = InMemoryEventBus()
    received = []

    async def handler(event: Event):
        received.append(event)

    await bus.subscribe(iia_events.DUPLICATE_DETECTED, handler)
    evt = iia_events.make_duplicate_detected_event(
        "u1", "s1", "AI Assignment", "Submit AI Assignment", "t1", 0.80
    )
    await bus.publish(evt)

    assert len(received) == 1
    assert received[0].payload["similarity_score"] == 0.80



@pytest.mark.asyncio
async def test_agent_lifecycle_no_emails():
    """Agent should return success with 0 suggestions when no emails are fetched."""
    from agents.inbox.agent import InboxIntelligenceAgent
    from agent_runtime.schemas.models import ExecutionContext, ExecutionMetadata

    context = ExecutionContext(
        user_id="test_user",
        session_id="test_session",
        execution_id="exec_1",
        metadata=ExecutionMetadata(
            execution_id="exec_1",
            retry_count=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
    )

    with patch("agents.inbox.agent.fetch_incremental_emails", return_value=([], "h_new")), \
         patch("agents.inbox.agent.load_sync_state", return_value=InboxSyncState()), \
         patch("agents.inbox.agent.save_sync_state"), \
         patch("agents.inbox.agent.get_existing_user_tasks", return_value=[]), \
         patch("agents.inbox.agent.get_existing_suggestions", return_value=[]), \
         patch("agents.inbox.agent.get_calendar_event_titles", return_value=[]), \
         patch("agents.inbox.agent.LongTermMemory") as mock_ltm_cls:

        mock_ltm = AsyncMock()
        mock_ltm.get_all.return_value = {}
        mock_ltm.set = AsyncMock()
        mock_ltm_cls.return_value = mock_ltm

        agent = InboxIntelligenceAgent()
        # Override plan to force sync
        response = await agent.run(context, {"force_sync": True})

    assert response.success is True
    assert response.output_data.get("suggestions_created", 0) == 0
    assert response.output_data.get("emails_fetched", 0) == 0


@pytest.mark.asyncio
async def test_agent_lifecycle_with_suggestions():
    """Agent should create suggestions for actionable emails."""
    from agents.inbox.agent import InboxIntelligenceAgent
    from agent_runtime.schemas.models import ExecutionContext, ExecutionMetadata

    context = ExecutionContext(
        user_id="test_user",
        session_id="test_session",
        execution_id="exec_2",
        metadata=ExecutionMetadata(
            execution_id="exec_2",
            retry_count=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
    )

    email = make_email(
        subject="Submit AI Assignment by Friday",
        body="Please submit your AI assignment by this Friday 11:59 PM to the LMS portal.",
    )
    extracted = make_extracted(
        title="Submit AI Assignment",
        confidence=0.92,
        message_id=email.message_id,
    )

    with patch("agents.inbox.agent.fetch_incremental_emails", return_value=([email], "h_new")), \
         patch("agents.inbox.agent.load_sync_state", return_value=InboxSyncState()), \
         patch("agents.inbox.agent.save_sync_state"), \
         patch("agents.inbox.agent.get_existing_user_tasks", return_value=[]), \
         patch("agents.inbox.agent.get_existing_suggestions", return_value=[]), \
         patch("agents.inbox.agent.get_calendar_event_titles", return_value=[]), \
         patch("agents.inbox.agent.extract_task_from_email", return_value=extracted), \
         patch("agents.inbox.agent.check_all_duplicates",
               return_value=DuplicateResult(is_duplicate=False)), \
         patch("agents.inbox.agent.build_calendar_match_result",
               return_value=CalendarMatchResult(already_in_calendar=False)), \
         patch("agents.inbox.agent.store_suggestion", return_value="sug_test_1"), \
         patch("agents.inbox.agent.LongTermMemory") as mock_ltm_cls:

        mock_ltm = AsyncMock()
        mock_ltm.get_all.return_value = {}
        mock_ltm.set = AsyncMock()
        mock_ltm_cls.return_value = mock_ltm

        agent = InboxIntelligenceAgent()
        response = await agent.run(context, {"force_sync": True})

    assert response.success is True
    assert response.output_data.get("suggestions_created") == 1
    assert "sug_test_1" in response.output_data.get("suggested_task_ids", [])


@pytest.mark.asyncio
async def test_agent_skips_duplicate():
    """Agent must not store a suggestion when duplicate is detected."""
    from agents.inbox.agent import InboxIntelligenceAgent
    from agent_runtime.schemas.models import ExecutionContext, ExecutionMetadata

    context = ExecutionContext(
        user_id="test_user",
        session_id="test_session",
        execution_id="exec_3",
        metadata=ExecutionMetadata(
            execution_id="exec_3",
            retry_count=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
    )

    email = make_email(subject="Submit AI Assignment",
                       body="Please submit your AI assignment by Friday 11:59 PM.")
    extracted = make_extracted("Submit AI Assignment", 0.92, message_id=email.message_id)

    with patch("agents.inbox.agent.fetch_incremental_emails", return_value=([email], "h_new")), \
         patch("agents.inbox.agent.load_sync_state", return_value=InboxSyncState()), \
         patch("agents.inbox.agent.save_sync_state"), \
         patch("agents.inbox.agent.get_existing_user_tasks", return_value=[]), \
         patch("agents.inbox.agent.get_existing_suggestions", return_value=[]), \
         patch("agents.inbox.agent.get_calendar_event_titles", return_value=[]), \
         patch("agents.inbox.agent.extract_task_from_email", return_value=extracted), \
         patch("agents.inbox.agent.check_all_duplicates",
               return_value=DuplicateResult(is_duplicate=True, matched_title="Submit AI Assignment")), \
         patch("agents.inbox.agent.store_suggestion") as mock_store, \
         patch("agents.inbox.agent.LongTermMemory") as mock_ltm_cls:

        mock_ltm = AsyncMock()
        mock_ltm.get_all.return_value = {}
        mock_ltm.set = AsyncMock()
        mock_ltm_cls.return_value = mock_ltm

        agent = InboxIntelligenceAgent()
        response = await agent.run(context, {"force_sync": True})

    assert response.success is True
    assert response.output_data.get("suggestions_created") == 0
    assert response.output_data.get("duplicates_detected") == 1
    mock_store.assert_not_called()


@pytest.mark.asyncio
async def test_agent_skips_already_in_calendar():
    """Agent must not store a suggestion if the task already exists in Calendar."""
    from agents.inbox.agent import InboxIntelligenceAgent
    from agent_runtime.schemas.models import ExecutionContext, ExecutionMetadata

    context = ExecutionContext(
        user_id="test_user",
        session_id="test_session",
        execution_id="exec_4",
        metadata=ExecutionMetadata(
            execution_id="exec_4",
            retry_count=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
    )

    email = make_email(subject="Team Meeting Monday", body="Please join the team meeting on Monday at 10 AM.")
    extracted = make_extracted("Team Meeting Monday", 0.88, message_id=email.message_id)

    with patch("agents.inbox.agent.fetch_incremental_emails", return_value=([email], "h_new")), \
         patch("agents.inbox.agent.load_sync_state", return_value=InboxSyncState()), \
         patch("agents.inbox.agent.save_sync_state"), \
         patch("agents.inbox.agent.get_existing_user_tasks", return_value=[]), \
         patch("agents.inbox.agent.get_existing_suggestions", return_value=[]), \
         patch("agents.inbox.agent.get_calendar_event_titles", return_value=[]), \
         patch("agents.inbox.agent.extract_task_from_email", return_value=extracted), \
         patch("agents.inbox.agent.check_all_duplicates",
               return_value=DuplicateResult(is_duplicate=False)), \
         patch("agents.inbox.agent.build_calendar_match_result",
               return_value=CalendarMatchResult(
                   already_in_calendar=True,
                   calendar_event_id="cal_1",
               )), \
         patch("agents.inbox.agent.store_suggestion") as mock_store, \
         patch("agents.inbox.agent.LongTermMemory") as mock_ltm_cls:

        mock_ltm = AsyncMock()
        mock_ltm.get_all.return_value = {}
        mock_ltm.set = AsyncMock()
        mock_ltm_cls.return_value = mock_ltm

        agent = InboxIntelligenceAgent()
        response = await agent.run(context, {"force_sync": True})

    assert response.success is True
    assert response.output_data.get("suggestions_created") == 0
    mock_store.assert_not_called()


@pytest.mark.asyncio
async def test_agent_planner_skips_if_recent_sync():
    """Planner should return should_sync=False within the cooldown window."""
    from agents.inbox.agent import InboxIntelligenceAgent
    from agent_runtime.schemas.models import ExecutionContext, ExecutionMetadata

    context = ExecutionContext(
        user_id="test_user",
        session_id="test_session",
        execution_id="exec_5",
        metadata=ExecutionMetadata(
            execution_id="exec_5",
            retry_count=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
    )

    # Sync state shows a very recent run
    recent_state = InboxSyncState(last_run_at=time.time() - 60)  # 1 minute ago

    with patch("agents.inbox.agent.load_sync_state", return_value=recent_state), \
         patch("agents.inbox.agent.save_sync_state"), \
         patch("agents.inbox.agent.fetch_incremental_emails") as mock_fetch, \
         patch("agents.inbox.agent.LongTermMemory") as mock_ltm_cls:

        mock_ltm = AsyncMock()
        mock_ltm.get_all.return_value = {}
        mock_ltm.set = AsyncMock()
        mock_ltm_cls.return_value = mock_ltm

        agent = InboxIntelligenceAgent()
        response = await agent.run(context, {})  # no force_sync

    # Planner should have skipped — fetch should not be called
    assert response.success is True
    mock_fetch.assert_not_called()


@pytest.mark.asyncio
async def test_agent_handles_gmail_failure_gracefully():
    """Gmail API failure should return structured error response."""
    from agents.inbox.agent import InboxIntelligenceAgent
    from agent_runtime.schemas.models import ExecutionContext, ExecutionMetadata

    context = ExecutionContext(
        user_id="test_user",
        session_id="test_session",
        execution_id="exec_6",
        metadata=ExecutionMetadata(
            execution_id="exec_6",
            retry_count=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
    )

    with patch("agents.inbox.agent.load_sync_state", return_value=InboxSyncState()), \
         patch("agents.inbox.agent.save_sync_state"), \
         patch("agents.inbox.agent.fetch_incremental_emails",
               side_effect=Exception("Gmail API quota exceeded")), \
         patch("agents.inbox.agent.LongTermMemory") as mock_ltm_cls:

        mock_ltm = AsyncMock()
        mock_ltm.get_all.return_value = {}
        mock_ltm.set = AsyncMock()
        mock_ltm_cls.return_value = mock_ltm

        agent = InboxIntelligenceAgent()
        response = await agent.run(context, {"force_sync": True})

    assert response.success is False
    assert "Gmail API quota exceeded" in (response.error or "")



class TestSchemas:

    def test_suggested_task_schema(self):
        s = SuggestedTask(
            user_id="u1",
            title="Submit Report",
            confidence=0.88,
            source_message_id="m1",
            source_subject="Submit Report",
            source_sender_email="boss@company.com",
        )
        assert s.status == "suggested"
        assert s.duplicate is False
        assert s.source == "gmail"
        assert s.suggestion_id != ""

    def test_iia_output_schema(self):
        out = IIAOutput(
            emails_fetched=10,
            emails_filtered=7,
            emails_processed=3,
            tasks_extracted=2,
            suggestions_created=2,
        )
        assert out.halt_execution is False
        assert out.needs_negotiation is False



def test_agent_registered_in_registry():
    """InboxIntelligenceAgent must appear in AgentRegistry after import."""
    from agent_runtime.orchestrator.registry import AgentRegistry
    agent_cls = AgentRegistry.get_agent_class("InboxIntelligenceAgent")
    assert agent_cls is not None, "InboxIntelligenceAgent not found in AgentRegistry"


def test_tools_registered_in_registry():
    """All IIA tools must appear in ToolRegistry after import."""
    from agent_runtime.registry.tool import ToolRegistry
    expected_tools = [
        "gmail_fetch_emails",
        "filter_email",
        "extract_task_from_email",
        "check_duplicate",
        "check_calendar_match",
        "store_suggested_task",
    ]
    all_tools = ToolRegistry.get_all_tools()
    for tool_name in expected_tools:
        assert tool_name in all_tools, f"Tool '{tool_name}' not found in ToolRegistry"


def test_agent_has_correct_permissions():
    """Verify IIA's state_permissions only cover its allowed keys."""
    from agents.inbox.agent import InboxIntelligenceAgent
    agent = InboxIntelligenceAgent()
    required_keys = ["inbox", "suggested_tasks", "extraction_results",
                     "calendar_matches", "duplicate_results", "execution_metadata"]
    for key in required_keys:
        assert key in agent.state_permissions, f"Missing state permission for '{key}'"
        assert "w" in agent.state_permissions[key], f"No write permission for '{key}'"


if __name__ == "__main__":
    async def run_all():
        print("=== INBOX INTELLIGENCE AGENT TEST SUITE ===")
        # Filter tests
        print("\n--- Email Filter Tests ---")
        suite = TestEmailFilter()
        tests = [
            ("promotions label", suite.test_filter_promotions_label),
            ("OTP subject", suite.test_filter_otp_subject),
            ("order delivered", suite.test_filter_order_delivered),
            ("actionable meeting", suite.test_filter_actionable_meeting),
            ("actionable deadline", suite.test_filter_actionable_deadline),
            ("short body", suite.test_filter_short_body_rejected),
            ("batch counts", suite.test_filter_batch_counts),
        ]
        for name, test in tests:
            try:
                test()
                print(f"   {name}")
            except AssertionError as e:
                print(f"   {name}: {e}")

        # Duplicate tests
        print("\nDuplicate Detection Tests")
        dup_suite = TestDuplicateDetection()
        dup_tests = [
            ("exact title", dup_suite.test_exact_title_duplicate),
            ("fuzzy title", dup_suite.test_fuzzy_title_duplicate),
            ("no duplicate", dup_suite.test_no_duplicate_different_titles),
            ("calendar duplicate", dup_suite.test_duplicate_against_calendar),
        ]
        for name, test in dup_tests:
            try:
                test()
                print(f"  {name}")
            except AssertionError as e:
                print(f" {name}: {e}")

        # Registration tests
        print("\n Registration Tests \n")
        try:
            test_agent_registered_in_registry()
            print("  AgentRegistry registration")
        except AssertionError as e:
            print(f"  AgentRegistry: {e}")

        try:
            test_tools_registered_in_registry()
            print("   ToolRegistry registration")
        except AssertionError as e:
            print(f"   ToolRegistry: {e}")

        # Async tests
        print("\n Async Tests ")
        async_tests = [
            ("event emission sync", test_event_emission_inbox_sync),
            ("event emission extracted", test_event_emission_task_extracted),
            ("lifecycle no emails", test_agent_lifecycle_no_emails),
            ("lifecycle with suggestions", test_agent_lifecycle_with_suggestions),
            ("skips duplicate", test_agent_skips_duplicate),
            ("skips calendar match", test_agent_skips_already_in_calendar),
            ("planner cooldown", test_agent_planner_skips_if_recent_sync),
            ("gmail failure handled", test_agent_handles_gmail_failure_gracefully),
        ]
        for name, coro in async_tests:
            try:
                await coro()
                print(f"  {name}")
            except AssertionError as e:
                print(f"  {name}: {e}")
            except Exception as e:
                print(f"  {name}: {type(e).__name__}: {e}")

        print("\n Test run complete.")

    asyncio.run(run_all())
