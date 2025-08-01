"""
DockerMania - A Python library for executing code in Docker containers.
"""
from ._executor import ExecutionResult, CodeExecutor
from typing import List, Optional

__version__ = "0.1.0"
__all__ = ["CodeExecutor", "ExecutionResult", "execute"] 

def execute(code: str, dependencies: List[str], 
            input_host_path: Optional[str] = None, 
            input_container_path: str = "/input_data",
            output_host_path: Optional[str] = None, 
            output_container_path: str = "/output_data",
            python_version="3.11", 
            base_image: Optional[str] = None, 
            timeout: int = 30, 
            memory_limit: str = "512m") -> ExecutionResult:
    """
    Execute code in a Docker container.

    Args:
        code: The code to execute.
        dependencies: The dependencies to install.
        input_host_path: Optional path to the directory on the host to mount as read-only input.
        input_container_path: Path inside the container where the input volume will be mounted.
        output_host_path: Optional path to the directory on the host to mount as read-write output.
        output_container_path: Path inside the container where the output volume will be mounted.
        python_version: The Python version to use (optional).
        base_image: The base image to use (optional).
        timeout: The timeout for the execution (optional).
        memory_limit: The memory limit for the container (optional).

    Returns:
        The result of the execution.
    """
    from ._executor import CodeExecutor
    _executor = CodeExecutor(python_version=python_version, base_image=base_image, timeout=timeout, memory_limit=memory_limit)
    return _executor.execute(code, dependencies, input_host_path, input_container_path, output_host_path, output_container_path)

