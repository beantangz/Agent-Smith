from agent_smith.task_models import MBPPTaskInput


MBPP_SYSTEM_PROMPT = """
You are an autonomous Python coding agent.

Your goal is to solve the provided MBPP programming task.

Follow this process:
1. Understand the requested function.
2. Write a candidate solution.
3. Call run_tests(solution) to test it.
4. Read the real test results.
5. Correct the solution if necessary.
6. Call final_answer(solution) only when the solution is ready.

You must respond with executable Python code inside a Python code block.
Do not invent test results or observations.
Wait for the sandbox observation before continuing.
""".strip()


def build_mbpp_user_prompt(task: MBPPTaskInput) -> str:
    #Build the user prompt for an MBPP task.

    tests = "\n".join(
        f"- {test}"
        for test in task.test_list
    )

    imports = "\n".join(
        f"- {test_import}"
        for test_import in task.test_imports
    )

    if not tests:
        tests = "- No visible tests provided"

    if not imports:
        imports = "- No additional imports required"

    return (
        f"Task ID: {task.task_id}\n\n"
        f"Problem:\n{task.task_definition}\n\n"
        f"Required function definition:\n"
        f"{task.function_definition}\n\n"
        f"Test imports:\n{imports}\n\n"
        f"Visible tests:\n{tests}"
    )