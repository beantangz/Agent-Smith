import io
import multiprocessing
from contextlib import redirect_stderr, redirect_stdout
from queue import Empty
from typing import Optional

from pydantic import BaseModel


class SandboxResult(BaseModel):
    """Result of one sandbox execution."""

    stdout: str = ""
    stderr: str = ""
    error: Optional[str] = None
    final_answer: Optional[str] = None #Optional[str] -> peut etre str ou None
    timed_out: bool = False


class FinalAnswerSignal(Exception):
    """Internal signal used to stop sandbox execution."""


def _execute_in_child(
    code: str,
    result_queue: multiprocessing.Queue,
) -> None:
    """Execute code inside the child process."""

    stdout_buffer = io.StringIO() # se comporte comme un fichier, mais reste juste en memoire
    stderr_buffer = io.StringIO()
    final_value: Optional[str] = None
    error_message: Optional[str] = None

    def final_answer(answer: str) -> None:
        nonlocal final_value # pour modifier final value, sans creer une nvelle variable locale

        if not isinstance(answer, str): # answer doit etre une str, sinon -> Raise
            raise TypeError(
                "final_answer() expects a string"
            )

        final_value = answer
        raise FinalAnswerSignal # on peut arreter le process

    namespace = {
        "final_answer": final_answer,
    }

    try:
        with redirect_stdout(stdout_buffer):
            with redirect_stderr(stderr_buffer):
                exec(code, namespace, namespace) #execute le code dans le process

    except FinalAnswerSignal:
        pass

    except Exception as error:
        error_message = (
            f"{type(error).__name__}: {error}"
        )

    result_queue.put( # envoie dan la Queu de communication entre process
        {
            "stdout": stdout_buffer.getvalue(),
            "stderr": stderr_buffer.getvalue(),
            "error": error_message,
            "final_answer": final_value,
            "timed_out": False,
        }
    )


class Sandbox:
    """Execute Python code in a separate process."""

    def __init__(
        self,
        timeout_seconds: float = 5.0,
    ) -> None:
        self.timeout_seconds = timeout_seconds

    def execute(self, code: str) -> SandboxResult:
        context = multiprocessing.get_context("spawn") # creer un processes
        result_queue = context.Queue() # creation Queue de communication entre process

        process = context.Process(
            target=_execute_in_child, #prepare le code dans le process
            args=(code, result_queue),
        )

        process.start() #lance le process
        process.join(self.timeout_seconds)

        if process.is_alive():
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
            result_data = result_queue.get( # recupere le dictionnaire de resultats du process
                timeout=1.0
            )
        except Empty:
            return SandboxResult(
                error=(
                    "Sandbox process ended without "
                    "returning a result"
                )
            )
        finally:
            result_queue.close() # ferme la queue qui utilise des ressources

        return SandboxResult(**result_data) # transforme le dictionnaire en objet SandboxResult