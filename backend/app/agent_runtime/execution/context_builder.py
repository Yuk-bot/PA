import datetime
from typing import Dict, Any, List, Optional
from uuid import uuid4

from agent_runtime.schemas.models import (
    ExecutionContext,
    ExecutionMetadata,
    ExecutionState,
    MemoryContext,
)
from agent_runtime.base.agent import BaseRuntimeAgent
from agent_runtime.registry.tool import ToolRegistry

class ContextBuilder:
    """
    Assembles state, memory, session context, tools, and metadata
    into a unified ExecutionContext before invoking an agent.
    Ensures data permissions are strictly enforced.
    """
    
    @staticmethod
    def build(
        user_id: str,
        session_id: str,
        agent: BaseRuntimeAgent,
        state_data: Dict[str, Any],
        working_memory: Dict[str, Any],
        session_memory: Dict[str, Any],
        long_term_memory: Dict[str, Any],
        parent_execution_id: Optional[str] = None,
        retry_count: int = 0
    ) -> Dict[str, Any]:
        execution_id = str(uuid4())
        
        # 1. Build Metadata
        metadata = ExecutionMetadata(
            execution_id=execution_id,
            parent_execution_id=parent_execution_id,
            retry_count=retry_count,
            created_at=datetime.datetime.utcnow(),
            updated_at=datetime.datetime.utcnow()
        )
        
        # 2. Build Context
        context = ExecutionContext(
            user_id=user_id,
            session_id=session_id,
            execution_id=execution_id,
            metadata=metadata
        )
        
        # 3. Filter State based on state_permissions (e.g. {"*": "r"} or {"allowed_key": "rw"})
        filtered_state_data = ContextBuilder._filter_data_by_permissions(
            state_data, agent.state_permissions
        )
        state = ExecutionState(
            session_id=session_id,
            state_data=filtered_state_data,
            version=1
        )
        
        # 4. Filter Memory based on memory_permissions
        filtered_working = ContextBuilder._filter_data_by_permissions(
            working_memory, agent.memory_permissions.get("working", "*")
        )
        filtered_session = ContextBuilder._filter_data_by_permissions(
            session_memory, agent.memory_permissions.get("session", "*")
        )
        filtered_long_term = ContextBuilder._filter_data_by_permissions(
            long_term_memory, agent.memory_permissions.get("long_term", "*")
        )
        
        memory = MemoryContext(
            working_memory=filtered_working,
            session_memory=filtered_session,
            long_term_memory=filtered_long_term
        )
        
        # 5. Fetch authorized tools based on tool_permissions
        tools = ToolRegistry.get_authorized_tools(agent.tool_permissions)
        
        return {
            "context": context,
            "state": state,
            "memory": memory,
            "tools": tools
        }

    @staticmethod
    def _filter_data_by_permissions(data: Dict[str, Any], permissions: Any) -> Dict[str, Any]:
        """
        Enforce permissions on a dictionary.
        permissions can be a string "*" (allow all), or a dict/list of allowed keys.
        """
        if permissions == "*" or permissions == ["*"] or (isinstance(permissions, dict) and "*" in permissions):
            return data.copy()
        
        allowed_keys = []
        if isinstance(permissions, list):
            allowed_keys = permissions
        elif isinstance(permissions, dict):
            allowed_keys = [k for k, v in permissions.items() if "r" in v]
        elif isinstance(permissions, str):
            allowed_keys = [permissions]
            
        return {k: v for k, v in data.items() if k in allowed_keys}
