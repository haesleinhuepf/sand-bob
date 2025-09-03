"""
Sand-Bob - A Python library for executing AI-generated code in Docker containers with automated issue detection and fixing.
"""
from ._executor import ExecutionResult, execute, execute_notebook
from ._code_gen import generate_code
from ._bob import bob, initialize

from ._config import config, config_openai, config_kisski

__version__ = "0.1.0"
__all__ = ["ExecutionResult", "execute", "config", "generate_code", "config_openai", "config_kisski"] 

WHITELIST_DEPENDENCIES = ["pandas", "matplotlib", "seaborn", "scipy", "numpy", 
                          "scikit-learn", "scikit-image", "tqdm",
                          "statsmodels", "stackview"]
#"pyclesperanto", "pyclesperanto_prototype", "cellpose","bioio", "apoc", 

