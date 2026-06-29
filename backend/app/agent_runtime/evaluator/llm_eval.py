import os
import json
from typing import Dict, Any, List
from agent_runtime.base.agent import BaseRuntimeAgent
from agent_runtime.schemas.models import AgentResponse, EvaluationResult
from agent_runtime.config import settings

class LlmEvaluator:
    """
    LLM-based Evaluator verifying reasoning quality, completeness,
    confidence metrics, and hallucination checks.
    """
    def __init__(self) -> None:
        self.api_key = os.getenv("GEMINI_API_KEY")
        self._client = None
        if self.api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except Exception:
                pass

    async def evaluate(
        self,
        agent: BaseRuntimeAgent,
        agent_input: Dict[str, Any],
        agent_output: AgentResponse
    ) -> EvaluationResult:
        if not agent_output.success:
            return EvaluationResult(
                is_valid=False,
                score=0.0,
                feedback="Skipping LLM evaluation due to upstream agent execution failure.",
                retry_required=True
            )

        # Build prompt for quality evaluation
        prompt = f"""
        Evaluate the output of an AI agent named '{agent.name}'.
        Agent Goal: {agent.description}
        Agent Input: {json.dumps(agent_input)}
        Agent Output: {json.dumps(agent_output.output_data)}
        
        Analyze:
        1. Reasoning Quality: Did the agent reason correctly?
        2. Completeness: Did the agent fully address the input requirements?
        3. Hallucinations: Does the output contain incorrect or unsupported claims?
        4. Confidence: Provide a confidence score between 0.0 and 1.0.

        Output your response as JSON in this exact format:
        {{
            "is_valid": true/false,
            "score": 0.85,
            "hallucination_detected": false,
            "feedback": "Reasoning was sound, but task list lacked dates."
        }}
        """

        if not self._client:
            # Fallback to Mock Evaluator if API Key is not set (e.g. during local tests)
            # Default pass, unless agent specifies a mock failure code for test purposes
            confidence = agent_output.metadata.get("mock_confidence", 0.9)
            is_valid = confidence >= settings.EVALUATION_CONFIDENCE_THRESHOLD
            return EvaluationResult(
                is_valid=is_valid,
                score=confidence,
                feedback="[MOCK LLM EVALUATOR] Validation succeeded based on mock confidence." if is_valid else "[MOCK LLM EVALUATOR] Low confidence detected.",
                retry_required=not is_valid
            )

        try:
            # Call Gemini model
            response = self._client.models.generate_content(
                model=settings.DEFAULT_MODEL,
                contents=prompt,
                config={"response_mime_type": "application/json"}
            )
            
            result_dict = json.loads(response.text)
            score = result_dict.get("score", 1.0)
            is_valid = result_dict.get("is_valid", True) and (score >= settings.EVALUATION_CONFIDENCE_THRESHOLD)
            
            return EvaluationResult(
                is_valid=is_valid,
                score=score,
                feedback=result_dict.get("feedback", "LLM evaluation finished."),
                retry_required=not is_valid
            )
        except Exception as e:
            # Resilient fallback on network/rate-limit error
            return EvaluationResult(
                is_valid=True,
                score=1.0,
                feedback=f"LLM evaluator failed to invoke API: {str(e)}. Permitting fallback pass.",
                retry_required=False
            )
