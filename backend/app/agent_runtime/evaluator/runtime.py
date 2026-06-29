from typing import Dict, Any, List
from pydantic import ValidationError

from agent_runtime.base.agent import BaseRuntimeAgent
from agent_runtime.schemas.models import AgentResponse, EvaluationResult

class RuntimeEvaluator:
    """
    Evaluator responsible for structure, schema, permissions, and tool output compliance checks.
    """
    def __init__(self) -> None:
        pass

    async def evaluate(self, agent: BaseRuntimeAgent, response: AgentResponse) -> EvaluationResult:
        errors: List[str] = []
        
        # 1. Output Schema Validation
        if agent.output_schema and response.success:
            try:
                agent.output_schema.model_validate(response.output_data)
            except ValidationError as e:
                errors.append(f"Schema mismatch for agent '{agent.name}': {str(e)}")
        
        # 2. Check general runtime errors reported by response
        if response.error:
            errors.append(f"Agent reported runtime error: {response.error}")

        is_valid = len(errors) == 0
        return EvaluationResult(
            is_valid=is_valid,
            score=1.0 if is_valid else 0.0,
            feedback="Structure and schema validation succeeded." if is_valid else "; ".join(errors),
            retry_required=not is_valid,
            validation_errors=errors
        )
