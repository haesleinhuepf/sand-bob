from ._endpoints import prompt_scadsai_llm, prompt_openai, prompt_ollama

class Config:
    def __init__(self):
        self.prompt_function_determine_dependencies = prompt_scadsai_llm
        self.prompt_function_generate_code = prompt_scadsai_llm
        self.prompt_function_fix_code = prompt_scadsai_llm
        self.prompt_function_generate_code_feedback = prompt_openai
        self.prompt_function_notebook_conversion = prompt_scadsai_llm
    
config = Config()

def config_openai(model: str="gpt-5-mini"):
    from ._config import config
    from functools import partial
    from ._endpoints import prompt_openai
    
    config.prompt_function_determine_dependencies = partial(prompt_openai, model=model)
    config.prompt_function_generate_code = partial(prompt_openai, model=model)
    config.prompt_function_fix_code = partial(prompt_openai, model=model)
    config.prompt_function_generate_code_feedback = partial(prompt_openai, model=model)
    config.prompt_function_notebook_conversion = partial(prompt_openai, model=model)

