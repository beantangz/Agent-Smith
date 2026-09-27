import os

from agent_smith.openai_compatible_client import (
    LLMClientError,
    OpenAICompatibleClient,
)
from agent_smith.prompts import (
    MBPP_SYSTEM_PROMPT,
    build_mbpp_user_prompt,
)
from agent_smith.task_loader import load_mbpp_task


def main() -> None:
    api_key = os.getenv("OPENROUTER_API_KEY")

    if api_key is None:
        print("Error: OPENROUTER_API_KEY is not defined")
        return

    task = load_mbpp_task(
        "examples/mbpp_square.json"
    )

    user_prompt = build_mbpp_user_prompt(task)

    client = OpenAICompatibleClient(
        api_url="https://openrouter.ai/api/v1",
        model_name="openrouter/free",
        api_key=api_key,
    )

    try:
        response = client.generate(
            system_prompt=MBPP_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )
    except LLMClientError as error:
        print(f"LLM request failed: {error}")
        return

    print("=== MODEL RESPONSE ===")
    print(response.content)

    print("\n=== METRICS ===")
    print(f"Model: {response.model_name}")
    print(f"Input tokens: {response.input_tokens}")
    print(f"Output tokens: {response.output_tokens}")
    print(f"Request time: {response.request_time_ms:.2f} ms")


if __name__ == "__main__":
    main()