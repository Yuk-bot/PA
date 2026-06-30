"""
Inbox Intelligence Agent — Agent 0

Extends BaseRuntimeAgent and is registered as "InboxIntelligenceAgent" in
the AgentRegistry. The planner's plan_steps() already includes this name
as the first step in the sequential workflow.

Responsibilities (ONLY these):
  - Read Gmail incrementally via stored OAuth credentials
  - Filter irrelevant emails (rule-based)
  - Extract actionable tasks via LLM (Gemini)
  - Detect duplicates against existing tasks, suggestions, and calendar events
  - Cross-reference with Google Calendar
  - Assign confidence scores and reject low-confidence results
  - Store SuggestedTask documents in Firestore
  - Update runtime state, memory, and emit events

NOT responsible for:
  - Prioritisation
  - Scheduling
  - Task decomposition
  - Actual task creation
  - Notifications
  - Calendar modification

Runtime Lifecycle (strictly followed):
  1. Receive Context
  2. Read Session State
  3. Read Memory
  4. Plan (internal planner)
  5. Execute
  6. Evaluate (done by ExecutionEngine post-run)
  7. Update State
  8. Update Memory
  9. Emit Events
  10. Return AgentResponse
"""

from __future__ import annotations

import datetime
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from agent_runtime.base.agent import BaseRuntimeAgent
from agent_runtime.config import settings
from agent_runtime.events.bus import InMemoryEventBus
from agent_runtime.memory.long_term import LongTermMemory
from agent_runtime.memory.session import SessionMemory
from agent_runtime.memory.working import WorkingMemory
from agent_runtime.orchestrator.registry import AgentRegistry, register_agent
from agent_runtime.schemas.models import AgentResponse, ExecutionContext

from agents.inbox.schemas import (
    ExtractedTask,
    IIAExecutionPlan,
    IIAOutput,
    InboxSyncState,
    RawEmail,
    SuggestedTask,
)
from agents.inbox import events as iia_events
from agents.inbox.calendar_service import build_calendar_match_result, get_calendar_event_titles
from agents.inbox.duplicate_service import check_all_duplicates
from agents.inbox.extraction_service import extract_task_from_email
from agents.inbox.filter_service import filter_emails_batch
from agents.inbox.gmail_service import (
    fetch_incremental_emails,
    load_sync_state,
    save_sync_state,
)
from agents.inbox.suggestion_service import (
    get_existing_suggestions,
    get_existing_user_tasks,
    store_suggestion,
)

logger = logging.getLogger("agents.inbox.agent")


# ---------------------------------------------------------------------------
# Shared event bus (singleton per process)
# ---------------------------------------------------------------------------

_event_bus = InMemoryEventBus()


# ---------------------------------------------------------------------------
# Agent definition
# ---------------------------------------------------------------------------

@register_agent("InboxIntelligenceAgent")
class InboxIntelligenceAgent(BaseRuntimeAgent):
    """
    Agent 0 — Inbox Intelligence Agent.

    Transforms raw Gmail inbox data into structured SuggestedTask documents
    that downstream agents can review, prioritise, and schedule.
    """

    def __init__(self) -> None:
        super().__init__(
            name="InboxIntelligenceAgent",
            description=(
                "Reads Gmail incrementally, filters noise, extracts actionable tasks via LLM, "
                "detects duplicates, cross-references Google Calendar, and stores structured "
                "SuggestedTask documents. Produces only suggestions — never actual tasks."
            ),
            output_schema=IIAOutput,
            required_tools=[
                "gmail_fetch_emails",
                "filter_email",
                "extract_task_from_email",
                "check_duplicate",
                "check_calendar_match",
                "store_suggested_task",
            ],
            tool_permissions=[
                "gmail_fetch_emails",
                "filter_email",
                "extract_task_from_email",
                "check_duplicate",
                "check_calendar_match",
                "store_suggested_task",
            ],
            state_permissions={
                "inbox": "rw",
                "suggested_tasks": "rw",
                "extraction_results": "rw",
                "calendar_matches": "rw",
                "duplicate_results": "rw",
                "execution_metadata": "rw",
                "*": "r",     # read-only access to all other state keys
            },
            memory_permissions={
                "working": "*",
                "session": "*",
                "long_term": "*",
            },
            retry_policy={"max_retries": 2, "backoff": 2.0},
        )

    # -----------------------------------------------------------------------
    # Runtime entry point
    # -----------------------------------------------------------------------

    async def run(
        self,
        context: ExecutionContext,
        input_data: Dict[str, Any],
    ) -> AgentResponse:
        """
        Main execution point called by the ExecutionEngine.
        Implements the full runtime lifecycle.
        """
        start_time = time.monotonic()
        uid = context.user_id
        session_id = context.session_id
        execution_id = context.execution_id

        logger.info(
            "InboxIntelligenceAgent starting [user=%s, execution=%s]", uid, execution_id
        )

        # Initialise per-run state
        output = IIAOutput()
        emitted_events: List = []
        warnings: List[str] = []

        # Memory handles (in-memory; real data comes from input_data context)
        working_mem = WorkingMemory()
        session_mem = SessionMemory()
        long_term_mem = LongTermMemory()

        try:
            # ------------------------------------------------------------------
            # STEP 2: Read Session / Previous State
            # ------------------------------------------------------------------
            inbox_state_dict: Dict[str, Any] = input_data.get("inbox", {})
            sync_state: InboxSyncState = self._load_sync_state(uid, inbox_state_dict)
            logger.debug("Sync state loaded: history_id=%s", sync_state.history_id)

            # ------------------------------------------------------------------
            # STEP 3: Read Memory
            # ------------------------------------------------------------------
            long_term_data = await long_term_mem.get_all(uid, session_id)
            sender_importance: Dict[str, float] = long_term_data.get("sender_importance", {})
            ignored_senders: List[str] = long_term_data.get("ignored_senders", [])

            await working_mem.set(uid, session_id, "execution_start", start_time)
            await working_mem.set(uid, session_id, "sync_state", sync_state.model_dump())

            # ------------------------------------------------------------------
            # STEP 4: Plan (internal planner decision)
            # ------------------------------------------------------------------
            plan = self._plan_execution(sync_state, input_data)
            output.execution_plan = plan.model_dump()
            logger.info("IIA execution plan: %s", plan.model_dump())

            if not plan.should_sync:
                logger.info("Planner decided sync is not required — returning early.")
                return self._build_success_response(output, start_time)

            # ------------------------------------------------------------------
            # STEP 5a: Emit InboxSyncStarted
            # ------------------------------------------------------------------
            sync_started_event = iia_events.make_inbox_sync_started_event(
                uid, session_id, sync_state.history_id
            )
            await _event_bus.publish(sync_started_event)
            emitted_events.append(sync_started_event.event_name)

            # ------------------------------------------------------------------
            # STEP 5b: Gmail Sync
            # ------------------------------------------------------------------
            raw_emails, new_history_id = fetch_incremental_emails(uid, sync_state, deep_sync=plan.deep_sync)
            print(f"EMAILS FETCHED: {len(raw_emails)}")
            output.emails_fetched = len(raw_emails)
            logger.info("Fetched %d email(s) for user '%s'.", len(raw_emails), uid)

            await _event_bus.publish(
                iia_events.make_inbox_sync_completed_event(
                    uid, session_id, len(raw_emails), new_history_id
                )
            )

            if not raw_emails:
                logger.info("No new emails for user '%s'.", uid)
                updated_sync_state = InboxSyncState(
                    last_sync_timestamp=time.time(),
                    processed_message_ids=sync_state.processed_message_ids,
                    history_id=new_history_id or sync_state.history_id,
                    last_run_at=time.time(),
                )
                save_sync_state(uid, updated_sync_state)
                output.sync_state = updated_sync_state.model_dump()
                warnings.append("No new emails found in inbox since last sync.")
                return self._build_success_response(output, start_time)

            # ------------------------------------------------------------------
            # STEP 5c: Pre-load data needed for duplicate detection
            # ------------------------------------------------------------------
            existing_tasks = get_existing_user_tasks(uid)
            existing_suggestions = get_existing_suggestions(uid)
            calendar_titles = get_calendar_event_titles(uid) if plan.should_check_calendar else []

            # ------------------------------------------------------------------
            # STEP 5d: Email filtering
            # ------------------------------------------------------------------
            relevant_emails, filter_results = filter_emails_batch(raw_emails)
            print(f"EMAILS FILTERED: {len(raw_emails) - len(relevant_emails)}")
            output.emails_filtered = len(raw_emails) - len(relevant_emails)
            output.emails_processed = len(relevant_emails)

            # Emit filtered events
            for fr in filter_results:
                if not fr.is_relevant:
                    await _event_bus.publish(
                        iia_events.make_email_filtered_event(
                            uid, session_id, fr.message_id, fr.reason
                        )
                    )

            # ------------------------------------------------------------------
            # STEP 5e: Per-email extraction pipeline
            # ------------------------------------------------------------------
            created_suggestion_ids: List[str] = []

            for email in relevant_emails:
                suggestion_id = await self._process_single_email(
                    uid=uid,
                    session_id=session_id,
                    email=email,
                    plan=plan,
                    existing_tasks=existing_tasks,
                    existing_suggestions=existing_suggestions,
                    calendar_titles=calendar_titles,
                    output=output,
                    warnings=warnings,
                )
                if suggestion_id:
                    created_suggestion_ids.append(suggestion_id)

            output.suggested_task_ids = created_suggestion_ids

            # Emit SuggestionsCreated if any were stored
            if created_suggestion_ids:
                await _event_bus.publish(
                    iia_events.make_suggestions_created_event(
                        uid, session_id,
                        count=len(created_suggestion_ids),
                        suggestion_ids=created_suggestion_ids,
                    )
                )

            # ------------------------------------------------------------------
            # STEP 8: Update State
            # ------------------------------------------------------------------
            processed_ids = list(
                set(sync_state.processed_message_ids)
                | {e.message_id for e in raw_emails}
            )
            # Cap processed_ids to last 1000 to avoid unbounded growth
            processed_ids = processed_ids[-1000:]

            updated_sync_state = InboxSyncState(
                last_sync_timestamp=time.time(),
                processed_message_ids=processed_ids,
                history_id=new_history_id or sync_state.history_id,
                last_run_at=time.time(),
            )
            save_sync_state(uid, updated_sync_state)
            output.sync_state = updated_sync_state.model_dump()

            # ------------------------------------------------------------------
            # STEP 9: Update Memory
            # ------------------------------------------------------------------
            # Session memory: what happened this run
            await session_mem.set(uid, session_id, "emails_processed", output.emails_processed)
            await session_mem.set(uid, session_id, "suggestions_created", output.suggestions_created)
            await session_mem.set(uid, session_id, "last_sync_history_id", new_history_id)

            # Long-term memory: sender patterns
            updated_sender_importance = self._update_sender_importance(
                sender_importance, relevant_emails, created_suggestion_ids
            )
            await long_term_mem.set(
                uid, session_id, "sender_importance", updated_sender_importance
            )

            # Working memory: current run context
            await working_mem.set(uid, session_id, "suggestion_ids", created_suggestion_ids)
            await working_mem.set(uid, session_id, "execution_output", output.model_dump())

            # ------------------------------------------------------------------
            # STEP 10: Emit ExecutionCompleted
            # ------------------------------------------------------------------
            elapsed_ms = (time.monotonic() - start_time) * 1000
            await _event_bus.publish(
                iia_events.make_execution_completed_event(
                    uid, session_id,
                    suggestions_created=output.suggestions_created,
                    latency_ms=elapsed_ms,
                )
            )
            output.warnings = warnings
            logger.info(
                "InboxIntelligenceAgent complete [user=%s, suggestions=%d, latency=%.0fms]",
                uid, output.suggestions_created, elapsed_ms
            )

            return self._build_success_response(output, start_time)

        except Exception as exc:
            logger.exception(
                "InboxIntelligenceAgent fatal error [user=%s, execution=%s]: %s",
                uid, execution_id, exc
            )
            await _event_bus.publish(
                iia_events.make_evaluation_failed_event(
                    uid, session_id, reason=str(exc),
                    retry_count=context.metadata.retry_count
                )
            )
            return AgentResponse(
                success=False,
                error=f"InboxIntelligenceAgent failed: {exc}",
                output_data={},
                metadata={"execution_id": execution_id},
            )

    # -----------------------------------------------------------------------
    # Internal planner
    # -----------------------------------------------------------------------

    def _plan_execution(
        self,
        sync_state: InboxSyncState,
        input_data: Dict[str, Any],
    ) -> IIAExecutionPlan:
        """
        Lightweight internal planning step. Mirrors AdkPlanner's interface
        but scoped to IIA sub-steps.

        Checks state flags to decide which sub-steps are needed.
        Does NOT perform business reasoning.
        """
        # If explicitly forced by orchestrator input
        deep_sync = input_data.get("deep_sync", False)

        # If last sync was very recent (< 5 minutes), skip unless it's a deep sync
        now = time.time()
        last_sync = sync_state.last_run_at or 0
        min_sync_interval_secs = 300  # 5 minutes
        if not deep_sync and (now - last_sync) < min_sync_interval_secs:
            return IIAExecutionPlan(
                should_sync=False,
                reason=f"Last sync was {int(now - last_sync)}s ago — too recent.",
            )

        return IIAExecutionPlan(
            should_sync=True,
            deep_sync=deep_sync,
            should_extract=True,
            should_deduplicate=True,
            should_check_calendar=True,
            requires_refinement=False,
            reason="Normal execution plan.",
        )

    # -----------------------------------------------------------------------
    # Per-email pipeline
    # -----------------------------------------------------------------------

    async def _process_single_email(
        self,
        uid: str,
        session_id: str,
        email: RawEmail,
        plan: IIAExecutionPlan,
        existing_tasks: List[Dict],
        existing_suggestions: List[Dict],
        calendar_titles: List[Tuple[str, Optional[str]]],
        output: IIAOutput,
        warnings: List[str],
    ) -> Optional[str]:
        """
        Runs the full pipeline for a single filtered email.
        Returns the suggestion_id if a suggestion was created, else None.
        """
        # --- LLM Extraction ---
        if not plan.should_extract:
            return None

        extracted: Optional[ExtractedTask] = extract_task_from_email(email)

        if extracted is None:
            output.tasks_rejected_low_confidence += 1
            await _event_bus.publish(
                iia_events.make_task_rejected_event(
                    uid, session_id,
                    message_id=email.message_id,
                    confidence=0.0,
                    threshold=settings.EVALUATION_CONFIDENCE_THRESHOLD,
                )
            )
            return None

        output.tasks_extracted += 1

        # --- Duplicate Detection ---
        if plan.should_deduplicate:
            dup_result = check_all_duplicates(
                extracted,
                existing_tasks,
                existing_suggestions,
                calendar_titles,
            )
            if dup_result.is_duplicate:
                output.duplicates_detected += 1
                await _event_bus.publish(
                    iia_events.make_duplicate_detected_event(
                        uid, session_id,
                        extracted_title=extracted.title,
                        matched_title=dup_result.matched_title,
                        matched_id=dup_result.matched_id,
                        similarity_score=dup_result.similarity_score,
                    )
                )
                logger.debug(
                    "Skipping duplicate: '%s' ↔ '%s'", extracted.title, dup_result.matched_title
                )
                return None

        # --- Calendar Cross-Reference ---
        calendar_match = None
        if plan.should_check_calendar:
            try:
                calendar_match = build_calendar_match_result(uid, extracted)
                if calendar_match.already_in_calendar or calendar_match.conflict_detected:
                    output.calendar_matches += 1
                    await _event_bus.publish(
                        iia_events.make_calendar_match_detected_event(
                            uid, session_id,
                            title=extracted.title,
                            calendar_event_id=calendar_match.calendar_event_id,
                            conflict_detected=calendar_match.conflict_detected,
                        )
                    )
                # If already in calendar exactly, skip creating suggestion
                if calendar_match.already_in_calendar:
                    logger.debug(
                        "Skipping '%s' — already in calendar (event_id=%s).",
                        extracted.title, calendar_match.calendar_event_id
                    )
                    return None
            except Exception as exc:
                warnings.append(f"Calendar check failed for '{extracted.title}': {exc}")
                calendar_match = None

        # --- Build and Store Suggestion ---
        suggestion = SuggestedTask(
            user_id=uid,
            title=extracted.title,
            description=extracted.description,
            deadline=extracted.deadline,
            due_date=extracted.due_date,
            due_time=extracted.due_time,
            location=extracted.location,
            meeting_link=extracted.meeting_link,
            task_category=extracted.task_category,
            urgency=extracted.urgency,
            source="gmail",
            source_message_id=extracted.source_message_id,
            source_subject=extracted.source_subject,
            source_sender_email=extracted.source_sender_email,
            source_sender_name=extracted.sender,
            confidence=extracted.confidence,
            already_in_calendar=calendar_match.already_in_calendar if calendar_match else False,
            calendar_event_id=calendar_match.calendar_event_id if calendar_match else None,
            conflict_detected=calendar_match.conflict_detected if calendar_match else False,
            conflict_metadata=(
                calendar_match.conflict_metadata.model_dump()
                if calendar_match and calendar_match.conflict_metadata
                else None
            ),
            duplicate=False,
            status="suggested",
        )

        try:
            suggestion_id = store_suggestion(uid, suggestion)
            output.suggestions_created += 1
            await _event_bus.publish(
                iia_events.make_task_extracted_event(
                    uid, session_id,
                    suggestion_id=suggestion_id,
                    title=suggestion.title,
                    confidence=suggestion.confidence,
                    source_message_id=suggestion.source_message_id,
                )
            )
            logger.info(
                "Suggestion created: id=%s, title='%s', confidence=%.2f",
                suggestion_id, suggestion.title, suggestion.confidence
            )
            return suggestion_id

        except Exception as exc:
            warnings.append(f"Failed to store suggestion '{extracted.title}': {exc}")
            logger.warning("Suggestion store failed for '%s': %s", extracted.title, exc)
            return None

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    def _load_sync_state(
        self, uid: str, inbox_state_dict: Dict[str, Any]
    ) -> InboxSyncState:
        """
        Loads sync state, preferring runtime state dict over Firestore
        (allows orchestrator to pass state in without extra DB reads).
        """
        if inbox_state_dict:
            try:
                return InboxSyncState(**inbox_state_dict)
            except Exception:
                pass
        try:
            return load_sync_state(uid)
        except Exception as exc:
            logger.warning("Could not load sync state for '%s': %s", uid, exc)
            return InboxSyncState()

    def _update_sender_importance(
        self,
        current_importance: Dict[str, float],
        emails: List[RawEmail],
        created_ids: List[str],
    ) -> Dict[str, float]:
        """
        Updates sender importance scores in long-term memory.
        Senders whose emails produced suggestions get a slight score boost.
        """
        created_count = len(created_ids)
        if created_count == 0:
            return current_importance

        # Compute simple per-sender conversion rate for this run
        for email in emails:
            sender = email.sender_email.lower()
            if sender:
                current = current_importance.get(sender, 0.5)
                # Increase importance slightly for senders whose emails produced tasks
                current_importance[sender] = min(1.0, current + 0.05)

        return current_importance

    def _build_success_response(
        self, output: IIAOutput, start_time: float
    ) -> AgentResponse:
        elapsed_ms = (time.monotonic() - start_time) * 1000
        return AgentResponse(
            success=True,
            output_data=output.model_dump(),
            metadata={
                "agent": "InboxIntelligenceAgent",
                "latency_ms": elapsed_ms,
                "suggestions_created": output.suggestions_created,
                "mock_confidence": 0.92,  # Used by LlmEvaluator mock path
            },
        )
