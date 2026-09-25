from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class StepMetrics(BaseModel):
    #Metrics and execution trace for one agent iteration.

    step: int
    input_tokens: int
    output_tokens: int
    request_time_ms: float
    api_url: str = ""
    model_name: str = ""
    llm_output: str = ""
    sandbox_input: str = ""
    sandbox_output: str = ""
    retries: int = 0
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat()
    )


class SolutionOutput(BaseModel):
    #Final result produced by an agent.

    task_id: str
    benchmark: str
    success: bool
    solution: str
    iterations: int
    total_requests: int
    total_input_tokens: int
    total_output_tokens: int
    total_time_seconds: float
    steps: list[StepMetrics] = Field(default_factory=list)
    system_prompt: str = ""
    error: Optional[str] = None
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat()
    )