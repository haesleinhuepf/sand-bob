"""
Sand-Bob - A Python library for executing code in Docker containers.
"""
from ._executor import ExecutionResult, execute, execute_notebook
from ._bob import bob, initialize

from ._config import config

__version__ = "0.1.0"
__all__ = ["ExecutionResult", "execute", "execute_notebook", "config"] 

WHITELIST_DEPENDENCIES = ["pandas", "matplotlib", "seaborn", "scipy", "numpy", 
                          "scikit-learn", "scikit-image", "tqdm",
                          "statsmodels", "bioio", "apoc", "stackview"]
#"pyclesperanto", "pyclesperanto_prototype", "cellpose",
