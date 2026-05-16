from ._endpoints import prompt_scadsai_llm, prompt_openai, prompt_ollama, prompt_kisski
from functools import partial

class Config:
    def __init__(self):
        self.prompt_function_determine_dependencies = prompt_scadsai_llm
        self.prompt_function_generate_code = prompt_scadsai_llm
        self.prompt_function_fix_code = prompt_scadsai_llm
        self.prompt_function_generate_code_feedback = prompt_scadsai_llm
        self.prompt_function_summarize_code = prompt_scadsai_llm
        self.prompt_function_notebook_conversion = partial(prompt_scadsai_llm, model="meta-llama/Llama-4-Scout-17B-16E-Instruct")
        self.prompt_template_code_generation = """
You are an expert in python programming. You have a list of framework constraints which you MUST follow.
Your task is to generate a fully functional code snippet that will be used to fulfill the prompt.
Assume your code will be executed in a Jupyter notebook cell.

# Framework constraints
* You may use the following libraries, but only if necessary: {dependencies_str}
* pip install is STRICTLY PROHIBITED. You can only use the libraries mentioned above.
* Statistics: When applying statisticals test, ENSURE that pre-conditions for the tests are checked before the tests are performed.
* Final result output (print or display calls): 
  * The second-last print or display call should be a description of the result (e.g. the measurment and a physical unit if relevant).
  * The last print or display call should be the final result ONLY.
  * If the task is to generate a count, ratio or measurements, print the final result using a separate `print` call. 
  * If the task is to answer a yes/no question, print "Yes" or "No" using a separate `print` call. Do not create any JSON for this.
  * If the task is to generate a plot, display the plot.
  * Also plot intermediate results if possible.
* Final result output (file writing):
  * If the task is to generate a text or a string, write the text or string to "{display_output_path}/final_result.txt".
  * If the task is to generate a table, write the table to "{display_output_path}/final_result.csv".
  * If the task is to generate a number, list, array or dictionary, write the result to "{display_output_path}/final_result.json".
    In that case, do not add additional data structures. Simply json.dump the result to the file. E.g. if the result is x=2, then just do `json.dump(x, fp)`.
* Keep the code short and concise.
"""
        self.prompt_template_code_feedback = """
You are an expert in python programming, data analysis, visualization and statistics. 
When provided with Python code, together with corresponding results, 
you will be asked to provide feedback on the code. The code is either an entire 
Jupyter notebook or a code snippet that is executed in a Jupyter notebook code cell.

# Feedback categories
* Code quality: Check if the code is well-structured, readable, contains comments and follows best practices.
* Statistics: When applying statisticals test, ENSURE that pre-conditions for the tests are checked before the tests are performed.
* Image Analysis: 
  * In image processing workflows, check intermediate results are displayed and if they look reasonable.
  * If a segmentation is performed, make sure the objects are neither over- nor under-segmented.
  * If a segmentation is performed, make sure the right objects are segmented.
  * If segmented objects look good in one region but not in another, use histogram equalization to improve the image quality before segmenting the image.
  * If a segmentation result looks bad, propose a completely different segmentation method.
* Data Analysis: Check if data is visualized before it is summarized.
* Sanity checks: If the code is longer, make sure that there are sanity checks for intermediate results.
* Documentation: Check if the code is documented and if the documentation is up to date.
* Error handling: Check if the code is robust and if it handles errors gracefully.
* Correct file paths in the code in case they were specified differently in the task description.
* Do not write code for generating synthetic data unless your asked to explicitly.
* Code style: Check if the code is formatted correctly and if it follows the PEP 8 style guide.
* Code complexity: 
  * Short and concise code is preferred. 
  * If a result is a number, do not package it in complicated data structures. When dumping such results to a json file, simply do `json.dump(x, fp)`. Do NOT add dictionaries or lists around it.
  * Do NOT propose adding main() functions as we are running the code in a Jupyter notebook.
  * Avoid determining and displaying results and measurements that are not relevant for the final result.
* Final result
  * If the final result is a word, sentence or number, ensure that the final result is displayed using a separate print or display call by the very end of the code. 
  * If the final result is a dataframe, save it in the folder {display_output_path} as .csv file and print its filename in the final output of the program.
  * If the final result is an image, save it in the folder {display_output_path} as .tif file and print its filename in the final output of the program.
  * If the final result is a plot, save it in the folder {display_output_path} as .png and as .svg file and print its filename in the final output of the program. Additionally, display the plot.
  * If the final result is supposed to be "Yes" or "No", make sure to print "Yes" or "No" only. Do not create any JSON for this.

# Feedback content
Feedback should be short and concise. No need to be overly friendly.
Show old code (snippets) and the corresponding new code how you would improve it. 
Explain your modifications shortly.
Avoid tables.
"""
        self.prompt_template_determine_missing_dependencies = """
You are an expert in python programming. You are given a traceback of an error that occurred when running a python code.
Your task is to determine the missing dependencies that are required to run the code. This list could also be empty.
The code is:
```python
{code}
```

The errors and stdout are:
```
{stdout}
```

```
{stderr}
```
Return the missing dependencies in a JSON list and nothing else.
"""
        self.prompt_template_fix_error_in_code = """
You are an expert in python programming. You are given python code, and a traceback of an error that occurred when running the python code.
Your task is to determine the new code that is required to fix the error.
Make sure to keep the code format.

The code is:
```
{code}
```
The errors and stdout are:
```
{stdout}
```

```
{stderr}
```
Return the new code and nothing else.
"""
    
config = Config()

def config_openai(model: str="gpt-5-mini"):
    from ._config import config
    from ._endpoints import prompt_openai
    
    config.prompt_function_determine_dependencies = partial(prompt_openai, model=model)
    config.prompt_function_generate_code = partial(prompt_openai, model=model)
    config.prompt_function_fix_code = partial(prompt_openai, model=model)
    config.prompt_function_generate_code_feedback = partial(prompt_openai, model=model)
    config.prompt_function_summarize_code = partial(prompt_openai, model=model)
    config.prompt_function_notebook_conversion = partial(prompt_openai, model=model)

def config_kisski(model: str="openai-gpt-oss-120b", vision_model: str="qwen2.5-vl-72b-instruct"):
    from ._config import config
    from functools import partial
    from ._endpoints import prompt_kisski
    
    config.prompt_function_determine_dependencies = partial(prompt_kisski, model=model)
    config.prompt_function_generate_code = partial(prompt_kisski, model=model)
    config.prompt_function_fix_code = partial(prompt_kisski, model=model)
    config.prompt_function_generate_code_feedback = partial(prompt_kisski, model=vision_model)
    config.prompt_function_summarize_code = partial(prompt_kisski, model=model)
    config.prompt_function_notebook_conversion = partial(prompt_kisski, model=model)

def config_scadsai_llm(model:str="openai/gpt-oss-120b", vision_model: str="meta-llama/Llama-4-Scout-17B-16E-Instruct"):
    from ._config import config
    from functools import partial
    from ._endpoints import prompt_scadsai_llm
    
    config.prompt_function_determine_dependencies = partial(prompt_scadsai_llm, model=model)
    config.prompt_function_generate_code = partial(prompt_scadsai_llm, model=model)
    config.prompt_function_fix_code = partial(prompt_scadsai_llm, model=model)
    config.prompt_function_generate_code_feedback = partial(prompt_scadsai_llm, model=vision_model)
    config.prompt_function_summarize_code = partial(prompt_scadsai_llm, model=model)
    config.prompt_function_notebook_conversion = partial(prompt_scadsai_llm, model=model)


def config_kiara(model:str="vllm-deepseek-coder-33b-instruct", vision_model: str="vllm-llama-4-scout-17b-16e-instruct", notebook_conversion_model: str="vllm-llama-3-3-nemotron-super-49b-v1"):
    from ._config import config
    from functools import partial
    from ._endpoints import prompt_kiara
    
    config.prompt_function_determine_dependencies = partial(prompt_kiara, model=model)
    config.prompt_function_generate_code = partial(prompt_kiara, model=model)
    config.prompt_function_fix_code = partial(prompt_kiara, model=model)
    config.prompt_function_generate_code_feedback = partial(prompt_kiara, model=vision_model)
    config.prompt_function_summarize_code = partial(prompt_kiara, model=model)
    config.prompt_function_notebook_conversion = partial(prompt_kiara, model=notebook_conversion_model)


def config_ollama(model: str="qwen2.5-coder:3b"):
    from ._config import config
    from functools import partial
    from ._endpoints import prompt_ollama
    
    config.prompt_function_determine_dependencies = partial(prompt_ollama, model=model)
    config.prompt_function_generate_code = partial(prompt_ollama, model=model)
    config.prompt_function_fix_code = partial(prompt_ollama, model=model)
    config.prompt_function_generate_code_feedback = partial(prompt_ollama, model=model)
    config.prompt_function_summarize_code = partial(prompt_ollama, model=model)
    config.prompt_function_notebook_conversion = partial(prompt_ollama, model=model)
