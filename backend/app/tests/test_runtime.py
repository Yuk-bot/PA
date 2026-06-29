import asyncio
import pytest
from pydantic import BaseModel
from typing import Dict, Any, Optional

from agent_runtime import (
    BaseRuntimeAgent,
    AgentRegistry,
    register_agent,
    ADKAdapter,
    ContextBuilder,
    ToolRegistry,
    tool,
    StateManager,
    SessionManager,
    CheckpointManager,
    AdkPlanner,
    InMemoryEventBus,
    WorkingMemory,
    SessionMemory,
    LongTermMemory,
    ExecutionEngine,
    RootOrchestrator
)
from agent_runtime.schemas.models import AgentResponse, ExecutionContext, Event

# ================= MOCK AGENTS =================

class MockInputSchema(BaseModel):
    input_text: str

class MockOutputSchema(BaseModel):
    result_text: str

@register_agent("MockTestAgent")
class MockTestAgent(BaseRuntimeAgent):
    def __init__(self) -> None:
        super().__init__(
            name="MockTestAgent",
            description="Agent for unit testing",
            input_schema=MockInputSchema,
            output_schema=MockOutputSchema,
            required_tools=["mock_tool"],
            tool_permissions=["mock_tool"],
            state_permissions={"allowed_key": "rw", "*": "r"},
            memory_permissions={"working": "*", "session": "*", "long_term": "*"}
        )

    async def run(self, context: ExecutionContext, input_data: Dict[str, Any]) -> AgentResponse:
        text = input_data.get("input_text", "hello")
        
        # Test tool permission call
        has_tool = any(t.name == "mock_tool" for t in ToolRegistry.get_authorized_tools(self.tool_permissions))
        
        return AgentResponse(
            success=True,
            output_data={"result_text": f"{text}_processed", "has_tool": has_tool},
            metadata={"mock_confidence": 0.95}
        )

# ================= MOCK TOOLS =================

@tool(name="mock_tool", description="A mock tool for verification testing")
def mock_tool(val: str) -> str:
    return f"mocked_{val}"

# ================= VERIFICATION TESTS =================

@pytest.mark.asyncio
async def test_agent_registry_and_adapter() -> None:
    # 1. Verification of Agent Registry
    agent_cls = AgentRegistry.get_agent_class("MockTestAgent")
    assert agent_cls is not None
    assert agent_cls == MockTestAgent

    agent_instance = agent_cls()
    assert agent_instance.name == "MockTestAgent"

    # 2. ADK Adapter translations
    adapter = ADKAdapter(agent_instance)
    assert adapter.name == "MockTestAgent"
    assert adapter.description == "Agent for unit testing"

@pytest.mark.asyncio
async def test_context_builder_and_permissions() -> None:
    agent = MockTestAgent()
    
    state_data = {"allowed_key": "valid_value", "secret_key": "shh"}
    working_mem = {"key1": "w1"}
    session_mem = {"key2": "s1"}
    long_term_mem = {"key3": "l1"}

    # Build filtered context
    built = ContextBuilder.build(
        user_id="test_user",
        session_id="test_sess",
        agent=agent,
        state_data=state_data,
        working_memory=working_mem,
        session_memory=session_mem,
        long_term_memory=long_term_mem
    )

    # State key 'secret_key' should be filtered out because it is not explicitly rw and not read
    assert "allowed_key" in built["state"].state_data
    assert "secret_key" not in built["state"].state_data
    
    # Tool mock_tool must be returned because it is in tool permissions
    tools = built["tools"]
    assert len(tools) > 0
    assert any(t.name == "mock_tool" for t in tools)

@pytest.mark.asyncio
async def test_state_manager_mutations() -> None:
    state_data = {"allowed_key": "value"}
    mgr = StateManager("test_session", state_data)
    
    # Authorized rw key
    agent_permissions = {"allowed_key": "rw"}
    assert mgr.get("allowed_key", agent_permissions) == "value"
    mgr.set("allowed_key", "new_value", agent_permissions)
    assert mgr.get("allowed_key", agent_permissions) == "new_value"

    # Unauthorized key write should raise PermissionError
    unauthorized_permissions = {"allowed_key": "r"}
    with pytest.raises(PermissionError):
        mgr.set("allowed_key", "bad_write", unauthorized_permissions)

@pytest.mark.asyncio
async def test_event_bus() -> None:
    bus = InMemoryEventBus()
    received_events = []

    async def mock_handler(event: Event) -> None:
        received_events.append(event)

    await bus.subscribe("MockEvent", mock_handler)
    
    test_event = Event(event_id="e1", event_name="MockEvent", payload={"data": 123})
    await bus.publish(test_event)

    assert len(received_events) == 1
    assert received_events[0].payload["data"] == 123

    # Unsubscribe check
    await bus.unsubscribe("MockEvent", mock_handler)
    await bus.publish(test_event)
    assert len(received_events) == 1

@pytest.mark.asyncio
async def test_execution_engine_and_evaluators() -> None:
    engine = ExecutionEngine()
    agent = MockTestAgent()

    state_data = {"allowed_key": "val"}
    
    res = await engine.execute_agent(
        agent=agent,
        user_id="test_user",
        session_id="test_sess",
        input_data={"input_text": "pytest"},
        state_data=state_data,
        working_memory={},
        session_memory={},
        long_term_memory={}
    )

    assert res.success is True
    assert res.output_data["result_text"] == "pytest_processed"
    assert res.output_data["has_tool"] is True

@pytest.mark.asyncio
async def test_root_orchestrator_flow() -> None:
    orchestrator = RootOrchestrator()
    
    # Set mock workflow in firestore mock state
    # We will pass a clean setup
    res = await orchestrator.execute_workflow(
        user_id="test_user",
        app_name="unit_test_app",
        session_id="test_sess_id",
        input_data={"input_text": "orchestrated_flow"}
    )
    
    # Verify success of workflow execution
    assert res.success is True

if __name__ == "__main__":
    async def run_all_tests():
        print("=== RUNNING RUNTIME FOUNDATION TESTS ===")
        try:
            await test_agent_registry_and_adapter()
            print("✅ test_agent_registry_and_adapter passed")
            await test_context_builder_and_permissions()
            print("✅ test_context_builder_and_permissions passed")
            await test_state_manager_mutations()
            print("✅ test_state_manager_mutations passed")
            await test_event_bus()
            print("✅ test_event_bus passed")
            await test_execution_engine_and_evaluators()
            print("✅ test_execution_engine_and_evaluators passed")
            await test_root_orchestrator_flow()
            print("✅ test_root_orchestrator_flow passed")
            print("🎉 ALL TESTS PASSED SUCCESSFULLY!")
        except Exception as e:
            import traceback
            print(f"❌ TEST FAILED: {e}")
            traceback.print_exc()

    asyncio.run(run_all_tests())

