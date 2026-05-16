from sand_bob._utilities import remove_outer_markdown

from ._parallel import parallel


GOOD_CODE = "Overall the code looks good."

def system_prompt_code_generation(display_output_path, dependencies):
    """Build the system prompt used for code generation.

    Parameters
    ----------
    display_output_path : str
        Output directory path in the execution environment where generated code
        should store final artifacts.
    dependencies : list[str]
        Allowed dependency names that generated code may import.

    Returns
    -------
    str
        Prompt text with framework constraints and output requirements.
    """
    from ._config import config

    dependencies_str = ", ".join(dependencies)
    return config.prompt_template_code_generation.format(
        dependencies_str=dependencies_str,
        display_output_path=display_output_path,
    )

def system_prompt_code_feedback(display_output_path):
    """Build the system prompt used for code-feedback generation.

    Parameters
    ----------
    display_output_path : str
        Output directory path in the execution environment used in feedback
        requirements for saved artifacts.

    Returns
    -------
    str
        Prompt text describing feedback categories and expectations.
    """
    from ._config import config

    return config.prompt_template_code_feedback.format(
        display_output_path=display_output_path
    )

def determine_missing_dependencies(code, stdout, stderr):
    """Infer missing packages from execution output.

    Parameters
    ----------
    code : str
        Code that was executed.
    stdout : str
        Standard output captured from execution.
    stderr : str
        Standard error captured from execution.

    Returns
    -------
    list[str]
        Missing dependency names filtered to the configured whitelist.
    """
    import json
    from sand_bob import WHITELIST_DEPENDENCIES, config
    from sand_bob._utilities import extract_code

    prompt = config.prompt_template_determine_missing_dependencies.format(
        code=code,
        stdout=stdout,
        stderr=stderr,
    )

    #import time
    #start_time = time.time()
    response = extract_code(config.prompt_function_determine_dependencies(prompt))
    #print(f"Prompt time taken (determine_missing_dependencies): {time.time() - start_time:.2f}s")
    #print("Response (json dependencies):", response)
    try:
        missing_dependencies = json.loads(response)
    except Exception as e:
        #print(f"Error loading dependencies: {e} \n\n {response}")
        missing_dependencies = []

    return [dep for dep in missing_dependencies if dep in WHITELIST_DEPENDENCIES]


def fix_error_in_code(code, stdout, stderr):
    """Generate a revised code snippet to address a runtime failure.

    Parameters
    ----------
    code : str
        Original code that failed.
    stdout : str
        Standard output captured during failed execution.
    stderr : str
        Standard error captured during failed execution.

    Returns
    -------
    tuple[str, str]
        Tuple containing extracted replacement code and the repair prompt used
        for the model call.
    """
    from sand_bob import config
    from sand_bob._utilities import extract_code
    
    prompt = config.prompt_template_fix_error_in_code.format(
        code=code,
        stdout=stdout,
        stderr=stderr,
    )
    #import time
    #start_time = time.time()
    response = extract_code(config.prompt_function_fix_code(prompt))
    #print(f"Prompt time taken (fix_error_in_code): {time.time() - start_time:.2f}s")
    #print("Response (code):", response)

    return extract_code(response), prompt


def run_auto_fix(code, prompt=None, dependencies=[], input_host_path=None, input_container_path="/input_data", n_codefix_attempts=2, status_display=None, executor=None, gpu_support=False):
    """Execute code and iteratively repair dependency and runtime failures.

    Parameters
    ----------
    code : str
        Code or notebook source to execute.
    prompt : str, optional
        Prompt context attached to the resulting execution metadata.
    dependencies : list[str], optional
        Initial dependency list allowed for execution.
    input_host_path : str, optional
        Host path to mount as input data.
    input_container_path : str, default "/input_data"
        Container path where input data is mounted.
    n_codefix_attempts : int, default 2
        Maximum number of repair attempts.
    status_display : object, optional
        Status UI object supporting update and add_progress.
    executor : CodeExecutor, optional
        Executor instance to reuse across runs.
    gpu_support : bool, default False
        Whether to enable GPU-capable execution.

    Returns
    -------
    ExecutionResult
        Final execution result containing updated code, dependencies, and
        attempt metadata.
    """
    from sand_bob import execute, execute_notebook
    from sand_bob._utilities import is_notebook
    from sand_bob._executor import ExecutionResult

    dependencies = dependencies.copy()
    former_result = None

    n_a = -1

    for n_a in range(n_codefix_attempts + 1):
   
        if status_display is not None:
            status_display.update(f"Executing code...")

        #print(f"Executing with dependencies: {dependencies}")
        if is_notebook(code):
            result = execute_notebook(code, dependencies=dependencies, input_host_path=input_host_path, input_container_path=input_container_path, executor=executor, gpu_support=gpu_support)
        else:
            result = execute(code, dependencies=dependencies, input_host_path=input_host_path, input_container_path=input_container_path, executor=executor, gpu_support=gpu_support)
        result.prompt = prompt

        if status_display is not None:
            status_display.add_progress(1)

        prefix_former_result(result, former_result)

        if n_a == n_codefix_attempts:
            break

        
        former_result = result

        if "Traceback" in result.stdout:
            #display(result)
            if "ImportError" in result.stdout or "ModuleNotFoundError" in result.stdout:
                if status_display is not None:
                    status_display.update(f"Determining missing dependencies...")
                new_dependencies = determine_missing_dependencies(code, result.stdout, result.stderr)
                if status_display is not None:
                    status_display.add_progress(1)

                if len(new_dependencies) > 0:
                    for new_dependency in new_dependencies:
                        if new_dependency in dependencies:
                            new_dependencies.remove(new_dependency)

                    if len(new_dependencies) > 0:
                        dependencies.extend(new_dependencies)
                        #print(f"Executing again with new dependencies: {new_dependencies}")
                        continue
            
            if status_display is not None:
                status_display.update(f"Fixing error in code... ")
            new_code, prompt = fix_error_in_code(code, result.stdout, result.stderr)
            if status_display is not None:
                status_display.add_progress(1)

            if new_code is not None:
                code = new_code
                #print(f"Executing again with new code: {code[:100]}")
                continue
        if status_display is not None:
            status_display.add_progress(n_codefix_attempts - n_a)
        break


    #if len(dependencies) != len(original_dependencies):
    #    print(f"New dependency list: {dependencies}")

    #print("Sand box output:", result.stdout)

    result.code = code
    result.dependencies = dependencies
    result.n_codefix_attempts = n_a + 1

    return result

def generate_run(prompt, prefix_code=None, suffix_code=None, dependencies=[], input_host_path=None, input_container_path="/input_data", n_codefix_attempts=3, status_display=None, executor=None, gpu_support=False):
    """Generate code for a task and execute it with automatic repairs.

    Parameters
    ----------
    prompt : str
        User task description used to generate code.
    prefix_code : str, optional
        Code prepended before generated code.
    suffix_code : str, optional
        Code appended after generated code.
    dependencies : list[str], optional
        Allowed dependency list for generation and execution.
    input_host_path : str, optional
        Host path to mount as input data.
    input_container_path : str, default "/input_data"
        Container mount path for input data.
    n_codefix_attempts : int, default 3
        Maximum number of automatic repair attempts.
    status_display : object, optional
        Status UI object supporting update and add_progress.
    executor : CodeExecutor, optional
        Executor instance to reuse across runs.
    gpu_support : bool, default False
        Whether to enable GPU-capable execution.

    Returns
    -------
    ExecutionResult
        Execution result for the generated code.
    """
    from ._utilities import extract_code
    from ._config import config
    
    if prefix_code:
        code = prefix_code + "\n"
    else:
        code = ""
    #import time
    #start_time = time.time()

    system_prompt = system_prompt_code_generation("/display_output", dependencies=dependencies)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
        ]
    
    if status_display is not None:
        status_display.update(f"Generating code...")
    code = code + extract_code(config.prompt_function_generate_code(messages))
    #print(f"Prompt time taken (generate_run): {time.time() - start_time:.2f}s")
    if suffix_code:
        code += "\n" + suffix_code

    if status_display is not None:
        status_display.add_progress(1)

    #print("input_host_path:", input_host_path)

    result = run_auto_fix(code, prompt=system_prompt + "\n\n" + prompt,
                          dependencies=dependencies, 
                          input_host_path=input_host_path, 
                          input_container_path=input_container_path,
                          n_codefix_attempts=n_codefix_attempts, status_display=status_display, executor=executor, gpu_support=gpu_support)
    #result.prompt = system_prompt + "\n\n" + prompt
    
    return result


def generate_code_feedback(code, list_of_objects=[], purpose=None):
    """Request qualitative feedback for code and its produced outputs.

    Parameters
    ----------
    code : str
        Executed code to review.
    list_of_objects : list, optional
        Execution outputs represented as typed objects.
    purpose : str, optional
        Original task context to include in the feedback request.

    Returns
    -------
    str
        Feedback text returned by the configured model endpoint.
    """
    from ._config import config
    
    if purpose is None:
        prefix = "We executed the following code and want to know it can be improved:"
    else:
        prefix = f"""
We had a task and wrote code for it. Now we executed the code, have the results, and want to know if the code can be improved, also in the context of the task.

# Task

{purpose}

# Code

We executed the following code:

```
"""

    suffix = f"""
```

# Request for feedback
Please let us know, what could be done to improve the code. 
If there are no improvements, simply say '{GOOD_CODE}' by the end.
"""

    messages = [{"role": "system", "content": system_prompt_code_feedback("/display_output")}] + \
        code_and_outputs_to_messages(code, list_of_objects, 
                                    prefix=prefix, 
                                    suffix=suffix)

    #import time
    #start_time = time.time()
    res = config.prompt_function_generate_code_feedback(messages)
    #print(f"Prompt time taken (generate_code_feedback): {time.time() - start_time:.2f}s")
    return res


def code_and_outputs_to_messages(code: str, list_of_objects, prefix, suffix):
    """Convert code and execution outputs into multimodal chat messages.

    Parameters
    ----------
    code : str
        Code content to include in the message.
    list_of_objects : list[dict]
        Output objects, including text values and optional image payloads.
    prefix : str
        Text placed before code and outputs.
    suffix : str
        Text appended after outputs.

    Returns
    -------
    list[dict]
        Chat message payload suitable for model APIs supporting text and image
        content items.
    """
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
            image_messages.append({"type": "image_url", "image_url": {"url": "data:image/png;base64," +output['data']}})
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
                {"type": "text", "text": outputs}] + image_messages
        }]

    return messages


def incorporate_feedback(code, prompt, feedback, dependencies=[], input_host_path=None, input_container_path="/input_data", status_display=None, executor=None, gpu_support=False):
    """Regenerate code by incorporating reviewer feedback.

    Parameters
    ----------
    code : str
        Current code implementation.
    prompt : str
        Original task description.
    feedback : str
        Reviewer feedback describing desired improvements.
    dependencies : list[str], optional
        Dependency list used for regeneration and execution.
    input_host_path : str, optional
        Host path to mount as input data.
    input_container_path : str, default "/input_data"
        Container path for mounted input data.
    status_display : object, optional
        Status UI object supporting update and add_progress.
    executor : CodeExecutor, optional
        Executor instance to reuse across runs.
    gpu_support : bool, default False
        Whether to enable GPU-capable execution.

    Returns
    -------
    ExecutionResult
        Execution result for regenerated code.
    """
    from ._config import config

    generation_prompt = config.prompt_template_incorporate_feedback.format(
        task=prompt,
        code=code,
        feedback=feedback,
    )
    res = generate_run(generation_prompt, dependencies=dependencies, input_host_path=input_host_path, input_container_path=input_container_path, status_display=status_display, executor=executor, gpu_support=gpu_support)
    
    return res

@parallel
def generate_and_optimize_code(prompt, dependencies=[], input_host_path=None, input_container_path="/input_data", n_codefix_attempts=2, n_feedback_iterations=1, final_touch=True, gpu_support=False):
    """Generate, execute, review, and iteratively improve task-specific code.

    Parameters
    ----------
    prompt : str
        Task description used to generate and optimize code.
    dependencies : list[str], optional
        Allowed dependency list for generation and execution.
    input_host_path : str, optional
        Host path to mount as input data.
    input_container_path : str, default "/input_data"
        Container path where input data is mounted.
    n_codefix_attempts : int, default 2
        Maximum repair attempts per generation iteration.
    n_feedback_iterations : int, default 1
        Maximum number of feedback-driven optimization rounds.
    final_touch : bool, default True
        Whether to convert final code into a more readable notebook format.
    gpu_support : bool, default False
        Whether to enable GPU-capable execution.

    Returns
    -------
    ExecutionResult or list[ExecutionResult]
        Final optimized execution result, or a list when called through the
        parallel wrapper or in iterative mode.
    """

    from IPython.display import display, Markdown, HTML
    from ._utilities import markdown_to_html
    from ._statusdisplay import StatusDisplay
    from ._executor import CodeExecutor
    import time

    status_display = StatusDisplay(total_steps=(n_feedback_iterations+1)*(n_codefix_attempts+1)*2, status_text="Initializing...")

    start_time = time.time()

    # Create a shared executor instance to reuse across iterations
    executor = CodeExecutor(gpu_support=gpu_support)

    # code generation and execution
    former_result = None
    res = generate_run(prompt, dependencies=dependencies, input_host_path=input_host_path, input_container_path=input_container_path, n_codefix_attempts=n_codefix_attempts, status_display=status_display, executor=executor, gpu_support=gpu_support)
    
    n_a = 0
    for n_a in range(n_feedback_iterations):
        dependencies = res.dependencies
        code_before = res.code
        former_result = res
        #print("len code (bef):", len(res.code))

        #display(Markdown(f"# {n_a + 1}. Result"))
        #display(res)

        # code inspection and feedback
        status_display.update(f"Generating feedback...")
        feedback = generate_code_feedback(res.code, res.outputs, purpose=prompt)
        status_display.add_progress(1)

        
        res.feedback = feedback

        #display(HTML("<details><summary>Feedback</summary>" + markdown_to_html(feedback) + "</details>"))

        if GOOD_CODE in feedback:
            if status_display is not None:
                status_display.add_progress((n_feedback_iterations - 1 - n_a)*(n_codefix_attempts+1))
            break

        # incorporating feedback
        #status_display.update(f"Incorporating feedback and regenerating code... {status_text}", progress / max_progress * 100)
        res = incorporate_feedback(res.code, prompt, feedback, dependencies=dependencies, input_host_path=input_host_path, input_container_path=input_container_path, status_display=status_display, executor=executor, gpu_support=gpu_support)

        #print("len code (aft):", len(res.code))

        if res.code == code_before:
            #print("Code did not change. Stopping.")
            if status_display is not None:
                status_display.add_progress((n_feedback_iterations - 1 - n_a)*(n_codefix_attempts+1))
            break

        prefix_former_result(res, former_result)

        former_result = res


    # Apply final touch to make the code look nice in a notebook
    if final_touch:
        status_display.update("Final touch")
        res = python_code_to_beautiful_notebook(res.code, original_task=prompt, dependencies=res.dependencies, input_host_path=input_host_path, input_container_path=input_container_path, executor=executor, gpu_support=gpu_support)
        prefix_former_result(res, former_result)

    status_display.update("")
    res.total_time = time.time() - start_time
    res.n_codefix_attempts = n_a + 1
    
    # Clean up the executor
    executor.cleanup()
    
    return res


def python_code_to_beautiful_notebook(source, original_task="", dependencies=[], input_host_path=None, input_container_path="/input_data", executor=None, gpu_support=False):
    """Convert Python source into a structured MystNB notebook and execute it.

    Parameters
    ----------
    source : str
        Python source to transform into notebook cells.
    original_task : str, optional
        Original task context to include in notebook narration.
    dependencies : list[str], optional
        Dependency list used when executing the generated notebook.
    input_host_path : str, optional
        Host path to mount as input data.
    input_container_path : str, default "/input_data"
        Container path where input data is mounted.
    executor : CodeExecutor, optional
        Executor instance to reuse for notebook execution.
    gpu_support : bool, default False
        Whether to enable GPU-capable execution.

    Returns
    -------
    ExecutionResult
        Execution result of the transformed notebook.
    """
    from ._config import config
    from ._utilities import erase_outputs_of_code_cells, remove_outer_markdown, fix_json

    dependencies_str = ", ".join(dependencies)

    original_task_prompt = ""
    if original_task:
        original_task_prompt = f"""
Also make sure the original task remains fulfilled: Mention the original task in the first markdown cell of the notebook.
The explanations further down in the notebook should refers to the original task where relevant.

Original task:
{original_task}
"""

    out, code = [], []

    def flush_code():
        if any(l.strip() for l in code):
            out.append("```{code-cell} ipython3\n" + "\n".join(code).strip() + "\n```\n")
        code.clear()

    for line in source.splitlines():
        s = line
        if s.startswith("#"):
            flush_code()
            text = s.lstrip("#").strip()
            level = len(s) - len(s.lstrip("#"))
            out.append(("#" * level + " " + text if level > 1 else text) + "\n")
        else:
            code.append(line.rstrip())

    flush_code()
    prompt = config.prompt_template_python_code_to_beautiful_notebook.format(
        draft_notebook="\n".join(out),
        original_task_prompt=original_task_prompt,
    )

    #print("prompt:", prompt)

    notebook_str = config.prompt_function_notebook_conversion(prompt)
    #notebook_str = remove_outer_markdown(notebook_str)
    if "```markdown" in notebook_str:
        notebook_str = "```markdown".join(notebook_str.split("```markdown")[1:])
        notebook_str = "```".join(notebook_str.split("```")[:-1])
    notebook_str = notebook_str.split("<notebook>")[-1].split("</notebook>")[0]
    notebook_str = notebook_str.replace("```python", "```{{code-cell}} ipython3")

    notebook_str = """---
kernelspec:
  name: python3
  display_name: python3
jupytext:
  text_representation:
    extension: .md
    format_name: myst
    format_version: '0.13'
    jupytext_version: 1.13.8
---
""" + notebook_str.split("\n---\n")[-1] 

    #print("result:", notebook_str)

    
    #try:
        #notebook_str = fix_json(notebook_str)

        #notebook_str = myst_nb_to_json(notebook_str)

        #notebook_str = erase_outputs_of_code_cells(notebook_str)
    #except Exception as e:
        #print(f"Error fixing json or erasing outputs of code cells: {e}")
        #with open("notebook_str.json", "w", encoding="utf-8") as f:
        #    f.write(notebook_str)
        #notebook_str = notebook_str
        #pass

    from ._executor import execute_notebook
    res = execute_notebook(notebook_mystnb=notebook_str, dependencies=dependencies, input_host_path=input_host_path, input_container_path=input_container_path, executor=executor, gpu_support=gpu_support)
    res.prompt = prompt

    #feedback = generate_code_feedback(code=res.code, list_of_objects=res.outputs, purpose="The markdown cells in this notebook should fit to the code cells and respective output. Refine the markdown cells only. Leave the code as it is.")
    #res = incorporate_feedback(code=res.code, prompt=original_task, feedback=feedback, dependencies=dependencies, input_host_path=input_host_path, input_container_path=input_container_path)

    return res

def myst_nb_to_json(myst_nb_str):
    """Convert MystNB markdown text into an ipynb JSON string.

    Parameters
    ----------
    myst_nb_str : str
        Notebook content in Myst markdown format.

    Returns
    -------
    str
        Notebook serialized in ipynb JSON format.
    """
    import jupytext
    nb = jupytext.reads(myst_nb_str, fmt="myst")
    ipynb_text = jupytext.writes(nb, fmt="ipynb")
    return ipynb_text

def generate_code(*args, **kwargs):
    """Generate code and normalize list output into ExecutionResultList.

    Parameters
    ----------
    *args
        Positional arguments forwarded to generate_and_optimize_code.
    **kwargs
        Keyword arguments forwarded to generate_and_optimize_code.

    Returns
    -------
    ExecutionResult or ExecutionResultList
        Wrapped execution result.
    """
    from ._executor import ExecutionResultList
    result = generate_and_optimize_code(*args, **kwargs)
    if isinstance(result, list):
        return ExecutionResultList(result)
    else:
        return result

def prefix_former_result(result, former_result):
    """Attach a previous result at the end of a result chain.

    Parameters
    ----------
    result : ExecutionResult
        Current execution result that may already reference earlier results.
    former_result : ExecutionResult or None
        Result to append as the earliest predecessor.

    Returns
    -------
    None
        This function mutates the chain in place.
    """
    while result.former_result is not None:
        result = result.former_result
    result.former_result = former_result

def summarize_code(code:str):
    """Summarize core algorithms used in a code snippet.

    Parameters
    ----------
    code : str
        Python code to summarize.

    Returns
    -------
    str
        Bullet-point summary focused on core algorithms.
    """

    prompt = f"""
You are an expert in python programming. You are given a python code snippet.
Your task is to summarize the code in a bullet point list mentioning the names of the used core-algorithms.
Stay concise, do not mention minor details, but focus on the core of what the code is doing and how it is doing it.

# Code
```
{code}
```

# Summary
"""

    from ._config import config
    return config.prompt_function_summarize_code(prompt)
