"""
Sand-Bob - A Python library for executing AI-generated code in Docker containers with automated issue detection and fixing.
"""
from ._executor import ExecutionResult, execute, execute_notebook
from ._code_gen import generate_code

# Conditionally import IPython magic functions only if IPython is available
try:
    from ._bob import alice, initialize
except (ImportError, NameError):
    # IPython not available or not in IPython context
    alice = None
    initialize = None

from ._config import config, config_openai, config_kisski, config_ollama, config_scadsai_llm, config_kiara

__version__ = "0.1.0"
__all__ = ["ExecutionResult", "execute", "config", "generate_code", "config_openai", "config_kisski", "config_ollama", "config_scadsai_llm"] 

WHITELIST_DEPENDENCIES = ["pandas", "matplotlib", "seaborn", "scipy", "numpy", 
                          "scikit-learn", "scikit-image", "tqdm",
                          "statsmodels", "stackview"]
#"pyclesperanto", "pyclesperanto_prototype", "cellpose","bioio", "apoc", 

