from typing import Dict, Any, Callable, List, Optional
from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.base_tool import BaseTool

class ToolRegistry:
    """
    Central tool registry. Handles decorator-based tool registration,
    permission checking, and dynamic tool injection for agents.
    """
    _registry: Dict[str, BaseTool] = {}

    @classmethod
    def register(cls, name: Optional[str] = None, description: Optional[str] = None) -> Callable[..., Any]:
        """
        Decorator to register a function or custom class as a tool.
        """
        def decorator(func_or_class: Any) -> Any:
            tool_name = name or getattr(func_or_class, "__name__", str(func_or_class))
            tool_desc = description or getattr(func_or_class, "__doc__", "") or "No description provided."
            
            if isinstance(func_or_class, type) and issubclass(func_or_class, BaseTool):
                # Custom BaseTool class
                tool_instance = func_or_class()
                cls._registry[tool_name] = tool_instance
            elif callable(func_or_class):
                # Standard Python function
                tool_instance = FunctionTool(func_or_class)
                tool_instance.name = tool_name
                tool_instance.description = tool_desc
                cls._registry[tool_name] = tool_instance
            else:
                raise TypeError("Only callables or BaseTool subclasses can be registered as tools.")
            
            return func_or_class
        return decorator

    @classmethod
    def get_tool(cls, name: str) -> Optional[BaseTool]:
        return cls._registry.get(name)

    @classmethod
    def get_all_tools(cls) -> Dict[str, BaseTool]:
        return cls._registry

    @classmethod
    def get_authorized_tools(cls, allowed_tool_names: List[str]) -> List[BaseTool]:
        """
        Filters and returns only tools that are explicitly allowed.
        Supports wildcards ("*") for unlimited access.
        """
        if "*" in allowed_tool_names:
            return list(cls._registry.values())
        
        authorized = []
        for name in allowed_tool_names:
            tool = cls.get_tool(name)
            if tool:
                authorized.append(tool)
        return authorized

# Global registry helper
tool = ToolRegistry.register
