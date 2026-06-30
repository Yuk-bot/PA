

from __future__ import annotations

import logging
import re
import string
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from agents.inbox.schemas import DuplicateResult, ExtractedTask

logger = logging.getLogger("agents.inbox.duplicate_service")

JACCARD_THRESHOLD: float = 0.45

DATE_PROXIMITY_DAYS: int = 1


def _normalise_title(title: str) -> str:
    """
    Lowercases and strips punctuation from a title string.
    Produces a canonical form for comparison.
    """
    title = title.lower()
    title = title.translate(str.maketrans("", "", string.punctuation))
    # Collapse whitespace
    title = re.sub(r"\s+", " ", title).strip()
    # Remove common stop-words that add noise
    stop_words = {
        "the", "a", "an", "and", "or", "for", "to", "in", "on", "at",
        "is", "are", "was", "be", "have", "has", "had", "with", "from",
        "by", "of", "my", "your", "our", "please", "re"
    }
    tokens = [t for t in title.split() if t not in stop_words]
    return " ".join(tokens)


def _tokenise(normalised_title: str) -> set:
    """Splits a normalised title into a set of tokens."""
    return set(normalised_title.split())


def _jaccard_similarity(a: set, b: set) -> float:
  
    if not a or not b:
        return 0.0
    intersection = len(a & b)
    union = len(a | b)
    return intersection / union if union > 0 else 0.0


def _parse_flexible_date(date_str: Optional[str]) -> Optional[datetime]:

    if not date_str:
        return None
    formats = [
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%d/%m/%Y",
        "%m/%d/%Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str[:len(fmt)], fmt)
        except ValueError:
            continue
    return None


def _dates_are_close(
    date1_str: Optional[str],
    date2_str: Optional[str],
    threshold_days: int = DATE_PROXIMITY_DAYS,
) -> bool:
    """Returns True if both dates parse and are within threshold_days of each other."""
    d1 = _parse_flexible_date(date1_str)
    d2 = _parse_flexible_date(date2_str)
    if d1 is None or d2 is None:
        return False
    return abs((d1 - d2).days) <= threshold_days

def _compare_to_candidate(
    extracted: ExtractedTask,
    candidate_title: str,
    candidate_date: Optional[str] = None,
    candidate_id: Optional[str] = None,
) -> Tuple[bool, float, str]:
    
    norm_extracted = _normalise_title(extracted.title)
    norm_candidate = _normalise_title(candidate_title)

    # Exact match after normalisation
    if norm_extracted == norm_candidate:
        return True, 1.0, f"Exact title match with '{candidate_title}'"

    tokens_a = _tokenise(norm_extracted)
    tokens_b = _tokenise(norm_candidate)
    jaccard = _jaccard_similarity(tokens_a, tokens_b)

    if jaccard >= JACCARD_THRESHOLD:
      
        extracted_date = extracted.due_date or extracted.deadline
        if candidate_date:
            if _dates_are_close(extracted_date, candidate_date):
                return True, jaccard, (
                    f"Title similarity {jaccard:.0%} + date proximity match with '{candidate_title}'"
                )
            else:
                # High similarity but different dates -not a duplicate
                return False, jaccard, (
                    f"Title similarity {jaccard:.0%} but different dates — not duplicate"
                )
        # No date to compare — title similarity alone is enough
        return True, jaccard, f"Title similarity {jaccard:.0%} with '{candidate_title}'"

    return False, jaccard, f"Similarity {jaccard:.0%} below threshold"
    
def check_duplicate_against_tasks(
    extracted: ExtractedTask,
    existing_tasks: List[Dict[str, Any]],
) -> DuplicateResult:

    
    for task in existing_tasks:
        title = task.get("title", "")
        if not title:
            continue
        task_id = task.get("id", "")
        deadline = task.get("deadline")

        is_dup, score, reason = _compare_to_candidate(
            extracted, title, candidate_date=deadline, candidate_id=task_id
        )
        if is_dup:
            logger.info(
                "Duplicate found: '%s' ↔ existing task '%s' (score=%.2f)", 
                extracted.title, title, score
            )
            return DuplicateResult(
                is_duplicate=True,
                matched_id=task_id,
                matched_title=title,
                similarity_score=score,
                reason=f"Matches existing task: {reason}",
            )

    return DuplicateResult(is_duplicate=False, reason="No duplicate found in existing tasks.")


def check_duplicate_against_suggestions(
    extracted: ExtractedTask,
    existing_suggestions: List[Dict[str, Any]],
) -> DuplicateResult:
    
    for suggestion in existing_suggestions:
        title = suggestion.get("title", "")
        if not title:
            continue
        sug_id = suggestion.get("suggestion_id", "")
        date = suggestion.get("due_date") or suggestion.get("deadline")

        is_dup, score, reason = _compare_to_candidate(
            extracted, title, candidate_date=date, candidate_id=sug_id
        )
        if is_dup:
            logger.info(
                "Duplicate found: '%s' ↔ existing suggestion '%s' (score=%.2f)",
                extracted.title, title, score
            )
            return DuplicateResult(
                is_duplicate=True,
                matched_id=sug_id,
                matched_title=title,
                similarity_score=score,
                reason=f"Matches existing suggestion: {reason}",
            )

    return DuplicateResult(is_duplicate=False, reason="No duplicate found in existing suggestions.")


def check_duplicate_against_calendar(
    extracted: ExtractedTask,
    calendar_event_titles: List[Tuple[str, Optional[str]]],
) -> DuplicateResult:
   
    for event_title, event_date in calendar_event_titles:
        if not event_title:
            continue
        is_dup, score, reason = _compare_to_candidate(
            extracted, event_title, candidate_date=event_date
        )
        if is_dup:
            logger.info(
                "Calendar duplicate: '%s' ↔ event '%s' (score=%.2f)",
                extracted.title, event_title, score
            )
            return DuplicateResult(
                is_duplicate=True,
                matched_title=event_title,
                similarity_score=score,
                reason=f"Title matches calendar event: {reason}",
            )

    return DuplicateResult(is_duplicate=False, reason="No calendar title duplicate.")


def check_all_duplicates(
    extracted: ExtractedTask,
    existing_tasks: List[Dict[str, Any]],
    existing_suggestions: List[Dict[str, Any]],
    calendar_event_titles: Optional[List[Tuple[str, Optional[str]]]] = None,
) -> DuplicateResult:
    
    
    result = check_duplicate_against_tasks(extracted, existing_tasks)
    if result.is_duplicate:
        return result

    result = check_duplicate_against_suggestions(extracted, existing_suggestions)
    if result.is_duplicate:
        return result

    if calendar_event_titles:
        result = check_duplicate_against_calendar(extracted, calendar_event_titles)
        if result.is_duplicate:
            return result

    return DuplicateResult(is_duplicate=False, reason="No duplicate detected.")
