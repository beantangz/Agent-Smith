import ast
# va verifier la structure du code produit par l'agent, pour s'assurer qu'il suit le protocole attendu :
# solution doit etre une str, et doit etre assigné a une variable nommée solution, puis faire :
# run_tests(solution) ou final_answer(solution)
# sinon -> Error

class ActionValidationError(Exception):
    """Raised when an agent action does not follow the protocol."""


def validate_agent_action(code: str) -> None:
    """Validate the structure of code produced by the agent."""

    try:
        tree = ast.parse(code)
    except SyntaxError as error:
        raise ActionValidationError(
            f"Invalid Python syntax: {error.msg}"
        ) from error

    solution_value = _find_solution_value(tree)

    if solution_value is None:
        raise ActionValidationError(
            "You must assign the complete Python solution to a "
            "variable named solution. The value of solution must be "
            "a string."
        )

    if not solution_value.strip():
        raise ActionValidationError(
            "The solution string cannot be empty."
        )

    action_calls = _find_action_calls(tree)

    if not action_calls:
        raise ActionValidationError(
            "Your code must call run_tests(solution) or "
            "final_answer(solution). Defining the requested function "
            "without calling one of these functions is not sufficient."
        )

    if len(action_calls) > 1:
        raise ActionValidationError(
            "Your code must contain exactly one action call. "
            "Call either run_tests(solution) or "
            "final_answer(solution), but not both."
        )

    action_call = action_calls[0]
    action_name = _get_call_name(action_call)

    if action_call.keywords:
        raise ActionValidationError(
            f"{action_name}() must be called with one positional "
            "argument: solution."
        )

    if len(action_call.args) != 1:
        raise ActionValidationError(
            f"{action_name}() expects exactly one argument: solution."
        )

    argument = action_call.args[0]

    if not (
        isinstance(argument, ast.Name)
        and argument.id == "solution"
    ):
        raise ActionValidationError(
            f"{action_name}() must receive the solution string "
            f"variable, using this exact format: "
            f"{action_name}(solution)."
        )


def _find_solution_value(
    tree: ast.AST,
) -> str | None:
    """Find a literal string assigned to the solution variable."""

    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue

        assigns_solution = any(
            isinstance(target, ast.Name)
            and target.id == "solution"
            for target in node.targets
        )

        if not assigns_solution:
            continue

        if not (
            isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            raise ActionValidationError(
                "The solution variable must contain a literal string, "
                "not a function, object, or another data type."
            )

        return node.value.value

    return None


def _find_action_calls(
    tree: ast.AST,
) -> list[ast.Call]:
    """Find calls to the functions exposed by the sandbox."""

    action_names = {
        "run_tests",
        "final_answer",
    }

    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and _get_call_name(node) in action_names
    ]


def _get_call_name(call: ast.Call) -> str | None:
    """Return the name of a direct function call."""

    if isinstance(call.func, ast.Name):
        return call.func.id

    return None