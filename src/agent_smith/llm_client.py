from abc import ABC, abstractmethod

from pydantic import BaseModel


class LLMResponse(BaseModel):
    #Normalized response returned by any LLM provider.

    content: str
    input_tokens: int
    output_tokens: int
    request_time_ms: float
    api_url: str
    model_name: str
    retries: int = 0

# class abstraite dont va heriter chaque LLM et devrai implementer generate()
class LLMClient(ABC):
    #Common interface implemented by every LLM provider

    @abstractmethod
    def generate(
        self,
        system_prompt: str, # regles : tu es un agent, blablabla, Cadrage general
        user_prompt: str, # probleme specifique a resoudre
    ) -> LLMResponse:
        """Send prompts to an LLM and return a normalized response."""
