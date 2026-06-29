from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class ExecutionMetadata(BaseModel):
    execution_id: str
    parent_execution_id: Optional[str] = None
    retry_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    latency_ms: Optional[float] = None
    token_usage: Dict[str, int] = Field(default_factory=lambda: {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})
    step_count: int = 0

class ExecutionContext(BaseModel):
    user_id: str
    session_id: str
    execution_id: str
    metadata: ExecutionMetadata

class AgentRequest(BaseModel):
    context: ExecutionContext
    agent_name: str
    input_data: Dict[str, Any] = Field(default_factory=dict)

class AgentResponse(BaseModel):
    success: bool
    output_data: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ExecutionState(BaseModel):
    session_id: str
    state_data: Dict[str, Any] = Field(default_factory=dict)
    version: int = 1
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class MemoryContext(BaseModel):
    working_memory: Dict[str, Any] = Field(default_factory=dict)
    session_memory: Dict[str, Any] = Field(default_factory=dict)
    long_term_memory: Dict[str, Any] = Field(default_factory=dict)

class Event(BaseModel):
    event_id: str
    event_name: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=lambda: datetime.utcnow().timestamp())
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    version: str = "v1"

class DelegationRequest(BaseModel):
    parent_execution_id: str
    target_agent: str
    input_data: Dict[str, Any] = Field(default_factory=dict)

class EvaluationResult(BaseModel):
    is_valid: bool
    score: float = 1.0
    feedback: str = ""
    retry_required: bool = False
    validation_errors: List[str] = Field(default_factory=list)

class ToolResult(BaseModel):
    tool_name: str
    success: bool
    output: Any = None
    error: Optional[str] = None

class TaskSuggestion(BaseModel):
    title: str
    description: Optional[str] = None
    deadline: Optional[str] = None
    priority: str = "medium"
    reason: str = ""
