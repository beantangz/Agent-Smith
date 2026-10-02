import pytest

from agent_smith.code_extractor import (
    CodeExtractionError,
    extract_python_code,
)


def test_extract_python_code() -> None:
    llm_output = '''
Explanation before the code.

```python
solution = """
def square(number):
    return number * number
"""

run_tests(solution)
```
'''

    result = extract_python_code(llm_output)

    assert "def square(number):" in result
    assert "run_tests(solution)" in result
    assert "```" not in result


def test_extract_py_code_block() -> None:
    llm_output = """
```py
solution = "print('hello')"
run_tests(solution)
```
"""

    result = extract_python_code(llm_output)

    assert result == (
        'solution = "print(\'hello\')"\n'
        "run_tests(solution)"
    )


def test_extract_unlabelled_code_block() -> None:
    llm_output = """
```
solution = "x = 42"
run_tests(solution)
```
"""

    result = extract_python_code(llm_output)

    assert result == (
        'solution = "x = 42"\n'
        "run_tests(solution)"
    )


def test_reject_response_without_code_block() -> None:
    llm_output = """
solution = "def square(number): return number * number"
run_tests(solution)
"""

    with pytest.raises(
        CodeExtractionError,
        match="No valid Python code block",
    ):
        extract_python_code(llm_output)


def test_reject_empty_code_block() -> None:
    llm_output = """
```python

```
"""

    with pytest.raises(
        CodeExtractionError,
        match="code block is empty",
    ):
        extract_python_code(llm_output)