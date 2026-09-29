import os
import subprocess
import sys

from mcp.server import MCPServer

from agent_smith.task_loader import (
    TaskLoadingError,
    load_mbpp_task, #contient les imports et les tests pour la tache MBPP courante
)


mcp = MCPServer("mbpp-tools") # creation du serveur

# on a actuellemt la fonction solution sous forme de str creer par le LLM,
# on regroupe donc ici les imports, la solution, et les tests dans une seule str
# pour l'envoyer a un sous process

# On construit ici le programme a executer dans un sous process
def _build_test_script( 
    
    solution: str,
    test_imports: list[str], 
    test_list: list[str],
) -> str:
    """Build a Python script containing the solution and tests."""

    imports_code = "\n".join(test_imports)

    return (
        f"{imports_code}\n\n"
        f"{solution}\n\n"
        f"tests = {test_list!r}\n"
        "passed = 0\n\n"
        "for index, test in enumerate(tests, start=1):\n"
        "    try:\n"
        "        exec(test, globals(), globals())\n"
        "        print(f'Test {index}: PASSED')\n"
        "        passed += 1\n"
        "    except Exception as error:\n"
        "        print(\n"
        "            f'Test {index}: FAILED - '\n"
        "            f'{type(error).__name__}: {error}'\n"
        "        )\n\n"
        "print(f'Summary: {passed}/{len(tests)} tests passed')\n"
    )


#on execute le code dans un nvx process pour pas faire crash le serveur MCP
def _run_tests_impl(solution: str) -> str: 
    """Execute a candidate solution against the current task."""
# on commence par load la tache, avec les imports et les tests
    task_path = os.getenv("MBPP_TASK_FILE")

    if task_path is None:
        return (
            "Configuration error: "
            "MBPP_TASK_FILE is not defined"
        )

    try:
        task = load_mbpp_task(task_path)
    except TaskLoadingError as error:
        return f"Task loading failed: {error}"

# on creer le script complet avec la solution du LLM, pour l'envoyer au sous process
    test_script = _build_test_script(
        solution=solution,
        test_imports=task.test_imports,
        test_list=task.test_list,
    )

    try:
        completed = subprocess.run( # nvx process
            [
                sys.executable,
                "-I",
                "-c",
                test_script, # script complet avec solution et tests
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return "Test execution timed out after 10 seconds"

    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()

    if stderr:
        if stdout:
            stdout += "\n"
        stdout += f"Execution error:\n{stderr}"

    if not stdout:
        return "Test execution produced no output"

    return stdout


@mcp.tool()
def run_tests(solution: str) -> str:
    """Run the current MBPP tests against candidate Python code.

    Args:
        solution: Complete Python source code of the candidate solution.
    """
    return _run_tests_impl(solution)


if __name__ == "__main__":
    mcp.run(transport="stdio") # lance le serveur