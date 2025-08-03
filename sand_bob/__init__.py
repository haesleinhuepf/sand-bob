"""
Sand-Bob - A Python library for executing code in Docker containers.
"""
from ._executor import ExecutionResult, execute

from ._config import config

__version__ = "0.1.0"
__all__ = ["ExecutionResult", "execute", "config"] 

WHITELIST_DEPENDENCIES = ["pandas", "matplotlib", "seaborn", "scipy", "numpy", 
                          "scikit-learn", "scikit-image", "pyclesperanto", 
                          "pyclesperanto_prototype", "cellpose", "tqdm",
                          "statsmodels", "bioio", "apoc"]

