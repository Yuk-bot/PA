import asyncio
import datetime
import logging
from typing import Dict, Any, Optional

from agent_runtime.base.agent import BaseRuntimeAgent
from agent_runtime.schemas.models import AgentResponse, ExecutionContext, EvaluationResult
from agent_runtime.execution.context_builder import ContextBuilder
from agent_runtime.evaluator.runtime import RuntimeEvaluator
from agent_runtime.evaluator.llm_eval import LlmEvaluator
from agent_runtime.config import settings

logger = logging.getLogger("agent_runtime.execution.engine")

class ExecutionEngine:
    """
    Execution Engine coordinates the exact invocation flow of a single agent,
    handling structural setup, timeouts, exceptions, evaluators, and retry budgets.
    """
    def __init__(self) -> None:
        self.runtime_evaluator = RuntimeEvaluator()
        self.llm_evaluator = LlmEvaluator()

    async def execute_agent(
        self,
        agent: BaseRuntimeAgent,
        user_id: str,
        session_id: str,
        input_data: Dict[str, Any],
        state_data: Dict[str, Any],
        working_memory: Dict[str, Any],
        session_memory: Dict[str, Any],
        long_term_memory: Dict[str, Any],
        parent_execution_id: Optional[str] = None
    ) -> AgentResponse:
        
        # Centralized config values
        retry_policy = agent.retry_policy
        max_retries = retry_policy.get("max_retries", settings.DEFAULT_MAX_RETRIES)
        backoff = retry_policy.get("backoff", settings.DEFAULT_BACKOFF_FACTOR)
        timeout = settings.DEFAULT_TIMEOUT_SEC

        retry_count = 0
        last_error: Optional[str] = None

        while retry_count <= max_retries:
            # 1. Check for cancellation/halt signals before step
            if state_data.get("halt_all_agents"):
                return AgentResponse(
                    success=False,
                    error="Execution cancelled by orchestrator halt signal."
                )

            # 2. Build Context (including filtering)
            built_ctx = ContextBuilder.build(
                user_id=user_id,
                session_id=session_id,
                agent=agent,
                state_data=state_data,
                working_memory=working_memory,
                session_memory=session_memory,
                long_term_memory=long_term_memory,
                parent_execution_id=parent_execution_id,
                retry_count=retry_count
            )
            
            context: ExecutionContext = built_ctx["context"]
            start_time = datetime.datetime.utcnow()

            try:
                # 3. Invoke Agent with Timeout
                logger.info(f"Invoking Agent '{agent.name}' [Execution: {context.execution_id}, Retry: {retry_count}]")
                
                # We wrap the run call in wait_for to enforce timeout settings
                response: AgentResponse = await asyncio.wait_for(
                    agent.run(context, input_data),
                    timeout=timeout
                )
                
                # Calculate latency
                latency = (datetime.datetime.utcnow() - start_time).total_seconds() * 1000.0
                response.metadata["latency_ms"] = latency
                response.metadata["execution_id"] = context.execution_id

                if not response.success:
                    raise Exception(response.error or "Agent execution failed.")

                # 4. Run Evaluator 1: Runtime Evaluator
                runtime_eval: EvaluationResult = await self.runtime_evaluator.evaluate(agent, response)
                if not runtime_eval.is_valid:
                    raise ValueError(f"Runtime validation failed: {runtime_eval.feedback}")

                # 5. Run Evaluator 2: LLM Evaluator (Reasoning & Hallucinations)
                llm_eval: EvaluationResult = await self.llm_evaluator.evaluate(agent, input_data, response)
                if not llm_eval.is_valid:
                    raise ValueError(f"LLM quality validation failed: {llm_eval.feedback}")

                # If all evaluations passed, return response!
                return response

            except asyncio.TimeoutError:
                last_error = f"Timeout of {timeout}s exceeded during agent run."
                logger.warning(f"Agent '{agent.name}' timed out.")
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Agent '{agent.name}' failed: {last_error}")

            # Apply backoff delay before retry
            retry_count += 1
            if retry_count <= max_retries:
                sleep_time = backoff ** retry_count
                logger.info(f"Retrying agent '{agent.name}' in {sleep_time:.2f}s...")
                await asyncio.sleep(sleep_time)

        # Retries exhausted
        return AgentResponse(
            success=False,
            error=f"Agent '{agent.name}' execution failed after {max_retries} retries. Last error: {last_error}"
        )
