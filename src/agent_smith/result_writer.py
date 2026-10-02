import re
from datetime import datetime
from pathlib import Path

from agent_smith.output_models import SolutionOutput


def save_solution_output(
    result: SolutionOutput,
    output_directory: str | Path = "results",
) -> Path:
    """Save one agent result as a JSON file."""

    directory = Path(output_directory)

    directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    safe_benchmark = _safe_filename_part(
        result.benchmark
    )
    safe_task_id = _safe_filename_part(
        result.task_id
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )

    filename = (
        f"{safe_benchmark}_"
        f"{safe_task_id}_"
        f"{timestamp}.json"
    )

    output_path = directory / filename

    output_path.write_text(
        result.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )

    return output_path


def _safe_filename_part(value: str) -> str:
    """Replace unsafe filename characters."""

    cleaned_value = re.sub(
        r"[^a-zA-Z0-9_-]+",
        "_",
        value,
    )

    return cleaned_value.strip("_") or "unknown"