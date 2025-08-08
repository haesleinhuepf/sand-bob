from ._endpoints import prompt_scadsai_llm, prompt_openai, prompt_ollama

class Config:
    def __init__(self):
        self.prompt_function_determine_dependencies = prompt_scadsai_llm
        self.prompt_function_generate_code = prompt_scadsai_llm
        self.prompt_function_fix_code = prompt_scadsai_llm
        self.prompt_function_generate_code_feedback = prompt_scadsai_llm
        self.prompt_function_notebook_conversion = prompt_scadsai_llm
    
config = Config()
