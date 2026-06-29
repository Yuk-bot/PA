import logging
from typing import Dict, Any, List, Optional

from agent_runtime.schemas.models import AgentResponse, Event
from agent_runtime.orchestrator.registry import AgentRegistry
from agent_runtime.execution.engine import ExecutionEngine
from agent_runtime.planner.adk_planner import AdkPlanner
from agent_runtime.checkpoint.manager import CheckpointManager
from agent_runtime.session.manager import SessionManager, SessionData
from agent_runtime.state.manager import StateManager
from agent_runtime.memory.working import WorkingMemory
from agent_runtime.memory.session import SessionMemory
from agent_runtime.memory.long_term import LongTermMemory
from agent_runtime.events.bus import InMemoryEventBus

logger = logging.getLogger("agent_runtime.orchestrator.root")

class RootOrchestrator:
    """
    Centralized coordinator responsible for sequential workflows,
    event-driven workflows, dynamic branching, checkpoints, and delegation.
    Contains no business logic.
    """
    def __init__(
        self,
        execution_engine: Optional[ExecutionEngine] = None,
        planner: Optional[AdkPlanner] = None,
        event_bus: Optional[InMemoryEventBus] = None
    ) -> None:
        self.engine = execution_engine or ExecutionEngine()
        self.planner = planner or AdkPlanner()
        self.event_bus = event_bus or InMemoryEventBus()
        self.session_manager = SessionManager()
        self.checkpoint_manager = CheckpointManager()
        
        # Memory caches
        self.working_memories: Dict[str, WorkingMemory] = {}
        self.session_memories: Dict[str, SessionMemory] = {}
        self.long_term_memory = LongTermMemory()

    async def execute_workflow(
        self,
        user_id: str,
        app_name: str,
        session_id: str,
        input_data: Dict[str, Any],
        resume_from_checkpoint: bool = False
    ) -> AgentResponse:
        
        # 1. Retrieve or create session
        session: Optional[SessionData] = await self.session_manager.get_session(user_id, session_id)
        if not session:
            session = await self.session_manager.create_session(app_name, user_id, session_id)
        
        # 2. Get state manager
        state_mgr = await StateManager.load_from_db(user_id, session_id)

        # 3. Handle checkpoints/recovery
        start_step = 0
        if resume_from_checkpoint:
            checkpoint = await self.checkpoint_manager.get_latest_checkpoint(user_id, session_id)
            if checkpoint:
                logger.info(f"Resuming workflow from checkpoint step: '{checkpoint.step_name}'")
                state_mgr = StateManager(session_id, checkpoint.state_data)
                
                # Restore memory contexts
                self.working_memories[session_id] = WorkingMemory()
                self.working_memories[session_id]._store[session_id] = checkpoint.working_memory
                
                self.session_memories[session_id] = SessionMemory()
                self.session_memories[session_id]._store[session_id] = checkpoint.session_memory
                
                # Determine how to index
                steps = await self.planner.plan_steps(None, state_mgr)
                if checkpoint.step_name in steps:
                    start_step = steps.index(checkpoint.step_name) + 1

        # 4. Resolve Memory Layer Scopes
        if session_id not in self.working_memories:
            self.working_memories[session_id] = WorkingMemory()
        if session_id not in self.session_memories:
            self.session_memories[session_id] = SessionMemory()

        working_mem = self.working_memories[session_id]
        session_mem = self.session_memories[session_id]
        long_term_mem = self.long_term_memory

        # 5. Retrieve steps from Planner
        steps = await self.planner.plan_steps(None, state_mgr)
        logger.info(f"Planned workflow steps: {steps}")

        last_output: Dict[str, Any] = input_data.copy()

        # 6. Execute loop across scheduled steps
        for i in range(start_step, len(steps)):
            step_name = steps[i]
            
            # Resolve Agent from registry
            agent_class = AgentRegistry.get_agent_class(step_name)
            if not agent_class:
                return AgentResponse(
                    success=False,
                    error=f"Step Agent '{step_name}' not found in registry."
                )
            
            agent_instance = agent_class()

            # Execute step through engine
            res: AgentResponse = await self.engine.execute_agent(
                agent=agent_instance,
                user_id=user_id,
                session_id=session_id,
                input_data=last_output,
                state_data=state_mgr.to_dict(),
                working_memory=await working_mem.get_all(user_id, session_id),
                session_memory=await session_mem.get_all(user_id, session_id),
                long_term_memory=await long_term_mem.get_all(user_id, session_id)
            )

            if not res.success:
                return res

            last_output = res.output_data

            # Save state mutations and updates
            # Mutate state based on agent returned changes (simulated update here)
            # Typically state changes are applied to state manager directly.
            # In a real run, the ContextBuilder gives state manager reference to execute_agent.
            # Here we reflect the output back to state manager for future steps.
            for key, val in last_output.items():
                if not key.startswith("temp:"):
                    # Safe permissions check mock: let the step write state
                    try:
                        state_mgr.set(key, val, agent_instance.state_permissions)
                    except PermissionError:
                        pass # Ignore unauthorized state mutations

            # Persist state changes back to Firestore
            await state_mgr.save_to_db(user_id)

            # 7. Checkpoint step completion
            await self.checkpoint_manager.save_checkpoint(
                user_id=user_id,
                session_id=session_id,
                step_name=step_name,
                state_data=state_mgr.to_dict(),
                working_memory=await working_mem.get_all(user_id, session_id),
                session_memory=await session_mem.get_all(user_id, session_id)
            )

            # 8. Check early stopping criteria
            if await self.planner.should_stop_early(None, state_mgr, step_name, last_output):
                logger.info(f"Early stopping triggered by step: '{step_name}'")
                break

            # 9. Handle dynamic delegation
            delegate_target = await self.planner.should_delegate(None, state_mgr, step_name, last_output)
            if delegate_target:
                logger.info(f"Delegating from '{step_name}' to subagent '{delegate_target}'")
                # Invoke subagent recursively as a delegation step
                sub_res = await self.execute_workflow(
                    user_id=user_id,
                    app_name=app_name,
                    session_id=session_id,
                    input_data=last_output,
                    resume_from_checkpoint=False
                )
                if not sub_res.success:
                    return sub_res
                last_output = sub_res.output_data

            # 10. Handle branching logic
            branch_target = await self.planner.get_next_branch(None, state_mgr, step_name, last_output)
            if branch_target:
                logger.info(f"Branching workflow to step: '{branch_target}'")
                # Dynamically append branch target to steps list
                steps.insert(i + 1, branch_target)

        # Clear working memory upon execution completion
        await working_mem.clear(user_id, session_id)

        # Return final execution response
        return AgentResponse(
            success=True,
            output_data=last_output
        )

    async def trigger_event(self, event: Event) -> None:
        """
        Publishes event to internal EventBus, triggering subscribed agent workflows.
        """
        await self.event_bus.publish(event)
