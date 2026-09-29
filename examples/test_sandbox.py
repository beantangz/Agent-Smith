from agent_smith.sandbox.executor import Sandbox


def main() -> None:
    sandbox = Sandbox(timeout_seconds=2.0)

    code = """
print("Beginning execution")

solution = "def square(number):\\n    return number * number"

final_answer(solution)

print("This line must not be executed")
"""

    result = sandbox.execute(code)

    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()