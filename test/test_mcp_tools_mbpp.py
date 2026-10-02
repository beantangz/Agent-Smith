import json
from pathlib import Path

import pytest

from mcp_tools_mbpp import _run_tests_impl


@pytest.fixture
def mbpp_task_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    """Create a temporary MBPP task for one test."""

    task_data = {
        "task_id": 1,
        "task_definition": (
            "Write a function that returns the square "
            "of an integer."
        ),
        "function_definition": "def square(number):",
        "test_imports": [],
        "test_list": [
            "assert square(4) == 16",
            "assert square(-3) == 9",
            "assert square(0) == 0",
        ],
    }

    task_path = tmp_path / "mbpp_task.json"

    task_path.write_text(
        json.dumps(task_data),
        encoding="utf-8",
    )

    monkeypatch.setenv(
        "MBPP_TASK_FILE",
        str(task_path),
    )

    return task_path


def test_run_tests_accepts_correct_solution(
    mbpp_task_file: Path,
) -> None:
    solution = """
def square(number):
    return number * number
"""

    raw_result = _run_tests_impl(solution)
    result = json.loads(raw_result)

    assert result["passed"] is True
    assert result["passed_tests"] == 3
    assert result["total_tests"] == 3
    assert result["error"] is None
    assert result["timed_out"] is False


def test_run_tests_rejects_incorrect_solution(
    mbpp_task_file: Path,
) -> None:
    solution = """
def square(number):
    return number + number
"""

    raw_result = _run_tests_impl(solution)
    result = json.loads(raw_result)

    assert result["passed"] is False
    assert result["passed_tests"] == 1
    assert result["total_tests"] == 3
    assert result["error"] == "Some tests failed"
    assert "FAILED" in result["stdout"]


def test_run_tests_rejects_invalid_python(
    mbpp_task_file: Path,
) -> None:
    solution = """
def square(number)
    return number * number
"""

    raw_result = _run_tests_impl(solution)
    result = json.loads(raw_result)

    assert result["passed"] is False
    assert result["passed_tests"] == 0
    assert result["total_tests"] == 3
    assert result["error"] is not None
    assert result["stderr"]


def test_run_tests_requires_task_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(
        "MBPP_TASK_FILE",
        raising=False,
    )

    solution = """
def square(number):
    return number * number
"""

    raw_result = _run_tests_impl(solution)
    result = json.loads(raw_result)

    assert result["passed"] is False
    assert result["error"] == (
        "MBPP_TASK_FILE is not defined"
    )