from pathlib import Path

from pydantic import ValidationError

from agent_smith.task_models import MBPPTaskInput


class TaskLoadingError(Exception):
    """Raised when a task file cannot be loaded."""


def load_mbpp_task(filepath: str) -> MBPPTaskInput:
    #Load and validate an MBPP task from a JSON file.

    path = Path(filepath)

    if not path.is_file():
        raise TaskLoadingError(
            f"Task file not found: {filepath}"
        )

    try:
        content = path.read_text(encoding="utf-8")
    except OSError as error:
        raise TaskLoadingError(
            f"Cannot read task file: {error}"
        ) from error

    try:
        return MBPPTaskInput.model_validate_json(content)
    except ValidationError as error:
        raise TaskLoadingError(
            f"Invalid MBPP task: {error}"
        ) from error