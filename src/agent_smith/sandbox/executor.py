import asyncio
import io
import multiprocessing
import time
from contextlib import redirect_stderr, redirect_stdout
from queue import Empty
from typing import Optional

from pydantic import BaseModel

from agent_smith.mcp_client import MCPClientError, StdioMCPClient


class SandboxResult(BaseModel):
    """Result of one sandbox execution."""

    stdout: str = ""
    stderr: str = ""
    error: Optional[str] = None #Optional[str] -> peut etre str ou None
    final_answer: Optional[str] = None
    tool_output: Optional[str] = None
    timed_out: bool = False


class FinalAnswerSignal(Exception):
    """Internal signal used to stop sandbox execution."""


def _execute_in_child(
    code: str,
    result_queue: multiprocessing.Queue,
    tool_request_queue: multiprocessing.Queue, # cannaux de communication entre process enfant qui exec le code et sandbox
    tool_response_queue: multiprocessing.Queue,
) -> None:
    """Execute generated code inside the child process."""

    stdout_buffer = io.StringIO()  # se comporte comme un fichier, mais reste juste en memoire
    stderr_buffer = io.StringIO()
    final_value: Optional[str] = None
    error_message: Optional[str] = None
    last_tool_output: Optional[str] = None



    def final_answer(answer: str) -> None:
        nonlocal final_value # pour modifier final value, sans creer une nvelle variable locale

        if not isinstance(answer, str):  # answer doit etre une str, sinon -> Raise
            raise TypeError(
                "final_answer() expects a string"
            )

        final_value = answer
        raise FinalAnswerSignal # on peut arreter le process



    def run_tests(solution: str) -> str:
        nonlocal last_tool_output

        if not isinstance(solution, str):
            raise TypeError(
                "run_tests() expects the solution as a string"
            )

        tool_request_queue.put(
            {
                "name": "run_tests",
                "arguments": {
                    "solution": solution,
                },
            }
        )

        response = tool_response_queue.get()

        if response["error"] is not None:
            raise RuntimeError(response["error"])
        
        last_tool_output = response["result"]

        return last_tool_output

    namespace = {
        "final_answer": final_answer,
        "run_tests": run_tests,
    }

    try:
        with redirect_stdout(stdout_buffer):
            with redirect_stderr(stderr_buffer):
                exec(code, namespace, namespace) #execute le code dans le process enfant

    except FinalAnswerSignal:
        pass

    except Exception as error:
        error_message = (
            f"{type(error).__name__}: {error}"
        )

    result_queue.put(  # envoie dan la Queu de communication entre process
        {
            "stdout": stdout_buffer.getvalue(),
            "stderr": stderr_buffer.getvalue(),
            "error": error_message,
            "final_answer": final_value,
            "tool_output": last_tool_output,
            "timed_out": False,
        }
    )


class Sandbox:
    """Execute Python code in a separate process."""

    def __init__(
        self,
        mcp_client: StdioMCPClient,
        timeout_seconds: float = 5.0,
    ) -> None:
        self.mcp_client = mcp_client
        self.timeout_seconds = timeout_seconds

    async def execute(self, code: str) -> SandboxResult: # fonction asyncrone
        context = multiprocessing.get_context("spawn") # creer un processes
 
        # cannaux de communication : (enfant = process de la sandbox qui exec le code du LLM)
        result_queue = context.Queue() # pour resultat final sandbox
        tool_request_queue = context.Queue() # enfant -> parent, nom du tool et args
        tool_response_queue = context.Queue() # parent -> enfant, resultat ou erreur
 
        process = context.Process( #prepare le code dans le process
            target=_execute_in_child, 
            args=(
                code,
                result_queue,
                tool_request_queue,
                tool_response_queue,
            ),
        )

        process.start() # lance le process, lance execute_in_child
        start_time = time.monotonic()

        try: # regarde si l'enfant fait une demande de tool
            while process.is_alive():
                elapsed_time = time.monotonic() - start_time

                if elapsed_time >= self.timeout_seconds:
                    process.terminate()
                    process.join() # attend que le process se termine

                    return SandboxResult(
                        error=(
                            "Execution timed out after "
                            f"{self.timeout_seconds} seconds"
                        ),
                        timed_out=True,
                    )

                try:
                    request = tool_request_queue.get_nowait() # regarde si une demande de l'enfant est arrivee
                except Empty:
                    await asyncio.sleep(0.01)
                    continue

                try:
                    tool_result = await self.mcp_client.call_tool( # appel MCP, qui va creer process et faire les tests
                        name=request["name"],
                        arguments=request["arguments"],
                    )

                    tool_response_queue.put( # envoie le resultat a l'enfant
                        {
                            "result": tool_result,
                            "error": None,
                        }
                    )

                except MCPClientError as error:
                    tool_response_queue.put(
                        {
                            "result": "",
                            "error": str(error),
                        }
                    )

            process.join()

            try:
                result_data = result_queue.get(timeout=1.0)
            except Empty:
                return SandboxResult(
                    error=(
                        "Sandbox process ended without "
                        "returning a result"
                    )
                )

            return SandboxResult(**result_data)

        finally:
            if process.is_alive():
                process.terminate()
                process.join()

            result_queue.close()
            tool_request_queue.close()
            tool_response_queue.close()