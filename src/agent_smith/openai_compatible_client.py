import time

import httpx

from agent_smith.llm_client import LLMClient, LLMResponse


class LLMClientError(Exception):
    """Raised when an LLM request fails."""


class OpenAICompatibleClient(LLMClient):
    """Client for providers using an OpenAI-compatible API."""

    def __init__(
        self,
        api_url: str,
        model_name: str,
        api_key: str,
        timeout_seconds: float = 60.0,
    ) -> None:
        self.api_url = api_url.rstrip("/")
        self.model_name = model_name
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_output_tokens: int | None = None,
    ) -> LLMResponse:
        start_time = time.monotonic()

        request_body = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
        }
        if max_output_tokens is not None:
            if max_output_tokens <= 0:
                raise LLMClientError(
                    "max_output_tokens must be greater than zero"
                )

            request_body["max_completion_tokens"] = max_output_tokens

        headers = {
            "Authorization": f"Bearer {self.api_key}", # cles d'API pour authentification, privee
            "Content-Type": "application/json",
        }

        try:
            response = httpx.post( # envoie a l'api (POST) et recupere la reponse
                f"{self.api_url}/chat/completions", #URL de l'api
                headers=headers,
                json=request_body,
                timeout=self.timeout_seconds,
            )

            response.raise_for_status() # tchek si POST a reussi
            data = response.json()

        except httpx.HTTPError as error:
            raise LLMClientError(
                f"LLM HTTP request failed: {error}"
            ) from error
        except ValueError as error:
            raise LLMClientError(
                "The LLM provider returned invalid JSON"
            ) from error

        elapsed_ms = (
            time.monotonic() - start_time
        ) * 1000

        try:
            content = data["choices"][0]["message"]["content"] # recuperation de la reponse 
            usage = data.get("usage", {}) #tokens utilises pour la requete

            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)

        except (KeyError, IndexError, TypeError) as error:
            raise LLMClientError(
                "Unexpected response format from LLM provider"
            ) from error

        return LLMResponse( # retourne un format normalise de la reponse de l'API
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            request_time_ms=elapsed_ms,
            api_url=self.api_url,
            model_name=self.model_name,
            retries=0,
        )