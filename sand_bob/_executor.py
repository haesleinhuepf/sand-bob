import time
import tempfile
import os
import json
from dataclasses import dataclass
from typing import List, Optional, Dict
from unittest import result
import docker
from docker.errors import DockerException, BuildError
import subprocess

import ipywidgets as widgets
from IPython.display import display, HTML
from typing import List, Optional, Dict, Any


from ._results import ExecutionResult

def execute(code: str, dependencies: List[str] = [], 
            input_host_path: Optional[str] = None, 
            input_container_path: str = "/input_data",
            output_host_path: Optional[str] = None, 
            output_container_path: str = "/output_data",
            python_version="3.11", 
            base_image: Optional[str] = None, 
            timeout: int = 30, 
            memory_limit: str = "512m",
            gpu_support: bool = False,
            executor: Optional["CodeExecutor"] = None) -> ExecutionResult:
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
        gpu_support: Whether to enable GPU support with NVIDIA drivers and pyclesperanto (optional).
        executor: Optional CodeExecutor instance to reuse (optional).

    Returns:
        The result of the execution.
    """
    from ._utilities import python_code_to_mystnb
    notebook_mystnb = python_code_to_mystnb(code)

    return execute_notebook(
                     notebook_mystnb=notebook_mystnb, 
                     dependencies=dependencies, 
                     input_host_path=input_host_path, 
                     input_container_path=input_container_path, 
                     output_host_path=output_host_path, 
                     output_container_path=output_container_path,
                     python_version=python_version,
                     base_image=base_image,
                     timeout=timeout,
                     memory_limit=memory_limit,
                     gpu_support=gpu_support,
                     executor=executor)


def execute_notebook(notebook_json: Optional[str] = None, 
                     notebook_mystnb: Optional[str] = None,
                    dependencies: List[str] = [], 
                    input_host_path: Optional[str] = None, 
                    input_container_path: str = "/input_data",
                    output_host_path: Optional[str] = None, 
                    output_container_path: str = "/output_data",
                    python_version="3.11", 
                    base_image: Optional[str] = None, 
                    timeout: int = 30, 
                    memory_limit: str = "512m",
                    gpu_support: bool = False,
                    executor: Optional["CodeExecutor"] = None) -> ExecutionResult:
    """
    Execute a Jupyter notebook in a Docker container using nbconvert.

    Args:
        notebook_json: The notebook JSON string to execute.
        notebook_mystnb: The notebook in mystnb format to execute (alternative to notebook_json).
        dependencies: The dependencies to install.
        input_host_path: Optional path to the directory on the host to mount as read-only input.
        input_container_path: Path inside the container where the input volume will be mounted.
        output_host_path: Optional path to the directory on the host to mount as read-write output.
        output_container_path: Path inside the container where the output volume will be mounted.
        python_version: The Python version to use (optional).
        base_image: The base image to use (optional).
        timeout: The timeout for the execution (optional).
        memory_limit: The memory limit for the container (optional).
        gpu_support: Whether to enable GPU support with NVIDIA drivers and pyclesperanto (optional).
        executor: Optional CodeExecutor instance to reuse (optional).

    Returns:
        The result of the execution.
    """
    from ._executor import CodeExecutor
    if executor is None:
        _executor = CodeExecutor(python_version=python_version, base_image=base_image, timeout=timeout, memory_limit=memory_limit, gpu_support=gpu_support)
    else:
        _executor = executor
    if notebook_json is None and notebook_mystnb is not None:
        res = _executor.execute_notebook(notebook_mystnb, notebook_filename="notebook.mystnb", dependencies=dependencies, input_host_path=input_host_path, input_container_path=input_container_path, output_host_path=output_host_path, output_container_path=output_container_path)
    else:
        res = _executor.execute_notebook(notebook_json, dependencies=dependencies, input_host_path=input_host_path, input_container_path=input_container_path, output_host_path=output_host_path, output_container_path=output_container_path)
    
    # store name of error for later display
    if "Traceback" in res.stdout:
        import re
        match = re.search(r"^([A-Za-z_][A-Za-z0-9_]*(?:Error|Exception)):", res.stdout, re.MULTILINE)
        res.error = match.group(1) if match else None
        res.traceback = res.stdout

    return res

class Cache:
    image_cache = {}

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
        memory_limit: str = "512m",
        gpu_support: bool = False
    ):
        """
        Initialize the code executor.
        
        Args:
            python_version: Python version to use
            base_image: Custom base Docker image
            timeout: Execution timeout in seconds
            memory_limit: Memory limit for containers
            gpu_support: Whether to enable GPU support with NVIDIA drivers
        """
        self.python_version = python_version
        self.gpu_support = gpu_support
        
        if base_image:
            self.base_image = base_image
        elif gpu_support:
            # Use NVIDIA CUDA runtime image with GPU support
            self.base_image = "nvidia/cuda:12.4.0-runtime-ubuntu22.04"
        else:
            self.base_image = f"python:{python_version}-slim"
        
        self.timeout = timeout
        self.memory_limit = memory_limit
        try:
            self.client = docker.from_env()
        except DockerException as e:
            if "Error while fetching server API version" in str(e):
                raise Exception("Docker daemon is not running. Please start the Docker daemon!") from e
            else:
                raise
        except Exception as e:
            raise Exception(f"Error initializing Docker client: {e}") from e

        self.containers = []
        self.build_log_output = []  # Store build logs for the current execution
        
    
    def execute_notebook(
        self, 
        notebook_content: str,
        notebook_filename:str = "notebook.ipynb",
        dependencies: List[str] = [], 
        input_host_path: Optional[str] = None, 
        input_container_path: str = "/input_data",
        output_host_path: Optional[str] = None, 
        output_container_path: str = "/output_data"
    ) -> ExecutionResult:
        """
        Execute a Jupyter notebook in a Docker container using nbconvert.
        
        Args:
            notebook_content: Jupyter notebook JSON or mystnb string to execute
            notebook_filename: The filename to use for the notebook inside the container ending with .md, .mystnb, or .ipynb
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

            if "pip install" not in notebook_content and "pip3 install" not in notebook_content:
                try:
                    # Write notebook JSON to a file
                    notebook_file = os.path.join(temp_dir, notebook_filename)
                    with open(notebook_file, "w", encoding="utf-8") as f:
                        f.write(notebook_content)
                    
                    # Create requirements.txt if dependencies exist
                    requirements_file = None
                    if dependencies:
                        requirements_file = os.path.join(temp_dir, "requirements.txt")
                        with open(requirements_file, "w") as f:
                            for dep in dependencies:
                                # Replace generic cupy with CUDA-compatible version for GPU support
                                if self.gpu_support and dep.strip().lower() == "cupy":
                                    # Use cupy-cuda12x for CUDA 12.x compatibility
                                    f.write("cupy-cuda12x\n")
                                else:
                                    f.write(f"{dep}\n")
                        #print(f"Created requirements.txt with {dependencies}")
                    
                    # Create Dockerfile for notebook execution
                    dockerfile_content = self._create_notebook_dockerfile(
                        has_dependencies=requirements_file is not None
                    )
                    dockerfile_path = os.path.join(temp_dir, "Dockerfile")
                    with open(dockerfile_path, "w") as f:
                        f.write(dockerfile_content)
                    
                    # Build and run container
                    container = self._build_and_run_container(
                        temp_dir, notebook_file, input_host_path, input_container_path, 
                        output_host_path, output_container_path,
                        display_output_host_path, display_output_container_path,
                        dependencies
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
            else:
                import traceback
                # Return error result
                result = ExecutionResult(
                    stdout="pip install is prohibited in this environment.",
                    stderr="pip install is prohibited in this environment.",
                    exit_code=1,
                    execution_time=time.time() - start_time,
                    traceback=""
                )
        
            result.code = notebook_content
            
            result.dependencies = dependencies

            # add files in output directory to result
            result.files = {}
            try:
                for file in os.listdir(display_output_host_path):
                    #print("file", file)
                    result.files[str(os.path.join(display_output_container_path, file)).replace("\\", "/")] = open(os.path.join(display_output_host_path, file), "rb").read()
            except Exception as e:
                print(f"Error reading files in display output directory: {e}")
                result.files = {}
        
        from io import BytesIO
        import warnings

        result.objects = {}
        result.final_result = None
        
        for filename, content in result.files.items():
            if filename.endswith(".png") or filename.endswith(".jpg") or filename.endswith(".jpeg") or filename.endswith(".gif"):
                from skimage.io import imread
                result.objects[filename] = imread(BytesIO(bytes(content)))
            elif filename.endswith(".csv"):
                import pandas as pd
                try:
                    result.objects[filename] = pd.read_csv(BytesIO(bytes(content)))
                except Exception as e:
                    # warnings.warn(f"Error reading CSV file {filename}: {e} \n\n {str(content)}")
                    result.objects[filename] = content
            elif filename.endswith(".json") or filename.endswith(".ipynb"):
                import json
                try:
                    result.objects[filename] = json.load(BytesIO(bytes(content)))
                except Exception as e:
                    # warnings.warn(f"Error reading JSON file {filename}: {e} \n\n {str(content)}")
                    result.objects[filename] = content
            elif filename.endswith(".jsonl"):
                import json
                result.objects[filename] = [json.loads(line) for line in content.decode("utf-8").splitlines()]
            elif filename.endswith(".txt") or filename.endswith(".svg"):
                try:
                    result.objects[filename] = content.decode("utf-8")
                except Exception as e:
                    # warnings.warn(f"Error reading text file {filename}: {e} \n\n {str(content)}")
                    result.objects[filename] = content
            else:
                result.objects[filename] = content

            if "display_output/final_result" in filename:
                result.final_result = result.objects[filename]

        notebook_json = None

        result.outputs = []
        if "/display_output/notebook_executed.ipynb" in result.objects:
            notebook_json = result.objects["/display_output/notebook_executed.ipynb"]
        elif "notebook_executed.ipynb" in result.objects:
            notebook_json = result.objects["notebook_executed.ipynb"]

            #json.dump(notebook_json, open("test.ipynb", "w"))

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

            if result.final_result is None and len(outputs) > 0:
                result.final_result = str(outputs[-1]["data"]).strip("\n").split("\n")[-1]
                try:
                    result.final_result = int(result.final_result)
                except ValueError:
                    try:
                        result.final_result = float(result.final_result)
                    except ValueError:
                        pass

        if isinstance(result.final_result, str) and result.final_result in result.objects:
            key = result.final_result
            if key.endswith(".svg") and key[:-4] + ".png" in result.objects:
                key = key[:-4] + ".png"
            result.final_result = result.objects[key]
        
        return result

    
    def _create_notebook_dockerfile(self, has_dependencies: bool) -> str:
        """Create a Dockerfile for notebook execution using nbconvert."""

        if self.gpu_support:
            # GPU-enabled Dockerfile with Python and pyclesperanto
            dockerfile = f"""
FROM {self.base_image}

WORKDIR /app

# Install Python, OpenCL, and system dependencies for GPU support
RUN apt-get update && apt-get install -y \\
    python3 \\
    python3-pip \\
    python3-dev \\
    gcc \\
    g++ \\
    ocl-icd-libopencl1 \\
    ocl-icd-opencl-dev \\
    opencl-headers \\
    clinfo \\
    && rm -rf /var/lib/apt/lists/*

# Create NVIDIA ICD file for OpenCL (runtime image should have the library)
RUN mkdir -p /etc/OpenCL/vendors && \\
    echo "libnvidia-opencl.so.1" > /etc/OpenCL/vendors/nvidia.icd

# Set library path to include NVIDIA libraries
ENV LD_LIBRARY_PATH=/usr/local/nvidia/lib:/usr/local/nvidia/lib64

# Create symbolic links for python and pip (force overwrite if they exist)
RUN ln -sf /usr/bin/python3 /usr/bin/python && \\
    ln -sf /usr/bin/pip3 /usr/bin/pip

# Upgrade pip
RUN python3 -m pip install --upgrade pip

# Install jupyter and nbconvert
RUN python3 -m pip install --no-cache-dir jupyter nbconvert jupytext 

# Copy requirements and install Python dependencies
"""
        else:
            # Standard Dockerfile
            dockerfile = f"""
FROM {self.base_image}

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    && rm -rf /var/lib/apt/lists/*

# Install jupyter and nbconvert
RUN pip install --no-cache-dir jupyter nbconvert jupytext

# Copy requirements and install Python dependencies
"""
        
        if has_dependencies:
            dockerfile += """
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
"""
        
        # Notebook file handling and execution are done at runtime via run_params
        # to avoid putting execution steps in the image build process.
        
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
        display_output_container_path: str = "/display_output",
        dependencies: Optional[List[str]] = None
    ) -> docker.models.containers.Container:
        """Build and run the Docker container."""
        # Create a cache key based on dependencies and base image
        # Use a stable tag name for the same dependencies to leverage Docker layer caching
        import hashlib
        import threading
        thread_id = threading.get_ident()

        cache_key_parts = [str(thread_id), self.base_image]
        if dependencies:
            cache_key_parts.extend(sorted(dependencies))
        cache_key = hashlib.md5("_".join(cache_key_parts).encode()).hexdigest()
        tag_name = f"sand-bob-{cache_key}"
        
        # Build the image - Docker will use layer cache for unchanged layers
        # (base image, system packages, Python dependencies) even if notebook changed
        start_time = time.time()
        
        # Process build logs to capture output (especially errors from pip install)
        self.build_log_output = []
        
        if cache_key in Cache.image_cache:
            image = Cache.image_cache[cache_key]
            build_logs = [f"Using cached image for key {cache_key} with tag {tag_name}"]
        else:
            try:
                # Build without decode to get raw stream, we'll decode manually
                image, build_logs = self.client.images.build(
                    path=temp_dir,
                    tag=tag_name,
                    rm=True
                )
                
                # Process and log build output
                # build_logs is a generator that yields log lines
                for log_line in build_logs:
                    # Decode if bytes
                    if isinstance(log_line, bytes):
                        log_line = log_line.decode('utf-8')
                    
                    # Try to parse as JSON to extract stream/error messages
                    try:
                        import json
                        log_dict = json.loads(log_line)
                        
                        if 'stream' in log_dict:
                            msg = log_dict['stream'].rstrip()
                            if msg:  # Only log non-empty lines
                                self.build_log_output.append(msg)
                        elif 'error' in log_dict:
                            error_msg = log_dict['error']
                            self.build_log_output.append(f"BUILD ERROR: {error_msg}")
                    except (json.JSONDecodeError, TypeError):
                        # If not JSON, just store the raw line
                        log_str = str(log_line).rstrip()
                        if log_str:
                            self.build_log_output.append(log_str)
                        
            except docker.errors.BuildError as e:
                # Capture build logs from the exception
                self.build_log_output.append("Docker build failed with error:")
                if hasattr(e, 'build_log') and e.build_log:
                    for log_entry in e.build_log:
                        if isinstance(log_entry, dict):
                            if 'stream' in log_entry:
                                log_line = log_entry['stream'].rstrip()
                                if log_line:
                                    self.build_log_output.append(log_line)
                            elif 'error' in log_entry:
                                error_msg = log_entry['error']
                                self.build_log_output.append(f"BUILD ERROR: {error_msg}")
                        elif isinstance(log_entry, bytes):
                            try:
                                import json
                                log_dict = json.loads(log_entry.decode('utf-8'))
                                if 'stream' in log_dict:
                                    msg = log_dict['stream'].rstrip()
                                    if msg:
                                        self.build_log_output.append(msg)
                                elif 'error' in log_dict:
                                    error_msg = log_dict['error']
                                    self.build_log_output.append(f"BUILD ERROR: {error_msg}")
                            except (json.JSONDecodeError, TypeError):
                                msg = log_entry.decode('utf-8', errors='replace')
                                self.build_log_output.append(msg)
                        else:
                            self.build_log_output.append(str(log_entry))
                else:
                    self.build_log_output.append(str(e))
                
                # Re-raise with more context
                full_log = '\n'.join(self.build_log_output)
                raise Exception(f"Docker build failed. Build log:\n{full_log}") from e
            
            
            # Store in cache for tracking
            Cache.image_cache[cache_key] = image

        self.build_time = time.time() - start_time
        
        # Prepare container run parameters
        run_params = {
            'image': image.id,
            'detach': True,
            'mem_limit': self.memory_limit,
            'network_disabled': True,  # Disable network for security
            'remove': False
        }

        notebook_filename = os.path.basename(code_file)
        runtime_command = (
            f'cp "/app/temp/{notebook_filename}" "/app/{notebook_filename}"; '
            f'if [ "${{NOTEBOOK_FILE##*.}}" = "mystnb" ] || [ "${{NOTEBOOK_FILE##*.}}" = "md" ]; then '
            f'jupytext --to notebook "{notebook_filename}" -o notebook.ipynb; '
            f'elif [ "{notebook_filename}" != "notebook.ipynb" ]; then '
            f'cp "{notebook_filename}" notebook.ipynb; '
            f'fi; '
            f'jupyter nbconvert --to notebook --execute notebook.ipynb --output "{display_output_container_path}/notebook_executed.ipynb"'
        )
        run_params['environment'] = {'NOTEBOOK_FILE': notebook_filename}
        run_params['command'] = ["sh", "-lc", runtime_command]
        
        # Add GPU support if enabled
        if self.gpu_support:
            run_params['device_requests'] = [
                docker.types.DeviceRequest(count=-1, capabilities=[['gpu']])
            ]
            # Add NVIDIA environment variables for GPU access
            gpu_environment = {
                'NVIDIA_VISIBLE_DEVICES': 'all',
                'NVIDIA_DRIVER_CAPABILITIES': 'compute,utility'
            }
            gpu_environment.update(run_params.get('environment', {}))
            run_params['environment'] = gpu_environment
        
        # Initialize volumes dictionary
        volumes = {}

        # mount notebook file as read-only
        volumes[temp_dir] = {
            'bind': "/app/temp",
            'mode': 'ro'
        }
        
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
        self.run_start_time = time.time()
        container = self.client.containers.run(**run_params)

        return container
    
    def _get_execution_result(self, container, start_time: float) -> ExecutionResult:
        """Get the execution result from the container."""
        from ._utilities import strip_ansi
        try:
            # Wait for container to finish
            container.wait(timeout=self.timeout)
            self.run_time = time.time() - self.run_start_time
            
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
            
            nb_exec_error_delimiter = "nbclient.exceptions.CellExecutionError: "
            if nb_exec_error_delimiter in stdout:
                stdout = stdout.split(nb_exec_error_delimiter)[-1]

            return ExecutionResult(
                stdout=stdout,
                stderr=stderr,
                exit_code=exit_code,
                execution_time=time.time() - start_time,
                run_time=self.run_time,
                build_time=self.build_time,
                container_id=container.id,
                build_log=self.build_log_output if self.build_log_output else None
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
                container_id=container.id if container else None,
                build_log=self.build_log_output if self.build_log_output else None
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

