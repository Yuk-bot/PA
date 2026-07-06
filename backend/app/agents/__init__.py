"""
Agents package root.

Importing agents.inbox triggers auto-registration of InboxIntelligenceAgent
and all its tools. Additional agent packages (agents.act, agents.priority, etc.)
will be imported here when they are implemented.
"""

import agents.inbox  # noqa: F401 — triggers IIA registration
import agents.planning.engagement_agent

