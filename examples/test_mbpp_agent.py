import asyncio
import os
import sys
from pathlib import Path

from agent_smith.agent.mbpp_agent import MBPPAgent
from agent_smith.mcp_client import StdioMCPClient
from agent_smith.openai_compatible_client import (
    OpenAICompatibleClient,
)
from agent_smith.sandbox.executor import Sandbox
from agent_smith.task_loader import load_mbpp_task


async def main() -> None:
    project_root = Path(__file__).resolve().parent.parent

    task_path = (
        project_root
        / "examples"
        / "mbpp_square.json"
    )
    server_path = project_root / "mcp_tools_mbpp.py"

    api_key = os.getenv("OPENROUTER_API_KEY")

    if not api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not defined"
        )

    task = load_mbpp_task(task_path)

    llm_client = OpenAICompatibleClient(
        api_url="https://openrouter.ai/api/v1",
        model_name="openrouter/free",
        api_key=api_key,
        timeout_seconds=60.0,
    )

    mcp_client = StdioMCPClient(
        command=sys.executable,
        args=[str(server_path)],
        env={
            "MBPP_TASK_FILE": str(task_path),
        },
    )

    async with mcp_client:
        sandbox = Sandbox(
            mcp_client=mcp_client,
            timeout_seconds=15.0,
        )

        agent = MBPPAgent(
            llm_client=llm_client,
            sandbox=sandbox,
        )

        result = await agent.run(task) # lance l'agent

    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())