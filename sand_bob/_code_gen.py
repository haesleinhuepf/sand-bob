
def determine_missing_dependencies(code, stdout, stderr):
    import json
    from sand_bob import WHITELIST_DEPENDENCIES, config
    from sand_bob._utilities import simplify

    prompt = f"""
    You are an expert in python programming. You are given a traceback of an error that occurred when running a python code.
    Your task is to determine the missing dependencies that are required to run the code. This list could also be empty.
    The code is:
    ```python
    {code}
    ```
    The traceback is:
    ```
    {stdout}
    ```
    The error message is:
    ```
    {stderr}
    ```
    Return the missing dependencies in a JSON list and nothing else.
    """

    response = simplify(config.prompt_function_determine_dependencies(prompt))
    print("Response (json dependencies):", response)
    missing_dependencies = json.loads(response)

    return [dep for dep in missing_dependencies if dep in WHITELIST_DEPENDENCIES]


def determine_new_code(code, stdout, stderr):
    from sand_bob import config
    from sand_bob._utilities import extract_code
    
    prompt = f"""
    You are an expert in python programming. You are given python code, a traceback of an error that occurred when running the python code.
    Your task is to determine the new code that is required to fix the error.
    The code is:
    ```python	
    {code}
    ```
    The traceback is:
    ```
    {stdout}
    ```
    The error message is:
    ```
    {stderr}
    ```
    Return the new code and nothing else.
    """
    response = extract_code(config.prompt_function_fix_code(prompt))
    print("Response (code):", response)

    return extract_code(response)


def run_auto_fix(code, dependencies=[], input_host_path=None, input_container_path="/input_data", n_attempts=3):
    """
    Run the code and fix the dependencies or the code if needed.

    Args:
        code: The code to run.
        dependencies: The dependencies to use.
        input_host_path: The path to the input data on the host.
        input_container_path: The path to the input data in the container.
        n_attempts: The number of attempts to fix the dependencies or the code.
    
    Returns:
        The result of the execution, the potentially fixed code, and all dependencies including potentially new ones.
    """
    from sand_bob import execute
    original_dependencies = dependencies.copy()

    for n_a in range(n_attempts):
        result = execute(code, dependencies=dependencies, input_host_path=input_host_path, input_container_path=input_container_path)
        if "Traceback" in result.stdout:
            if "ImportError" in result.stdout or "ModuleNotFoundError" in result.stdout:
                new_dependencies = determine_missing_dependencies(code, result.stdout, result.stderr)
                if len(new_dependencies) == 0:
                    break
                dependencies.extend(new_dependencies)
                print(f"Executing again with new dependencies: {new_dependencies}")
            else:
                new_code = determine_new_code(code, result.stdout, result.stderr)
                if new_code is not None:
                    code = new_code
                    print(f"Executing again with new code: {new_code}")
                else:
                    break
        else:
            break

    if len(dependencies) != len(original_dependencies):
        print(f"New dependency list: {dependencies}")

    return result, code, dependencies, n_a + 1


def generate_run_check(prompt, additional_code=None, expected_output=None, dependencies=[], input_host_path=None, input_container_path="/input_data", n_attempts=3):
    """
    Generate a code snippet that runs the given prompt and checks if the output is as expected.
    """
    from ._utilities import extract_code, simplify
    from ._config import config
    
    code = extract_code(config.prompt_function_generate_code(prompt))
    if additional_code:
        code += "\n" + additional_code

    from sand_bob import execute

    result = run_auto_fix(code, 
                          dependencies=dependencies, 
                          input_host_path=input_host_path, 
                          input_container_path=input_container_path,
                          n_attempts=n_attempts)

    return simplify(result.stdout) == expected_output, code, result.stdout, result.stderr
