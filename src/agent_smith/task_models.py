from pydantic import BaseModel, Field


class MBPPTaskInput(BaseModel):
    #Input data for an MBPP task.

    task_id: int
    task_definition: str
    function_definition: str
    test_imports: list[str] = Field(default_factory=list) # default factory -> force une liste par test
    test_list: list[str] = Field(default_factory=list)


class SWEBenchTaskInput(BaseModel):
    #Input data for a SWE-bench task.

    instance_id: str
    problem_statement: str
    docker_image: str
    eval_script: str
    hints_text: str = ""
    repo: str = ""