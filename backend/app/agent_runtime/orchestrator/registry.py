from typing import Dict, Type, Optional, Any
from agent_runtime.base.agent import BaseRuntimeAgent

class AgentRegistry:
    """
    Central registry for dynamic agent discovery and retrieval.
    Avoids hardcoded instantiations of business agents.
    """
    _agents: Dict[str, Type[BaseRuntimeAgent]] = {}

    @classmethod
    def register(cls, name: Optional[str] = None) -> Any:
        """
        Decorator to register a custom agent class in the central registry.
        """
        def decorator(agent_cls: Type[BaseRuntimeAgent]) -> Type[BaseRuntimeAgent]:
            agent_name = name or agent_cls.__name__
            cls._agents[agent_name] = agent_cls
            return agent_cls
        return decorator

    @classmethod
    def get_agent_class(cls, name: str) -> Optional[Type[BaseRuntimeAgent]]:
        return cls._agents.get(name)

    @classmethod
    def get_all_agents(cls) -> Dict[str, Type[BaseRuntimeAgent]]:
        return cls._agents

# Global registration helper
register_agent = AgentRegistry.register
