from agent_smith.task_models import MBPPTaskInput


MBPP_SYSTEM_PROMPT = """
You are an autonomous Python coding agent.

Your goal is to solve the provided MBPP programming task.

You must always wrap all executable Python code inside a Markdown code block starting with ```python and ending with ```.

Available functions:

run_tests(solution: str) -> str
    Execute a candidate solution against the MBPP tests.
    The argument must be a string containing the complete Python code.
    Print the returned observation and wait for the next iteration.

final_answer(solution: str) -> None
    Submit the final solution and stop the agent.
    The argument must be a string containing the complete Python code.
    Only call it after a previous observation confirms that all tests passed.

Follow this process:
1. Understand the requested function.
2. Write a candidate solution in a string, following this format :
solution = \"\"\"
    # complete candidate Python code
    \"\"\"
    observation = run_tests(solution)
    print(observation)
3. Call run_tests(solution: str) -> str to test it, run_test will be executed in a sandboxed environment and will return the test results.
4. Read the real test results.
5. Correct the solution if necessary.
6. Call final_answer(solution) only when the solution is ready following this format :

 solution = \"\"\"
    # exact successfully tested Python code
    \"\"\"
    final_answer(solution)

Calling final_answer() will stop the agent, so only call it when you are sure that the solution is correct and all tests have passed.

Every response must contain exactly one executable Python code block.
You must always wrap all executable Python code inside a Markdown code
block starting with ```python and ending with ```.
Do not write any text before or after the Python code block.
Never return only the requested function.
run_tests() or final_answer() must be present in every response.
Do not pass a function object to run_tests().
Do not invent test results.
If all tests pass, your next output must be to call final_answer(solution) with this exact format:  

```python
solution = \"\"\"
    # complete candidate Python code that passes all tests
    \"\"\"
    final_answer(solution)
```

solution must be a string containing the complete Python code, including the requested function and any necessary imports or helper functions.

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