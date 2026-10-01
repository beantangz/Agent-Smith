import asyncio
import time

from agent_smith.code_extractor import (
    CodeExtractionError,
    extract_python_code,
)
from agent_smith.action_validator import (
    ActionValidationError,
    validate_agent_action,
)
from agent_smith.llm_client import LLMClient
from agent_smith.output_models import SolutionOutput, StepMetrics
from agent_smith.prompts import (
    MBPP_SYSTEM_PROMPT,
    build_mbpp_user_prompt,
)
from agent_smith.sandbox.executor import Sandbox
from agent_smith.task_models import MBPPTaskInput


class MBPPAgent:
    """Solve an MBPP task using an LLM and a sandbox."""

    def __init__(
        self,
        llm_client: LLMClient,
        sandbox: Sandbox,
        max_iterations: int = 10,
        max_input_tokens: int = 6000,
        max_output_tokens: int = 1500,
        timeout_seconds: float = 120.0,
    ) -> None:
        self.llm_client = llm_client
        self.sandbox = sandbox
        self.max_iterations = max_iterations
        self.max_input_tokens = max_input_tokens
        self.max_output_tokens = max_output_tokens
        self.timeout_seconds = timeout_seconds

    async def run(
        self,
        task: MBPPTaskInput,
    ) -> SolutionOutput:
        """Run the Thought-Code-Observation loop."""

        start_time = time.monotonic()
        user_prompt = build_mbpp_user_prompt(task)

        steps: list[StepMetrics] = []
        total_input_tokens = 0
        total_output_tokens = 0
        total_requests = 0

        for iteration in range(1, self.max_iterations + 1): # boucle principale de l'agent, chaque iteration = une requete au LLM
            elapsed_time = time.monotonic() - start_time
            remaining_time = self.timeout_seconds - elapsed_time

            if remaining_time <= 0:
                return self._build_result( # solution output avec error
                    task=task,
                    success=False,
                    solution="",
                    steps=steps,
                    total_requests=total_requests,
                    total_input_tokens=total_input_tokens,
                    total_output_tokens=total_output_tokens,
                    start_time=start_time,
                    error="Agent execution timed out",
                )

            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread( # run la fonction generate() (synchrone) dans un thread pour ne pas bloquer
                        self.llm_client.generate,
                        MBPP_SYSTEM_PROMPT,
                        user_prompt,
                    ),
                    timeout=remaining_time,
                )
            except asyncio.TimeoutError: #erreur timout LLM
                return self._build_result(
                    task=task,
                    success=False,
                    solution="",
                    steps=steps,
                    total_requests=total_requests,
                    total_input_tokens=total_input_tokens,
                    total_output_tokens=total_output_tokens,
                    start_time=start_time,
                    error="LLM request timed out",
                )
            except Exception as error: # toutes les autres erreurs (ex: probleme de connexion, erreur de l'API LLM)
                return self._build_result(
                    task=task,
                    success=False,
                    solution="",
                    steps=steps,
                    total_requests=total_requests,
                    total_input_tokens=total_input_tokens,
                    total_output_tokens=total_output_tokens,
                    start_time=start_time,
                    error=(
                        f"LLM request failed: "
                        f"{type(error).__name__}: {error}"
                    ),
                )

            total_requests += 1
            total_input_tokens += response.input_tokens
            total_output_tokens += response.output_tokens

            if total_input_tokens > self.max_input_tokens: #tchek limites tokens
                return self._build_result(
                    task=task,
                    success=False,
                    solution="",
                    steps=steps,
                    total_requests=total_requests,
                    total_input_tokens=total_input_tokens,
                    total_output_tokens=total_output_tokens,
                    start_time=start_time,
                    error="Maximum input token budget exceeded",
                )

            if total_output_tokens > self.max_output_tokens: #tchek limites tokens
                return self._build_result(
                    task=task,
                    success=False,
                    solution="",
                    steps=steps,
                    total_requests=total_requests,
                    total_input_tokens=total_input_tokens,
                    total_output_tokens=total_output_tokens,
                    start_time=start_time,
                    error="Maximum output token budget exceeded",
                )

            try:
                sandbox_code = extract_python_code( # extraction code python de la rep du LLM
                    response.content
                )
            except CodeExtractionError as error:
                observation = (
                    f"Code extraction failed: {error}"
                )

                steps.append( # si erreur extraction, on ajoute un step avec l'erreur
                    StepMetrics(
                        step=iteration,
                        input_tokens=response.input_tokens,
                        output_tokens=response.output_tokens,
                        request_time_ms=response.request_time_ms,
                        api_url=response.api_url,
                        model_name=response.model_name,
                        llm_output=response.content,
                        sandbox_output=observation, # code extraction failer, voir erreur au dessus
                        retries=response.retries,
                    )
                )

                user_prompt = self._add_observation( # on ajoute l'erreur au prompt pour la prochaine iteration
                    user_prompt=user_prompt,
                    iteration=iteration,
                    llm_output=response.content,
                    observation=observation, # code extrac failed
                )
                continue # refait passer a l'iteration de la boucle principale -> retour au debut

            elapsed_time = time.monotonic() - start_time
            remaining_time = self.timeout_seconds - elapsed_time

            if remaining_time <= 0: # tchek timeout avant d'envoyer le code a la sandbox
                return self._build_result(
                    task=task,
                    success=False,
                    solution="",
                    steps=steps,
                    total_requests=total_requests,
                    total_input_tokens=total_input_tokens,
                    total_output_tokens=total_output_tokens,
                    start_time=start_time,
                    error="Agent execution timed out",
                )

            try: # verification format reponse LLM -> doit avoir code python en str, et appel a run_tests() ou final_answer()
                validate_agent_action(sandbox_code)
            except ActionValidationError as error:
                observation = (
                    "Agent action validation failed:\n"
                    f"{error}\n\n"
                    "Required test format:\n"
                    "solution = \"\"\"\n"
                    "# complete Python solution\n"
                    "\"\"\"\n"
                    "observation = run_tests(solution)\n"
                    "print(observation)\n\n"
                    "Required final format:\n"
                    "solution = \"\"\"\n"
                    "# exact successfully tested solution\n"
                    "\"\"\"\n"
                    "final_answer(solution)"
                )
                steps.append(
                    StepMetrics(
                        step=iteration,
                        input_tokens=response.input_tokens,
                        output_tokens=response.output_tokens,
                        request_time_ms=response.request_time_ms,
                        api_url=response.api_url,
                        model_name=response.model_name,
                        llm_output=response.content,
                        sandbox_input=sandbox_code,
                        sandbox_output=observation,
                        retries=response.retries,
                    )
                )
                user_prompt = self._add_observation(
                    user_prompt=user_prompt,
                    iteration=iteration,
                    llm_output=response.content,
                    observation=observation,
                )
                continue
            try:
                # le code fait tout le trajet, avec serveur MCP, process enfants et tout :
                #  -> sandbox.execute() -> _execute_in_child() 
                # -> exec() -> sandbox_result
                sandbox_result = await asyncio.wait_for( 
                    self.sandbox.execute(sandbox_code),
                    timeout=remaining_time,
                )
            except asyncio.TimeoutError: # error timout si sanbox
                return self._build_result(
                    task=task,
                    success=False,
                    solution="",
                    steps=steps,
                    total_requests=total_requests,
                    total_input_tokens=total_input_tokens,
                    total_output_tokens=total_output_tokens,
                    start_time=start_time,
                    error="Sandbox execution timed out",
                )

            observation = self._format_observation( # formatage texte python en un texte pour le LLM
                stdout=sandbox_result.stdout,
                stderr=sandbox_result.stderr,
                error=sandbox_result.error,
                timed_out=sandbox_result.timed_out,
            )

            steps.append(
                StepMetrics(
                    step=iteration,
                    input_tokens=response.input_tokens,
                    output_tokens=response.output_tokens,
                    request_time_ms=response.request_time_ms,
                    api_url=response.api_url, # url fournisseur LLM
                    model_name=response.model_name,
                    llm_output=response.content,
                    sandbox_input=sandbox_code,
                    sandbox_output=observation, # texte transmit au LLM pour le prochain prompt
                    retries=response.retries,
                )
            )

            if sandbox_result.final_answer is not None: # tache terminee ?
                return self._build_result(
                    task=task,
                    success=True,
                    solution=sandbox_result.final_answer,
                    steps=steps,
                    total_requests=total_requests,
                    total_input_tokens=total_input_tokens,
                    total_output_tokens=total_output_tokens,
                    start_time=start_time,
                    error=None,
                )

            user_prompt = self._add_observation( # on relance une iteration avec nvx prompt
                user_prompt=user_prompt,
                iteration=iteration,
                llm_output=response.content,
                observation=observation,
            )

        return self._build_result( # si nbre iteration fini et pas final answer -> erreur
            task=task,
            success=False,
            solution="",
            steps=steps,
            total_requests=total_requests,
            total_input_tokens=total_input_tokens,
            total_output_tokens=total_output_tokens,
            start_time=start_time,
            error="Maximum number of iterations reached",
        )

    @staticmethod
    def _format_observation(
        stdout: str,
        stderr: str,
        error: str | None,
        timed_out: bool,
    ) -> str:
        """Convert a sandbox result into text for the LLM."""

        return (
            f"stdout:\n{stdout or '<empty>'}\n\n"
            f"stderr:\n{stderr or '<empty>'}\n\n"
            f"error:\n{error or '<none>'}\n\n"
            f"timed_out: {timed_out}"
        )

    @staticmethod
    def _add_observation(
        user_prompt: str,
        iteration: int,
        llm_output: str,
        observation: str,
    ) -> str:
        """Add one attempt and its observation to the prompt."""

        if (
            "tests passed" in observation.lower()
            and "failed" not in observation.lower()
        ):
            next_instruction = (
                "All tests passed. In your next response, recreate the exact "
                "successfully tested solution as a string named solution, then "
                "call final_answer(solution). Do not explain the solution. "
                "Do not return the function by itself. Do not call run_tests "
                "again."
            )
        elif (
            "stdout:\n<empty>" in observation
            and "error:\n<none>" in observation
        ):
            next_instruction = (
                "Your code finished without calling an available function. "
                "You must either call run_tests(solution), or call "
                "final_answer(solution) if a previous observation already "
                "confirmed that all tests passed."
            )
        else:
            next_instruction = (
                "Use the real sandbox observation to correct the solution. "
                "Return exactly one executable Python code block and call "
                "run_tests(solution)."
            )

        return (
            f"{user_prompt}\n\n"
            f"--- Iteration {iteration} ---\n\n"
            f"Previous model response:\n"
            f"{llm_output}\n\n"
            f"Real sandbox observation:\n"
            f"{observation}\n\n"
            f"Required next action:\n{next_instruction}"
        )

    @staticmethod
    def _build_result( # tranmettre le return final de l'agent, avec toutes les metrics et infos
        task: MBPPTaskInput,
        success: bool,
        solution: str,
        steps: list[StepMetrics],
        total_requests: int,
        total_input_tokens: int,
        total_output_tokens: int,
        start_time: float,
        error: str | None,
    ) -> SolutionOutput:
        """Build the normalized final result."""

        return SolutionOutput(
            task_id=str(task.task_id),
            benchmark="mbpp",
            success=success,
            solution=solution,
            iterations=len(steps),
            total_requests=total_requests,
            total_input_tokens=total_input_tokens,
            total_output_tokens=total_output_tokens,
            total_time_seconds=(
                time.monotonic() - start_time
            ),
            steps=steps,
            system_prompt=MBPP_SYSTEM_PROMPT,
            error=error,
        )