"""
Core execution functionality for DockerMania.
"""

import time
import tempfile
import os
from dataclasses import dataclass
from typing import List, Optional
import docker
from docker.errors import DockerException, ContainerError
import subprocess

@dataclass
class ExecutionResult:
    """Result of code execution in a Docker container."""
    stdout: str
    stderr: str
    exit_code: int
    execution_time: float
    container_id: Optional[str] = None


class CodeExecutor:
    """
    Executes Python code in isolated Docker containers.
    
    This class manages the lifecycle of Docker containers for code execution,
    including dependency installation and cleanup.
    """
    
    def __init__(
        self,
        python_version: str = "3.11",
        base_image: Optional[str] = None,
        timeout: int = 30,
        memory_limit: str = "512m"
    ):
        """
        Initialize the code executor.
        
        Args:
            python_version: Python version to use
            base_image: Custom base Docker image
            timeout: Execution timeout in seconds
            memory_limit: Memory limit for containers
        """
        self.python_version = python_version
        self.base_image = base_image or f"python:{python_version}-slim"
        self.timeout = timeout
        self.memory_limit = memory_limit
        try:
            self.client = docker.from_env()
        except DockerException as e:
            if "Error while fetching server API version" in str(e):
                print("Docker daemon is not running. Starting Docker daemon...")
                subprocess.run(["dockerd"], check=True)
                self.client = docker.from_env()
            else:
                raise
        except Exception as e:
            print(f"Error initializing Docker client: {e}")
            self.client = None

        self.containers = []
        
    def execute(
        self, 
        code: str, 
        dependencies: List[str], 
        host_path: Optional[str] = None, 
        container_path: str = "/mounted_data"
    ) -> ExecutionResult:
        """
        Execute Python code in a Docker container.
        
        Args:
            code: Python code to execute
            dependencies: List of Python package dependencies
            host_path: Optional path to the directory on the host to mount
            container_path: Path inside the container where the volume will be mounted (only used if host_path is provided)
            
        Returns:
            ExecutionResult with stdout, stderr, exit_code, and execution_time
        """
        start_time = time.time()
        
        try:
            # Validate host path if provided
            if host_path is not None:
                host_path = os.path.abspath(host_path)
                if not os.path.exists(host_path):
                    raise ValueError(f"Host path does not exist: {host_path}")
                
                if not os.path.isdir(host_path):
                    raise ValueError(f"Host path is not a directory: {host_path}")
            
            # Create temporary directory for the code
            with tempfile.TemporaryDirectory() as temp_dir:
                # Write code to a file
                code_file = os.path.join(temp_dir, "code.py")
                with open(code_file, "w") as f:
                    f.write(code)
                
                # Create requirements.txt if dependencies exist
                requirements_file = None
                if dependencies:
                    requirements_file = os.path.join(temp_dir, "requirements.txt")
                    with open(requirements_file, "w") as f:
                        for dep in dependencies:
                            f.write(f"{dep}\n")
                
                # Create Dockerfile
                dockerfile_content = self._create_dockerfile(requirements_file is not None)
                dockerfile_path = os.path.join(temp_dir, "Dockerfile")
                with open(dockerfile_path, "w") as f:
                    f.write(dockerfile_content)
                
                # Build and run container
                container = self._build_and_run_container(
                    temp_dir, code_file, host_path, container_path
                )
                
                self.containers.append(container.id)
                
                # Get execution results
                result = self._get_execution_result(container, start_time)
                
                return result
                
        except Exception as e:
            # Return error result
            return ExecutionResult(
                stdout="",
                stderr=str(e),
                exit_code=1,
                execution_time=time.time() - start_time
            )
    
    def _create_dockerfile(self, has_dependencies: bool) -> str:
        """Create a Dockerfile for the execution environment."""
        dockerfile = f"""
FROM {self.base_image}

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
"""
        
        if has_dependencies:
            dockerfile += """
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
"""
        
        dockerfile += """
# Copy the code file
COPY code.py .

# Run the code
CMD ["python", "code.py"]
"""
        return dockerfile
    
    def _build_and_run_container(
        self, 
        temp_dir: str, 
        code_file: str, 
        host_path: Optional[str] = None, 
        container_path: str = "/mounted_data"
    ) -> docker.models.containers.Container:
        """Build and run the Docker container."""
        # Build the image
        image, _ = self.client.images.build(
            path=temp_dir,
            tag=f"dockermania-{int(time.time())}",
            rm=True
        )
        
        # Prepare container run parameters
        run_params = {
            'image': image.id,
            'detach': True,
            'mem_limit': self.memory_limit,
            'network_disabled': True,  # Disable network for security
            'remove': False
        }
        
        # Add volume mount if host_path is provided
        if host_path is not None:
            run_params['volumes'] = {
                host_path: {
                    'bind': container_path,
                    'mode': 'rw'
                }
            }
            print(f"bind: container: {container_path} host: {host_path}")
        
        # Run the container
        container = self.client.containers.run(**run_params)
        
        return container
    
    def _get_execution_result(self, container, start_time: float) -> ExecutionResult:
        """Get the execution result from the container."""
        try:
            # Wait for container to finish
            container.wait(timeout=self.timeout)
            
            # Get logs
            logs = container.logs().decode('utf-8')
            
            # Get container info
            container_info = container.attrs
            
            # Determine if there was an error
            exit_code = container_info['State']['ExitCode']
            
            # Split stdout and stderr (Docker combines them by default)
            # For simplicity, we'll treat all output as stdout
            # In a more sophisticated implementation, you might want to capture stderr separately
            stdout = logs
            stderr = ""
            
            if exit_code != 0:
                stderr = logs
                stdout = ""
            
            # Clean up the container after getting logs
            try:
                container.remove()
            except Exception as e:
                # Container might already be removed, ignore the error
                pass
            
            return ExecutionResult(
                stdout=stdout,
                stderr=stderr,
                exit_code=exit_code,
                execution_time=time.time() - start_time,
                container_id=container.id
            )
            
        except Exception as e:
            # Clean up the container in case of error
            try:
                if container:
                    container.remove()
            except Exception:
                # Container might already be removed, ignore the error
                pass
            
            return ExecutionResult(
                stdout="",
                stderr=str(e),
                exit_code=1,
                execution_time=time.time() - start_time,
                container_id=container.id if container else None
            )
    
    def cleanup(self):
        """Clean up all containers created by this executor."""
        for container_id in self.containers:
            try:
                container = self.client.containers.get(container_id)
                if container.status == 'running':
                    container.stop(timeout=5)
                container.remove()
            except docker.errors.NotFound:
                # Container already removed
                pass
            except Exception as e:
                print(f"Warning: Could not clean up container {container_id}: {e}")
        
        self.containers.clear()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.cleanup() 