GOOD_CODE = "Overall the code looks good."

def system_prompt_code_generation():
    return """
You are an expert in python programming. You have a list of framework constraints which you MUST follow.
Your task is to generate a fully functional code snippet that will be used to fulfill the prompt.
Assume your code will be executed in a Jupyter notebook cell. That means you can use the `display` function to display results.

# Framework constraints
* Use the following libraries when necessary: {", ".join(WHITELIST_DEPENDENCIES)}
* When intermediate or final results are computed, use the pre-existing `display` function to display them.
* NEVER overwrite or redefine the `display` function. It exists for a reason.
* If the task is to generate a count, ratio or measurements, make sure to print the final result by the very end on a new line. 
  In this case, the second-last line should be the name of the measurement and a physical unit (if relevant)
"""

def system_prompt_code_feedback():
    return """
You are an expert in python programming, data analysis, visualization and statistics. 
When provided with Python code, together with corresponding results, 
you will be asked to provide feedback on the code. The code is either an entire 
Jupyter notebook or a code snippet that is executed in a Jupyter notebook code cell.

## Feedback categories
* Code quality: Check if the code is well-structured, readable, contains comments and follows best practices.
* Statistics: Check if best-practice statistics are used, e.g. check if pre-conditions are checked before statistical tests are performed.
* Image Analysis: In image processing workflows, check intermediate results are displayed and if they look reasonable.
* Data Analysis: Check if data is visualized before it is summarized.
* Sanity checks: If the code is longer, make sure that there are sanity checks for intermediate results.
* Documentation: Check if the code is documented and if the documentation is up to date.
* Error handling: Check if the code is robust and if it handles errors gracefully.
* Code style: Check if the code is formatted correctly and if it follows the PEP 8 style guide.
* Code complexity: 
  * Short and concise code is preferred. 
  * Do NOT propose adding main() functions as we are running the code in a Jupyter notebook.
  * Avoid determining and displaying results and measurements that are not relevant for the final result.                  

## Feedback content
Feedback should be short and concise. No need to be overly friendly.
Show old code (snippets) and the corresponding new code how you would improve it. 
Explain your modifications shortly.
Avoid tables.
"""

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
    #print("Response (json dependencies):", response)
    missing_dependencies = json.loads(response)

    return [dep for dep in missing_dependencies if dep in WHITELIST_DEPENDENCIES]


def fix_error_in_code(code, stdout, stderr):
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
    #print("Response (code):", response)

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
                #print(f"Executing again with new dependencies: {new_dependencies}")
            else:
                new_code = fix_error_in_code(code, result.stdout, result.stderr)
                if new_code is not None:
                    code = new_code
                    #print(f"Executing again with new code: {new_code}")
                else:
                    break
        else:
            break

    #if len(dependencies) != len(original_dependencies):
    #    print(f"New dependency list: {dependencies}")

    #print("Sand box output:", result.stdout)

    result.code = code
    result.dependencies = dependencies
    result.n_attempts = n_a + 1

    return result

def generate_run(prompt, prefix_code=None, suffix_code=None, dependencies=[], input_host_path=None, input_container_path="/input_data", n_attempts=3):
    """
    Generate a code snippet that runs the given prompt and checks if the output is as expected.
    """
    from ._utilities import extract_code
    from ._config import config
    
    if prefix_code:
        code = prefix_code + "\n"
    else:
        code = ""
    
    messages = [
        {"role": "system", "content": system_prompt_code_generation()},
        {"role": "user", "content": prompt}
        ]
    code = code + extract_code(config.prompt_function_generate_code(messages))
    if suffix_code:
        code += "\n" + suffix_code

    result = run_auto_fix(code, 
                          dependencies=dependencies, 
                          input_host_path=input_host_path, 
                          input_container_path=input_container_path,
                          n_attempts=n_attempts)
    
    return result


def generate_run_check(prompt, prefix_code=None, suffix_code=None, expected_output=None, dependencies=[], input_host_path=None, input_container_path="/input_data", n_attempts=3):

    from ._utilities import simplify

    result = generate_run(prompt=prompt, 
                                prefix_code=prefix_code, 
                                suffix_code=suffix_code, 
                                dependencies=dependencies, 
                                input_host_path=input_host_path, 
                                input_container_path=input_container_path, 
                                n_attempts=n_attempts)

    if isinstance(expected_output, str):
        result.result_check_ok = simplify(result.stdout) == expected_output
    elif callable(expected_output):
        result.result_check_ok = expected_output(result.stdout)
    else:
        raise ValueError(f"Expected output must be a string or a callable, got {type(expected_output)}")
    
    return result


def generate_code_feedback(code, list_of_objects=[], purpose=None):
    from ._config import config
    
    if purpose is None:
        prefix = "We executed the following code and want to know it can be improved:"
    else:
        prefix = f"""
We had a task and wrote code for it. Now we executed the code and want to know if the code can be improved, also in the context of the task.

# Task

{purpose}

# Code

We executed the following code:
"""

    messages = [{"role": "system", "content": system_prompt_code_feedback()}] + \
        code_and_outputs_to_messages(code, list_of_objects, 
                                    prefix=prefix, 
                                    suffix=f"Please let us know, what could be done to improve the code. If there is not much potential, simply say '{GOOD_CODE}' by the end.")

    return config.prompt_function_generate_code_feedback(messages)


def code_and_outputs_to_messages(code: str, list_of_objects, prefix, suffix):
    # Prepare text content and image messages
    text_parts = [f"""
{prefix}

```
{code}
```

And the result was:
```
"""]
    image_messages = []

    for i, output in enumerate(list_of_objects):
        if output["type"] == "image/png":
            image_messages.append({"type": "image_url", "image_url": {"url": output['data']}})
            text_parts.append(f"[img{len(image_messages) + 1}]")
        else:
            text_parts.append(str(output['data']))
    text_parts.append(f"""
```
{suffix}
""")

    # Combine text parts into one message
    outputs = "\n".join(text_parts)

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": outputs}]
        }]

    return messages


def incorporate_feedback(code, feedback, dependencies=[], input_host_path=None, input_container_path="/input_data"):
    res = generate_run(f"""
    Given some code and detailed feedback, propose new code that incroporates the feedback.

    # Code

    ```
    {code}
    ```

    # Feedback

    {feedback}

    # Your task
    Provide the updated code which incorporates the feedback. Skip all explanations.
    """, dependencies=dependencies, input_host_path=input_host_path, input_container_path=input_container_path)
    
    return res


def generate_and_optimize_code(code, dependencies=[], input_host_path=None, input_container_path="/input_data", n_attempts=3):
    # code generation and execution
    res = generate_run(code, dependencies=dependencies, input_host_path=input_host_path, input_container_path=input_container_path, n_attempts=n_attempts)
    for n_a in range(n_attempts):
        dependencies = res.dependencies

        # code inspection and feedback
        feedback = generate_code_feedback(res.code, res.outputs)

        if GOOD_CODE in feedback:
            res.feedback = feedback
            break

        # incorporating feedback
        old_res = res
        res = incorporate_feedback(res.code, feedback, dependencies=dependencies, input_host_path=input_host_path, input_container_path=input_container_path)
        res.predecessor = old_res
        dependencies = res.dependencies

        code = res.code
    return res

