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
from agent_smith.output_models import SolutionOutput
from agent_smith.result_writer import save_solution_output

async def run_one_task(
    task_path: Path,
    server_path: Path,
    llm_client: OpenAICompatibleClient,
) -> SolutionOutput:
    """Run the complete agent chain for one MBPP task."""

    task = load_mbpp_task(str(task_path))

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
            max_iterations=10,
            max_input_tokens=6000,
            max_output_tokens=1500,
            timeout_seconds=120.0,
        )

        return await agent.run(task)


async def main() -> None:
    project_root = Path(__file__).resolve().parent.parent

    server_path = project_root / "mcp_tools_mbpp.py"
    examples_directory = project_root / "examples"

    task_paths = [
        examples_directory / "mbpp_square.json",
        examples_directory / "mbpp_reverse_string.json",
        examples_directory / "mbpp_is_prime.json",
    ]

    api_key = os.getenv("OPENROUTER_API_KEY")

    if not api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not defined"
        )

    llm_client = OpenAICompatibleClient(
        api_url="https://openrouter.ai/api/v1",
        model_name="openrouter/free",
        api_key=api_key,
        timeout_seconds=60.0,
    )

    results: list[SolutionOutput] = []

    for task_path in task_paths:
        print()
        print("=" * 60)
        print(f"Running task: {task_path.name}")
        print("=" * 60)

        result = await run_one_task(
            task_path=task_path,
            server_path=server_path,
            llm_client=llm_client,
        )

        results.append(result)

        result_path = save_solution_output(
        result=result,
        output_directory=project_root / "results" / "mbpp",
        )
        print(f"Result saved to: {result_path}")

        print(f"Success: {result.success}")
        print(f"Iterations: {result.iterations}")
        print(f"Requests: {result.total_requests}")
        print(f"Input tokens: {result.total_input_tokens}")
        print(f"Output tokens: {result.total_output_tokens}")
        print(
            f"Time: {result.total_time_seconds:.2f} seconds"
        )

        if result.success:
            print("Solution:")
            print(result.solution)
        else:
            print(f"Error: {result.error}")

    successful_tasks = sum(
        1
        for result in results
        if result.success
    )

    total_requests = sum(
        result.total_requests
        for result in results
    )

    total_input_tokens = sum(
        result.total_input_tokens
        for result in results
    )

    total_output_tokens = sum(
        result.total_output_tokens
        for result in results
    )

    total_time = sum(
        result.total_time_seconds
        for result in results
    )

    print()
    print("=" * 60)
    print("MBPP SUITE SUMMARY")
    print("=" * 60)
    print(
        f"Passed: {successful_tasks}/{len(results)}"
    )
    print(f"Total requests: {total_requests}")
    print(f"Total input tokens: {total_input_tokens}")
    print(f"Total output tokens: {total_output_tokens}")
    print(f"Total time: {total_time:.2f} seconds")


if __name__ == "__main__":
    asyncio.run(main())