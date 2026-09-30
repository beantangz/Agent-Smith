import asyncio
import sys
from pathlib import Path

from agent_smith.mcp_client import StdioMCPClient
from agent_smith.sandbox.executor import Sandbox


async def main() -> None:
    project_root = Path(__file__).resolve().parent.parent

    server_path = project_root / "mcp_tools_mbpp.py"
    task_path = project_root / "examples" / "mbpp_square.json"

    client = StdioMCPClient(
        command=sys.executable,
        args=[str(server_path)],
        env={
            "MBPP_TASK_FILE": str(task_path),
        },
    )

    generated_code = '''
solution = """
def square(number):
    return number * number
"""

observation = run_tests(solution)
print(observation)

final_answer(solution)
'''

    async with client:
        sandbox = Sandbox(
            mcp_client=client,
            timeout_seconds=15.0,
        )

        result = await sandbox.execute(generated_code)

    print("=== STDOUT ===")
    print(result.stdout)

    print("=== STDERR ===")
    print(result.stderr)

    print("=== ERROR ===")
    print(result.error)

    print("=== FINAL ANSWER ===")
    print(result.final_answer)

    print("=== TIMED OUT ===")
    print(result.timed_out)


if __name__ == "__main__":
    asyncio.run(main())