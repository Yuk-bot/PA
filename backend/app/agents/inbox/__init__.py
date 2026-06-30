"""
Inbox Intelligence Agent package.

Importing this package triggers auto-registration of:
  - InboxIntelligenceAgent → AgentRegistry (via @register_agent)
  - All IIA tools → ToolRegistry (via @tool)

This is the single import needed in main.py to activate Agent 0.
"""

# Import order matters:
# 1. tools.py first — registers tools before agent tries to reference them
# 2. agent.py second — registers the agent class itself

from agents.inbox import tools  # noqa: F401 — side-effect: tool registrations
from agents.inbox import agent  # noqa: F401 — side-effect: agent registration

__all__ = ["agent", "tools"]
