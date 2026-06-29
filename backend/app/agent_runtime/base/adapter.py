from typing import AsyncGenerator, Any
from uuid import uuid4
import datetime

from google.adk.agents.base_agent import BaseAgent
from google.adk.events.event import Event
from google.adk.agents.invocation_context import InvocationContext

from agent_runtime.base.agent import BaseRuntimeAgent
from agent_runtime.schemas.models import ExecutionContext, ExecutionMetadata, AgentResponse

class ADKAdapter(BaseAgent):
    """
    Adapter layer wrapping BaseRuntimeAgent into a Google ADK-compliant BaseAgent.
    This translation layer allows the orchestrator to run runtime-native agents
    within standard ADK structures.
    """
    runtime_agent: BaseRuntimeAgent

    def __init__(self, runtime_agent: BaseRuntimeAgent, **kwargs: Any):
        super().__init__(
            name=runtime_agent.name,
            description=runtime_agent.description,
            runtime_agent=runtime_agent,
            **kwargs
        )

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        exec_id = str(uuid4())
        
        # Fetch user_id and session_id from ADK context
        user_id = getattr(ctx, "user_id", "default_user") or "default_user"
        session_id = getattr(ctx, "session_id", "default_session") or "default_session"
        
        metadata = ExecutionMetadata(
            execution_id=exec_id,
            parent_execution_id=None,
            retry_count=0,
            created_at=datetime.datetime.utcnow(),
            updated_at=datetime.datetime.utcnow()
        )
        
        execution_context = ExecutionContext(
            user_id=user_id,
            session_id=session_id,
            execution_id=exec_id,
            metadata=metadata
        )
        
        # Simple extraction of last event content as input
        input_data = {}
        if hasattr(ctx, "events") and ctx.events:
            last_event = ctx.events[-1]
            if hasattr(last_event, "text") and last_event.text:
                input_data = {"text": last_event.text}
            elif hasattr(last_event, "content") and last_event.content:
                input_data = {"text": str(last_event.content)}
        
        # Execute the underlying runtime agent
        response: AgentResponse = await self.runtime_agent.run(execution_context, input_data)
        
        # Construct and yield ADK Event from response
        if response.success:
            yield Event(
                invocation_id=ctx.invocation_id,
                author=self.name,
                text=str(response.output_data.get("text", response.output_data))
            )
        else:
            yield Event(
                invocation_id=ctx.invocation_id,
                author=self.name,
                text=f"Error: {response.error}"
            )
