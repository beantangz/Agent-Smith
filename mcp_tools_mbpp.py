import os
import subprocess
import sys
import json
import re

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

def _make_result(
    passed: bool,
    passed_tests: int = 0,
    total_tests: int = 0,
    stdout: str = "",
    stderr: str = "",
    error: str | None = None,
    timed_out: bool = False,
) -> str:
    """Serialize a normalized test result as JSON."""

    return json.dumps(
        {
            "passed": passed,
            "passed_tests": passed_tests,
            "total_tests": total_tests,
            "stdout": stdout,
            "stderr": stderr,
            "error": error,
            "timed_out": timed_out,
        },
        indent=2,
    )


#on execute le code dans un nvx process pour pas faire crash le serveur MCP

def _run_tests_impl(solution: str) -> str:
    """Execute a candidate solution against the current task."""

    task_path = os.getenv("MBPP_TASK_FILE")

    if task_path is None:
        return _make_result(
            passed=False,
            error="MBPP_TASK_FILE is not defined",
        )

    try:
        task = load_mbpp_task(task_path)
    except TaskLoadingError as error:
        return _make_result(
            passed=False,
            error=f"Task loading failed: {error}",
        )
# on creer le scprit de test avec les imports, le code solution et les tests en string pour le process (subprocess)
    test_script = _build_test_script(
        solution=solution,
        test_imports=task.test_imports,
        test_list=task.test_list,
    )

    try:
        completed = subprocess.run(
            [
                sys.executable,
                "-I",
                "-c",
                test_script,
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return _make_result(
            passed=False,
            total_tests=len(task.test_list),
            error="Test execution timed out after 10 seconds",
            timed_out=True,
        )

    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()

    summary_matches = re.findall(
        r"Summary: (\d+)/(\d+) tests passed",
        stdout,
    )

    if not summary_matches:
        return _make_result(
            passed=False,
            total_tests=len(task.test_list),
            stdout=stdout,
            stderr=stderr,
            error=(
                "The test process ended without producing "
                "a valid test summary"
            ),
        )

    passed_count, total_count = summary_matches[-1]

    passed_tests = int(passed_count)
    total_tests = int(total_count)

    all_tests_passed = (
        completed.returncode == 0
        and passed_tests == total_tests
        and total_tests == len(task.test_list)
    )

    return _make_result(
        passed=all_tests_passed,
        passed_tests=passed_tests,
        total_tests=total_tests,
        stdout=stdout,
        stderr=stderr,
        error=None if all_tests_passed else "Some tests failed",
    )


@mcp.tool()
def run_tests(solution: str) -> str:
    """Run the current MBPP tests against candidate Python code.

    Args:
        solution: Complete Python source code of the candidate solution.
    """
    return _run_tests_impl(solution)


if __name__ == "__main__":
    mcp.run(transport="stdio") # lance le serveur