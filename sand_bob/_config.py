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
