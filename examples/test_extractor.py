from agent_smith.code_extractor import extract_python_code


llm_output = """
I will test the following implementation.

```python
def square(number):
    return number * number

run_tests(square)
```
"""

code = extract_python_code(llm_output)

print("=== EXTRACTED CODE ===")
print(code)