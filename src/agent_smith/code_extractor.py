import re


class CodeExtractionError(Exception):
    """Raised when executable code cannot be extracted."""


def extract_python_code(llm_output: str) -> str:
    """Extract Python code from an LLM response."""

    pattern = r"```(?:python|py)?\s*(.*?)```"

    match = re.search(
        pattern,
        llm_output,
        flags=re.DOTALL | re.IGNORECASE,
    )

    if match is None:
        raise CodeExtractionError(
            "No valid Python code block was found"
        )

    code = match.group(1).strip()

    if not code:
        raise CodeExtractionError(
            "The Python code block is empty"
        )

    return code