import time
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class TraceSpan(BaseModel):
    span_id: str
    name: str
    parent_span_id: Optional[str] = None
    inputs: Dict[str, Any] = Field(default_factory=dict)
    outputs: Optional[Dict[str, Any]] = None
    start_time: float = Field(default_factory=time.time)
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    children: List["TraceSpan"] = Field(default_factory=list)

class TraceCollector:
    """
    Collector and manager for execution path tracing.
    Builds structured execution trace graphs for observability.
    """
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self._spans: Dict[str, TraceSpan] = {}
        self._root_span: Optional[TraceSpan] = None

    def start_span(self, span_id: str, name: str, parent_span_id: Optional[str] = None, inputs: Optional[Dict[str, Any]] = None) -> TraceSpan:
        span = TraceSpan(
            span_id=span_id,
            name=name,
            parent_span_id=parent_span_id,
            inputs=inputs or {}
        )
        self._spans[span_id] = span
        
        if parent_span_id and parent_span_id in self._spans:
            self._spans[parent_span_id].children.append(span)
        elif not self._root_span:
            self._root_span = span
            
        return span

    def end_span(self, span_id: str, outputs: Optional[Dict[str, Any]] = None) -> Optional[TraceSpan]:
        span = self._spans.get(span_id)
        if span:
            span.outputs = outputs or {}
            span.end_time = time.time()
            span.duration_ms = (span.end_time - span.start_time) * 1000.0
            return span
        return None

    def get_trace(self) -> Optional[TraceSpan]:
        return self._root_span
