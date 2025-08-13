"""
Core execution functionality for Sand-Bob.
"""

import time
import tempfile
import os
import json
from dataclasses import dataclass
from typing import List, Optional, Dict
import docker
from docker.errors import DockerException
import subprocess

@dataclass
class ExecutionResult:
    """Result of code execution in a Docker container."""
    stdout: str
    stderr: str
    exit_code: int
    execution_time: float
    container_id: Optional[str] = None
    code: Optional[str] = None
    dependencies: Optional[List[str]] = None
    traceback: Optional[str] = None
    files: Optional[Dict[str, str]] = None
    n_attempts: Optional[int] = None
    result_check_ok: Optional[bool] = None
    outputs: Optional[List[Dict]] = None
    feedback: Optional[str] = None
    final_result: Optional[str] = None

    def _repr_html_(self):
        from IPython.display import display
        import pandas as pd
        from io import BytesIO
        import base64

        parsed_output = ""
        if self.outputs is not None:
            for output in self.outputs:
                if output["type"] == "image/png":
                    parsed_output += f"<p><img src='data:image/png;base64,{output['data']}'/></p>"
                elif output["type"] == "text/plain":
                    parsed_output += f"<pre>{output['data']}</pre>"
                else:
                    parsed_output += f"<pre>{output['data']}</pre>"

        #print(parsed_output)

        additional_html = ""
        if self.files is not None and len(self.files) > 0:
            additional_html += "<li>Files:<ul>"
            for file, content in self.files.items():
                additional_html += f"<li>{file}</li>"
            additional_html += "</ul></li>"
        if self.n_attempts is not None:
            additional_html += f"<li>Number of attempts:\n{self.n_attempts}</li>"
        if self.result_check_ok is not None:
            additional_html += f"<li>Result check ok:\n{self.result_check_ok}</li>"
        if self.traceback is not None:
            additional_html += "<li>Traceback:\n<pre>{self.traceback}</pre></li>"

        return f"""
        <div>
            {parsed_output}
            <details><summary>Details</summary>
            <ul>
            <li><details><summary>StdOut ({len(self.stdout)})</summary><pre>{self.stdout}</pre></details></li>
            <li><details><summary>StdErr ({len(self.stderr)})</summary><pre>{self.stderr}</pre></details></li>
            <li>Dependencies:\n{", ".join(self.dependencies)}</li>
            <li>Exit Code:\n{self.exit_code}</li>
            {additional_html}
            <li>Execution Time:\n{self.execution_time}</li>
            <li><details><summary>Code</summary><pre>{self.code}<pre></details></li>
            </ul>
            </details>
        </div>
        """


def execute(code: str, dependencies: List[str] = [], 
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
    from ._utilities import python_code_to_notebook
    notebook_json = python_code_to_notebook(code)

    return execute_notebook(notebook_json, 
                     dependencies=dependencies, 
                     input_host_path=input_host_path, 
                     input_container_path=input_container_path, 
                     output_host_path=output_host_path, 
                     output_container_path=output_container_path,
                     python_version=python_version,
                     base_image=base_image,
                     timeout=timeout,
                     memory_limit=memory_limit)


def execute_notebook(notebook_json: str, dependencies: List[str] = [], 
                    input_host_path: Optional[str] = None, 
                    input_container_path: str = "/input_data",
                    output_host_path: Optional[str] = None, 
                    output_container_path: str = "/output_data",
                    python_version="3.11", 
                    base_image: Optional[str] = None, 
                    timeout: int = 30, 
                    memory_limit: str = "512m") -> ExecutionResult:
    """
    Execute a Jupyter notebook in a Docker container using nbconvert.

    Args:
        notebook_json: The notebook JSON string to execute.
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
    return _executor.execute_notebook(notebook_json, dependencies, input_host_path, input_container_path, output_host_path, output_container_path)


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
        
    
    def execute_notebook(
        self, 
        notebook_json: str, 
        dependencies: List[str], 
        input_host_path: Optional[str] = None, 
        input_container_path: str = "/input_data",
        output_host_path: Optional[str] = None, 
        output_container_path: str = "/output_data"
    ) -> ExecutionResult:
        """
        Execute a Jupyter notebook in a Docker container using nbconvert.
        
        Args:
            notebook_json: Jupyter notebook JSON string to execute
            dependencies: List of Python package dependencies
            input_host_path: Optional path to the directory on the host to mount as read-only input
            input_container_path: Path inside the container where the input volume will be mounted
            output_host_path: Optional path to the directory on the host to mount as read-write output
            output_container_path: Path inside the container where the output volume will be mounted
            
        Returns:
            ExecutionResult with stdout, stderr, exit_code, and execution_time
        """
        from ._utilities import load_base64_image
        import json
        start_time = time.time()
        
        # Validate input host path if provided
        if input_host_path is not None:
            input_host_path = os.path.abspath(input_host_path)
            if not os.path.exists(input_host_path):
                raise ValueError(f"Input host path does not exist: {input_host_path}")
            
            if not os.path.isdir(input_host_path):
                raise ValueError(f"Input host path is not a directory: {input_host_path}")
        
        # Validate output host path if provided
        if output_host_path is not None:
            output_host_path = os.path.abspath(output_host_path)
            if not os.path.exists(output_host_path):
                raise ValueError(f"Output host path does not exist: {output_host_path}")
            
            if not os.path.isdir(output_host_path):
                raise ValueError(f"Output host path is not a directory: {output_host_path}")
        
        # Create temporary directory for the notebook
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create display output directory
            display_output_host_path = os.path.join(temp_dir, "display_output")
            display_output_container_path = "/display_output"
            os.makedirs(display_output_host_path, exist_ok=True)

            try:
                # Write notebook JSON to a file
                notebook_file = os.path.join(temp_dir, "notebook.ipynb")
                with open(notebook_file, "w", encoding="utf-8") as f:
                    f.write(notebook_json)
                
                # Create requirements.txt if dependencies exist
                requirements_file = None
                if dependencies:
                    requirements_file = os.path.join(temp_dir, "requirements.txt")
                    with open(requirements_file, "w") as f:
                        for dep in dependencies:
                            f.write(f"{dep}\n")
                
                # Create Dockerfile for notebook execution
                dockerfile_content = self._create_notebook_dockerfile(requirements_file is not None, display_output_container_path)
                dockerfile_path = os.path.join(temp_dir, "Dockerfile")
                with open(dockerfile_path, "w") as f:
                    f.write(dockerfile_content)
                
                # Build and run container
                container = self._build_and_run_container(
                    temp_dir, notebook_file, input_host_path, input_container_path, 
                    output_host_path, output_container_path,
                    display_output_host_path, display_output_container_path
                )
                
                self.containers.append(container.id)
                
                # Get execution results
                result = self._get_execution_result(container, start_time)
                                    
            except Exception as e:
                import traceback
                # Return error result
                result = ExecutionResult(
                    stdout="",
                    stderr=str(e),
                    exit_code=1,
                    execution_time=time.time() - start_time,
                    traceback=traceback.format_exc()
                )
        
            result.code = notebook_json
            result.dependencies = dependencies

            # add files in output directory to result
            result.files = {}
            for file in os.listdir(display_output_host_path):
                #print("file", file)
                result.files[str(os.path.join(display_output_container_path, file)).replace("\\", "/")] = open(os.path.join(display_output_host_path, file), "rb").read()
        
        from io import BytesIO

        result.objects = {}
        for filename, content in result.files.items():
            if filename.endswith(".png") or filename.endswith(".jpg") or filename.endswith(".jpeg") or filename.endswith(".gif"):
                from skimage.io import imread
                result.objects[filename] = imread(BytesIO(bytes(content)))
            elif file.endswith(".csv"):
                import pandas as pd
                result.objects[file] = pd.read_csv(BytesIO(bytes(content)))
            elif file.endswith(".json") or filename.endswith(".ipynb"):
                import json
                result.objects[file] = json.load(BytesIO(bytes(content)))
            elif file.endswith(".txt") or filename.endswith(".svg"):
                result.objects[file] = content.decode("utf-8")
            else:
                result.objects[file] = content

        result.outputs = []
        if "notebook_executed.ipynb" in result.objects:
            # Try to copy the executed notebook from the container
            notebook_json = None

            # Get the executed notebook from the container
            notebook_json = result.objects["notebook_executed.ipynb"]

            json.dump(notebook_json, open("test.ipynb", "w"))

            #print("notebook_json", notebook_json)

            if notebook_json is not None:
                outputs = []
                for c in notebook_json["cells"]:
                    if "outputs" in c:
                        for o in c["outputs"]:
                            if "data" in o:
                                if "image/png" in o["data"]:
                                    base64_image = o["data"]["image/png"]
                                    pil_image, np_image = load_base64_image(base64_image)
                                    outputs.append({
                                        "type": "image/png",
                                        "data": base64_image,
                                        "np_image": np_image,
                                        "pil_image": pil_image
                                    })
                                elif 'text/plain' in o["data"]:
                                    text = o["data"]["text/plain"]
                                    if isinstance(text, list):
                                        text = "".join(text)
                                    outputs.append({
                                        "type": "text/plain",
                                        "data": text.strip("\n")
                                    })
                                else:
                                    print("unknown output type", o["data"].keys())
                                    # Handle other output types
                                    output_types = list(o["data"].keys())
                                    outputs.append({
                                        "type": "unknown",
                                        "data": o["data"],
                                        "output_types": output_types
                                    })
                            elif "text" in o:
                                text = o["text"]
                                if isinstance(text, list):
                                    text = "".join(text)

                                outputs.append({
                                    "type": "text/plain",
                                    "data": text.strip("\n")
                                })
                            else:
                                print("unknown output", o.keys())
                                # Handle outputs without data (like execution count, etc.)
                                outputs.append({
                                    "type": "metadata",
                                    "data": o
                                })
                
                # Store the outputs in the result
                result.outputs = outputs
                result.final_result = str(outputs[-1]["data"]).split("\n")[-1]

        
        return result

    
    def _create_notebook_dockerfile(self, has_dependencies: bool, output_container_path: str) -> str:
        """Create a Dockerfile for notebook execution using nbconvert."""


        dockerfile = f"""
FROM {self.base_image}

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    && rm -rf /var/lib/apt/lists/*

# Install jupyter and nbconvert
RUN pip install --no-cache-dir jupyter nbconvert

# Copy requirements and install Python dependencies
"""
        
        if has_dependencies:
            dockerfile += """
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
"""
        
        dockerfile += f"""
# Copy the notebook file
COPY notebook.ipynb .

# Execute the notebook using nbconvert and save to file
CMD ["jupyter", "nbconvert", "--to", "notebook", "--execute", "notebook.ipynb", "--output", "{output_container_path}/notebook_executed.ipynb"]
"""
        return dockerfile
    
    def _build_and_run_container(
        self, 
        temp_dir: str, 
        code_file: str, 
        input_host_path: Optional[str] = None, 
        input_container_path: str = "/input_data",
        output_host_path: Optional[str] = None, 
        output_container_path: str = "/output_data",
        display_output_host_path: Optional[str] = None,
        display_output_container_path: str = "/display_output"
    ) -> docker.models.containers.Container:
        """Build and run the Docker container."""
        # Build the image
        image, _ = self.client.images.build(
            path=temp_dir,
            tag=f"sand-bob-{int(time.time())}",
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
        
        # Initialize volumes dictionary
        volumes = {}
        
        # Add input volume mount if provided (read-only)
        if input_host_path is not None:
            volumes[input_host_path] = {
                'bind': "/app" + input_container_path,
                'mode': 'ro'
            }
            
        # Add output volume mount if provided (read-write)
        if output_host_path is not None:
            volumes[output_host_path] = {
                'bind': "/app" + output_container_path,
                'mode': 'rw'
            }

        if display_output_host_path is not None:
            volumes[display_output_host_path] = {
                'bind': display_output_container_path,
                'mode': 'rw'
            }
            
        # Add volumes to run parameters if any volumes are specified
        if volumes:
            run_params['volumes'] = volumes
        
        # Run the container
        container = self.client.containers.run(**run_params)
        
        return container
    
    def _get_execution_result(self, container, start_time: float) -> ExecutionResult:
        """Get the execution result from the container."""
        from ._utilities import strip_ansi
        try:
            # Wait for container to finish
            container.wait(timeout=self.timeout)
            
            # Get logs
            logs = container.logs().decode('utf-8')
            logs = strip_ansi(logs)
            
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