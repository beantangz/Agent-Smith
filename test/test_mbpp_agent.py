import ast
import json

import pytest

from agent_smith.agent.mbpp_agent import MBPPAgent
from agent_smith.llm_client import LLMResponse
from agent_smith.sandbox.executor import SandboxResult
from agent_smith.task_models import MBPPTaskInput


CORRECT_SOLUTION = """
def square(number):
    return number * number
"""

INCORRECT_SOLUTION = """
def square(number):
    return number + number
"""


def make_llm_response(content: str) -> LLMResponse:
    """Create a normalized fake LLM response."""

    return LLMResponse(
        content=content,
        input_tokens=10,
        output_tokens=10,
        request_time_ms=1.0,
        api_url="https://fake-llm.test/v1",
        model_name="fake-model",
        retries=0,
    )


class FakeLLMClient:
    """Return predefined LLM responses in order."""

    def __init__(
        self,
        responses: list[LLMResponse],
    ) -> None:
        self.responses = responses
        self.index = 0
        self.calls = 0
        self.received_token_limits: list[int | None] = []

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_output_tokens: int | None = None,
    ) -> LLMResponse:
        response = self.responses[self.index]
        self.index += 1
        self.calls += 1
        self.received_token_limits.append(max_output_tokens)
        return response


class FakeSandbox:
    """Simulate sandbox actions and MBPP test results."""

    def __init__(self) -> None:
        self.executed_codes: list[str] = []

    async def execute(
        self,
        code: str,
    ) -> SandboxResult:
        self.executed_codes.append(code)

        solution = self._extract_solution(code)

        if "final_answer(solution)" in code:
            return SandboxResult(
                final_answer=solution,
            )

        if "run_tests(solution)" in code:
            passed = (
                "return number * number" in solution
            )

            passed_tests = 3 if passed else 1

            test_result = {
                "passed": passed,
                "passed_tests": passed_tests,
                "total_tests": 3,
                "stdout": (
                    f"Summary: {passed_tests}/3 tests passed"
                ),
                "stderr": "",
                "error": (
                    None if passed else "Some tests failed"
                ),
                "timed_out": False,
            }

            return SandboxResult(
                stdout=json.dumps(test_result),
            )

        return SandboxResult(
            error="No sandbox action found",
        )

    @staticmethod
    def _extract_solution(code: str) -> str:
        """Read the literal assigned to solution."""

        tree = ast.parse(code)

        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue

            assigns_solution = any(
                isinstance(target, ast.Name)
                and target.id == "solution"
                for target in node.targets
            )

            if not assigns_solution:
                continue

            return ast.literal_eval(node.value)

        raise AssertionError(
            "The tested code does not define solution"
        )


@pytest.fixture
def mbpp_task() -> MBPPTaskInput:
    """Create a small MBPP task for the agent tests."""

    return MBPPTaskInput(
        task_id=1,
        task_definition=(
            "Write a function that returns the square "
            "of an integer."
        ),
        function_definition="def square(number):",
        test_imports=[],
        test_list=[
            "assert square(4) == 16",
            "assert square(-3) == 9",
            "assert square(0) == 0",
        ],
    )


@pytest.mark.asyncio
async def test_agent_accepts_valid_final_answer(
    mbpp_task: MBPPTaskInput,
) -> None:
    test_response = make_llm_response(
        f'''```python
solution = {CORRECT_SOLUTION!r}
observation = run_tests(solution)
print(observation)
```'''
    )

    final_response = make_llm_response(
        f'''```python
solution = {CORRECT_SOLUTION!r}
final_answer(solution)
```'''
    )

    llm_client = FakeLLMClient(
        responses=[
            test_response,
            final_response,
        ]
    )
    sandbox = FakeSandbox()

    agent = MBPPAgent(
        llm_client=llm_client,
        sandbox=sandbox,
        max_iterations=2,
        max_output_tokens=100,
    )

    result = await agent.run(mbpp_task)

    assert result.success is True
    assert result.solution.strip() == (
        CORRECT_SOLUTION.strip()
    )
    assert result.error is None
    assert result.total_requests == 2

    assert len(sandbox.executed_codes) == 3

    final_verification = sandbox.executed_codes[2]

    assert "run_tests(solution)" in final_verification
    verified_solution = FakeSandbox._extract_solution(
    final_verification
    )

    assert verified_solution.strip() == (
        CORRECT_SOLUTION.strip()
    )

    assert llm_client.received_token_limits == [
        100,
        90,
    ]


@pytest.mark.asyncio
async def test_agent_rejects_invalid_final_answer(
    mbpp_task: MBPPTaskInput,
) -> None:
    test_response = make_llm_response(
        f'''```python
solution = {CORRECT_SOLUTION!r}
observation = run_tests(solution)
print(observation)
```'''
    )

    dishonest_final_response = make_llm_response(
        f'''```python
solution = {INCORRECT_SOLUTION!r}
final_answer(solution)
```'''
    )

    llm_client = FakeLLMClient(
        responses=[
            test_response,
            dishonest_final_response,
        ]
    )
    sandbox = FakeSandbox()

    agent = MBPPAgent(
        llm_client=llm_client,
        sandbox=sandbox,
        max_iterations=2,
    )

    result = await agent.run(mbpp_task)

    assert result.success is False
    assert result.solution == ""
    assert result.error == (
        "Maximum number of iterations reached"
    )

    assert len(sandbox.executed_codes) == 3

    final_verification = sandbox.executed_codes[2]

    assert "run_tests(solution)" in final_verification
    verified_solution = FakeSandbox._extract_solution(
    final_verification
    )

    assert verified_solution.strip() == (
        INCORRECT_SOLUTION.strip()
    )

    assert (
        "The final answer was rejected"
        in result.steps[-1].sandbox_output
    )