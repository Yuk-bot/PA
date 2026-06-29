from typing import List, Dict, Any, Optional
from agent_runtime.schemas.models import ExecutionContext, ExecutionState

class AdkPlanner:
    """
    Expanded Planner that handles dynamic execution planning,
    delegation triggers, conditional branching, early stopping,
    and runtime adjustments rather than static sequential flow.
    """
    def __init__(self) -> None:
        pass

    async def plan_steps(self, context: ExecutionContext, state: ExecutionState) -> List[str]:
        """
        Determines the sequence of agent names to invoke based on current execution context and state.
        This provides default path scheduling.
        """
        # Default plan: sequential list of components if specified in state,
        # or fallback to state-driven dynamic routing.
        workflow = state.state_data.get("current_workflow", "sequential")
        if workflow == "sequential":
            return ["InboxIntelligenceAgent", "ActAgent", "PriorityAgent", "EngagementPlanner"]
        return ["InboxIntelligenceAgent"]

    async def should_delegate(
        self,
        context: ExecutionContext,
        state: ExecutionState,
        current_agent: str,
        output_data: Dict[str, Any]
    ) -> Optional[str]:
        """
        Evaluates output to determine if control should be delegated to a subagent.
        """
        # Logic trigger: e.g. if inbox intelligence detects negotiation required, delegate to Negotiator.
        if current_agent == "InboxIntelligenceAgent" and output_data.get("needs_negotiation"):
            return "NegotiatorAgent"
        if current_agent == "ActAgent" and output_data.get("unresolved_risks"):
            return "RiskAgent"
        return None

    async def should_stop_early(
        self,
        context: ExecutionContext,
        state: ExecutionState,
        current_agent: str,
        output_data: Dict[str, Any]
    ) -> bool:
        """
        Evaluates outputs/state for termination conditions (early stopping).
        """
        # If any agent detects a fatal error or user cancellation, halt execution.
        if output_data.get("halt_execution") or state.state_data.get("halt_all_agents"):
            return True
        return False

    async def get_next_branch(
        self,
        context: ExecutionContext,
        state: ExecutionState,
        current_agent: str,
        output_data: Dict[str, Any]
    ) -> Optional[str]:
        """
        Determines dynamic conditional branching pathways based on agent outputs.
        """
        # E.g. Branch to RescueAgent if conflict is unresolvable by engagement planner
        if current_agent == "EngagementPlanner" and output_data.get("conflict_detected"):
            return "RescueAgent"
        return None
