from ._executor import ExecutionResult, execute
from ._code_gen import generate_code

# Conditionally import IPython magic functions only if IPython is available
try:
    from ._alice import alice, initialize
except (ImportError, NameError):
    # IPython not available or not in IPython context
    alice = None
    initialize = None

from ._config import config, config_openai, config_kisski, config_ollama, config_scadsai_llm, config_kiara, config_llms, config_strix, config_blablador

__version__ = "0.3.0"
__all__ = ["ExecutionResult", "execute", "config", "generate_code", "config_openai", "config_kisski", "config_ollama", "config_scadsai_llm", "config_kiara", "config_llms", "config_strix", "config_blablador"] 

WHITELIST_DEPENDENCIES = ["pandas", "matplotlib", "seaborn", "scipy", "numpy", 
                          "scikit-learn", "scikit-image", "tqdm",
                          "statsmodels", "stackview", "cupy"]

