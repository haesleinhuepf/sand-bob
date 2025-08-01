"""
DockerMania - A Python library for executing code in Docker containers.
"""
from ._executor import ExecutionResult, CodeExecutor
from typing import List, Optional

__version__ = "0.1.0"
__all__ = ["CodeExecutor", "ExecutionResult", "execute"] 

def execute(code: str, dependencies: List[str], 
            host_path: Optional[str] = None, 
            container_path: str = "/mounted_data", 
            python_version="3.11", 
            base_image: Optional[str] = None, 
            timeout: int = 30, 
            memory_limit: str = "512m") -> ExecutionResult:
    """
    Execute code in a Docker container.

    Args:
        code: The code to execute.
        dependencies: The dependencies to install.
        host_path: The path to the directory on the host to mount (optional).
        container_path: The path inside the container where the volume will be mounted (optional).
        python_version: The Python version to use (optional).
        base_image: The base image to use (optional).
        timeout: The timeout for the execution (optional).
        memory_limit: The memory limit for the container (optional).

    Returns:
        The result of the execution.
    """
    from ._executor import CodeExecutor
    _executor = CodeExecutor(python_version=python_version, base_image=base_image, timeout=timeout, memory_limit=memory_limit)
    return _executor.execute(code, dependencies, host_path, container_path)

