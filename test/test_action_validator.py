import pytest

from agent_smith.agent.action_validator import (
    ActionValidationError,
    validate_agent_action,
)


def test_accept_run_tests_action() -> None:
    code = '''
solution = """
def square(number):
    return number * number
"""

observation = run_tests(solution)
print(observation)
'''

    validate_agent_action(code)


def test_accept_final_answer_action() -> None:
    code = '''
solution = """
def square(number):
    return number * number
"""

final_answer(solution)
'''

    validate_agent_action(code)


def test_reject_missing_solution_variable() -> None:
    code = """
run_tests(candidate)
"""

    with pytest.raises(
        ActionValidationError,
        match="variable named solution",
    ):
        validate_agent_action(code)


def test_reject_non_string_solution() -> None:
    code = """
def square(number):
    return number * number

solution = square
run_tests(solution)
"""

    with pytest.raises(
        ActionValidationError,
        match="literal string",
    ):
        validate_agent_action(code)


def test_reject_empty_solution() -> None:
    code = '''
solution = """
"""

run_tests(solution)
'''

    with pytest.raises(
        ActionValidationError,
        match="cannot be empty",
    ):
        validate_agent_action(code)


def test_reject_missing_action() -> None:
    code = '''
solution = """
def square(number):
    return number * number
"""
'''

    with pytest.raises(
        ActionValidationError,
        match="must call run_tests",
    ):
        validate_agent_action(code)


def test_reject_multiple_actions() -> None:
    code = '''
solution = """
def square(number):
    return number * number
"""

run_tests(solution)
final_answer(solution)
'''

    with pytest.raises(
        ActionValidationError,
        match="exactly one action",
    ):
        validate_agent_action(code)


def test_reject_function_object_argument() -> None:
    code = '''
solution = """
def square(number):
    return number * number
"""

def square(number):
    return number * number

run_tests(square)
'''

    with pytest.raises(
        ActionValidationError,
        match="run_tests\\(solution\\)",
    ):
        validate_agent_action(code)


def test_reject_direct_string_argument() -> None:
    code = '''
solution = """
def square(number):
    return number * number
"""

run_tests("def square(number): return number * number")
'''

    with pytest.raises(
        ActionValidationError,
        match="run_tests\\(solution\\)",
    ):
        validate_agent_action(code)


def test_reject_keyword_argument() -> None:
    code = '''
solution = """
def square(number):
    return number * number
"""

run_tests(solution=solution)
'''

    with pytest.raises(
        ActionValidationError,
        match="positional argument",
    ):
        validate_agent_action(code)


def test_reject_invalid_python_syntax() -> None:
    code = """
solution =
run_tests(solution)
"""

    with pytest.raises(
        ActionValidationError,
        match="Invalid Python syntax",
    ):
        validate_agent_action(code)