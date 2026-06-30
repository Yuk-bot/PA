

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field
from uuid import uuid4




class RawEmail(BaseModel):

    #normalized, filtered needed gmail structure
    message_id: str
    thread_id: str
    subject: str = ""
    body: str = ""
    snippet: str = ""
    sender: str = ""
    sender_email: str = ""
    recipient: str = ""
    date: Optional[datetime] = None
    labels: List[str] = Field(default_factory=list)
    is_read: bool = False
    has_attachments: bool = False




class FilterResult(BaseModel):
    
    #filtered output from llm- by checking how relevant the mail is in regards with tasks nad deadlines
    message_id: str
    is_relevant: bool
    reason: str = ""



class ExtractedTask(BaseModel):
   
    title: str
    confidence: float = Field(ge=0.0, le=1.0)
    deadline: Optional[str] = None        
    due_date: Optional[str] = None        
    due_time: Optional[str] = None       
    location: Optional[str] = None
    meeting_link: Optional[str] = None
    sender: Optional[str] = None
    task_category: Optional[str] = None  
    urgency: Optional[str] = None        
    description: Optional[str] = None

    source_message_id: str = ""
    source_subject: str = ""
    source_sender_email: str = ""

class DuplicateResult(BaseModel):
  

    is_duplicate: bool
    matched_id: Optional[str] = None     # task_id or suggestion_id that matched
    matched_title: Optional[str] = None
    similarity_score: float = 0.0
    reason: str = ""



class ConflictMetadata(BaseModel):
    

    conflicting_event_id: str
    conflicting_event_title: str
    conflict_start: Optional[str] = None
    conflict_end: Optional[str] = None


class CalendarMatchResult(BaseModel):
    
    already_in_calendar: bool = False
    calendar_event_id: Optional[str] = None
    conflict_detected: bool = False
    conflict_metadata: Optional[ConflictMetadata] = None


class SuggestedTask(BaseModel):
   

    suggestion_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str

    # Core task data (from LLM extraction)
    title: str
    description: Optional[str] = None
    deadline: Optional[str] = None
    due_date: Optional[str] = None
    due_time: Optional[str] = None
    location: Optional[str] = None
    meeting_link: Optional[str] = None
    task_category: Optional[str] = None
    urgency: Optional[str] = None

    #from metadata
    source: str = "gmail"
    source_message_id: str = ""
    source_subject: str = ""
    source_sender_email: str = ""
    source_sender_name: Optional[str] = None

    confidence: float = Field(ge=0.0, le=1.0)

    already_in_calendar: bool = False
    calendar_event_id: Optional[str] = None
    conflict_detected: bool = False
    conflict_metadata: Optional[Dict[str, Any]] = None
    duplicate: bool = False

    status: str = "suggested" 
    created_at: float = Field(default_factory=lambda: datetime.utcnow().timestamp())
    updated_at: float = Field(default_factory=lambda: datetime.utcnow().timestamp())


#all agent and execution and definition and setup checks core logic done
class InboxSyncState(BaseModel):


    last_sync_timestamp: Optional[float] = None 
    processed_message_ids: List[str] = Field(default_factory=list)
    history_id: Optional[str] = None 
    last_run_at: Optional[float] = None

class IIAExecutionPlan(BaseModel):

    should_sync: bool = True
    deep_sync: bool = False
    should_extract: bool = True
    should_deduplicate: bool = True
    should_check_calendar: bool = True
    requires_refinement: bool = False
    reason: str = ""


class IIAOutput(BaseModel):

    emails_fetched: int = 0
    emails_filtered: int = 0  # irrelevant emails skipped
    emails_processed: int = 0  # emails sent to LLM
    tasks_extracted: int = 0
    tasks_rejected_low_confidence: int = 0
    duplicates_detected: int = 0
    calendar_matches: int = 0
    suggestions_created: int = 0

    suggested_task_ids: List[str] = Field(default_factory=list)
    execution_plan: Optional[Dict[str, Any]] = None
    sync_state: Optional[Dict[str, Any]] = None
    
    needs_negotiation: bool = False    # checked by RootOrchestrator planner
    halt_execution: bool = False
    warnings: List[str] = Field(default_factory=list)
