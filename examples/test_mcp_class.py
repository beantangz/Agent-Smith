import asyncio
import sys
from pathlib import Path

from agent_smith.mcp_client import (
    StdioMCPClient,
)


async def main() -> None:
    project_root = Path(__file__).parent.parent

    server_path = (
        project_root / "mcp_tools_mbpp.py"
    ).resolve()

    task_path = (
        project_root
        / "examples"
        / "mbpp_square.json"
    ).resolve()

    client = StdioMCPClient(
        command=sys.executable,
        args=[str(server_path)],
        env={
            "MBPP_TASK_FILE": str(task_path),
        },
    )

    async with client:
        print("=== TOOLS MANUAL ===")
        print(await client.build_tools_manual())

        solution = """
def square(number):
    return number * number
"""

        print("\n=== FIRST CALL ===")
        print(
            await client.call_tool(
                "run_tests",
                {
                    "solution": solution,
                },
            )
        )

        print("\n=== SECOND CALL ===")
        print(
            await client.call_tool(
                "run_tests",
                {
                    "solution": solution,
                },
            )
        )


if __name__ == "__main__":
    asyncio.run(main())