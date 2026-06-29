import abc
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from agent_runtime.schemas.models import ExecutionContext, AgentResponse

class BaseRuntimeAgent(abc.ABC):
    """
    Independent Agent contract. All domain/business agents inherit from this.
    It does not subclass Google ADK's BaseAgent directly, which prevents coupling.
    Instead, an ADKAdapter translates and wraps this agent.
    """
    def __init__(
        self,
        name: str,
        description: str,
        input_schema: Optional[type[BaseModel]] = None,
        output_schema: Optional[type[BaseModel]] = None,
        required_tools: Optional[List[str]] = None,
        tool_permissions: Optional[List[str]] = None,
        state_permissions: Optional[Dict[str, str]] = None,
        memory_permissions: Optional[Dict[str, str]] = None,
        retry_policy: Optional[Dict[str, Any]] = None
    ):
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.output_schema = output_schema
        self.required_tools = required_tools or []
        self.tool_permissions = tool_permissions or []
        self.state_permissions = state_permissions or {}
        self.memory_permissions = memory_permissions or {}
        self.retry_policy = retry_policy or {"max_retries": 3, "backoff": 1.5}

    @abc.abstractmethod
    async def run(self, context: ExecutionContext, input_data: Dict[str, Any]) -> AgentResponse:
        """
        Main execution point for the agent. Called by the ExecutionEngine.
        """
        pass
