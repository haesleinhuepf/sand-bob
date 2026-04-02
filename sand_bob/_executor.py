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
from docker.errors import DockerException, BuildError
import subprocess

import ipywidgets as widgets
from IPython.display import display, HTML
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import base64
from io import BytesIO

@dataclass
class ExecutionResult:
    """Result of code execution in a Docker container."""
    stdout: str
    stderr: str
    exit_code: int
    execution_time: float
    run_time: Optional[float] = None
    build_time: Optional[float] = None
    container_id: Optional[str] = None
    code: Optional[str] = None
    dependencies: Optional[List[str]] = None
    traceback: Optional[str] = None
    files: Optional[Dict[str, str]] = None
    n_codefix_attempts: Optional[int] = None
    outputs: Optional[List[Dict]] = None
    feedback: Optional[str] = None
    final_result: Optional[Any] = None
    total_time: Optional[float] = None
    former_result: Optional["ExecutionResult"] = None
    render_inline: bool = True
    build_log: Optional[List[str]] = None
    summary: Optional[str] = None

    def _repr_html_(self):
        from IPython.display import display, HTML
        import pandas as pd
        from io import BytesIO
        import base64

        self._create_widget()
        display(self.widget)

        if not self.render_inline:
            return ""


        return self._html_output()
    
    def _html_output(self):
        
        parsed_output = ""
        if self.outputs is not None:
            for output in self.outputs:
                if output["type"] == "image/png":
                    parsed_output += f"<p><img src='data:image/png;base64,{output['data']}'/></p>"
                elif output["type"] == "text/plain":
                    parsed_output += f"<pre>{output['data']}</pre>"
                else:
                    parsed_output += f"<pre>{output['data']}</pre>"

        return parsed_output

    #def __post_init__(self):
    #    """Initialize the widget interface after dataclass initialization."""
    #    self._create_widget()

    def _create_widget(self, include_chain_selector: bool = True):
        """Create the main widget interface with tabs.

        Args:
            include_chain_selector: When True, show a dropdown above the tabs
                to navigate the chain of `former_result` starting from the
                earliest result to the current one. When False, render only
                this result's tabs (used for nested rendering).
        """
        # Create output widgets
        self.details_output = widgets.Output()
        self.stdout_output = widgets.Output()
        self.stderr_output = widgets.Output()
        self.code_output = widgets.Output()
        self.output_display = widgets.Output()
        
        # Create save notebook output if notebook file exists
        self.save_notebook_output = None
        if self.files and '/display_output/notebook_executed.ipynb' in self.files:
            self.save_notebook_output = widgets.Output()
            # Populate save notebook content immediately
            self._populate_save_notebook()
        
        # Create tab children in the specified order: output, code, details, stdout, stderr, save notebook
        tab_children = [self.output_display, self.code_output, self.details_output, self.stdout_output, self.stderr_output]
        tab_titles = ["Output", "Code", "Details", "StdOut", "StdErr"]
        
        # Add save notebook tab if it exists
        if self.save_notebook_output:
            tab_children.append(self.save_notebook_output)
            tab_titles.append("Save Notebook")
        
        # Create the tab widget
        self.tab_widget = widgets.Tab()
        self.tab_widget.children = tab_children
        
        # Set tab titles
        for i, title in enumerate(tab_titles):
            self.tab_widget.set_title(i, title)
        
        # Add styling to the tab widget
        self.tab_widget.layout = widgets.Layout(
            width='100%',
            height='auto'
        )
        
        # Populate all tabs immediately for this result
        self._populate_output()
        self._populate_code()
        self._populate_details()
        self._populate_stdout()
        self._populate_stderr()

        # If requested, create a dropdown that lets the user switch between
        # this result and all of its former_result ancestors. The list starts
        # with the earliest result (no former_result) and ends with current.
        if include_chain_selector:
            # Build the chain from oldest to newest
            chain: List[ExecutionResult] = []
            cursor = self
            while cursor is not None:
                if cursor is cursor.former_result:
                    print(f"Cursor is same as former_result")
                    break
                if cursor in chain:
                    print(f"Cycle detected in chain")
                    break
                chain.append(cursor)    
                cursor = cursor.former_result
            chain = list(reversed(chain))

            if len(chain) > 1:
                # Prepare widgets for each result in the chain without their own selector
                chain_widgets = []
                for r in chain:
                    # Avoid re-creating if widget exists and is suitable
                    r._create_widget(include_chain_selector=False)
                    chain_widgets.append(r.widget if hasattr(r, 'widget') else self.tab_widget)

                # Labels: Result 1..N with simple descriptors
                def make_label(idx: int, r: "ExecutionResult") -> str:
                    label = f"Result {idx+1}"
                    try:
                        if hasattr(r, 'exit_code'):
                            label += f" (exit {r.exit_code})"
                    except Exception:
                        pass
                    return label

                options = [(make_label(i, r), i) for i, r in enumerate(chain)]
                dropdown = widgets.Dropdown(
                    options=options,
                    value=len(chain) - 1,
                    description='History:',
                    style={'description_width': '90px'},
                    layout=widgets.Layout(width='auto')
                )

                # Container to hold the currently selected result's tabs
                selected_container = widgets.Box()

                def update_selected(index: int):
                    selected_widget = chain_widgets[index]
                    selected_container.children = (selected_widget,)

                def on_change(change):
                    if change.get('name') == 'value' and change.get('type') == 'change':
                        update_selected(change['new'])

                dropdown.observe(on_change, names='value')
                update_selected(len(chain) - 1)

                # Compose final widget with dropdown on top
                self.widget = widgets.VBox([dropdown, selected_container])
                return

        # Default: no chain selector, expose only this tab widget
        self.widget = self.tab_widget




    def _populate_details(self):
        """Populate the details section."""
        with self.details_output:
            self.details_output.clear_output(wait=True)
            
            details_html = "<div><h4>Execution Details</h4><ul style='list-style: none; padding: 0;'>"
            
            # Basic info
            if self.final_result is not None:
                details_html += f"<li><strong>Final result:</strong> {self.final_result}</li>"
            if self.summary is not None:
                details_html += f"<li><strong>Summary:</strong> {self.summary}</li>"
                
            details_html += f"<li><strong>Exit Code:</strong> <span style='color: {'green' if self.exit_code == 0 else 'red'};'>{self.exit_code}</span></li>"
            if self.build_time is not None:
                details_html += f"<li><strong>Build Time:</strong> {self.build_time:.2f}s</li>"
            if self.run_time is not None:
                details_html += f"<li><strong>Run Time:</strong> {self.run_time:.2f}s</li>"
            details_html += f"<li><strong>Execution Time:</strong> {self.execution_time:.2f}s</li>"

            if self.total_time is not None:
                details_html += f"<li><strong>Total Time:</strong> {self.total_time:.2f}s</li>"
            
            if self.container_id:
                details_html += f"<li><strong>Container ID:</strong> {self.container_id}</li>"
            
            if self.dependencies:
                details_html += f"<li><strong>Dependencies:</strong> {', '.join(self.dependencies)}</li>"
            
            if self.files and len(self.files) > 0:
                details_html += "<li><strong>Files:</strong><ul>"
                for file, content in self.files.items():
                    details_html += f"<li>{file}</li>"
                details_html += "</ul></li>"
            
            if self.n_codefix_attempts is not None:
                details_html += f"<li><strong>Number of attempts:</strong> {self.n_codefix_attempts}</li>"
            
            
            
            if self.traceback:
                details_html += f"<li><strong>Traceback:</strong><pre style='background: #f1f1f1; padding: 10px; border-radius: 5px; color: red;'>{self.traceback}</pre></li>"

            if self.feedback:
                details_html += f"<li><strong>Feedback:</strong><pre style='background: #f1f1f1; padding: 10px; border-radius: 5px; color: red;'>{self.feedback}</pre></li>"
            
            if self.build_log:
                build_log_text = '\n'.join(self.build_log)
                # Truncate if too long (show first and last parts)
                if len(build_log_text) > 10000:
                    lines = self.build_log
                    first_lines = '\n'.join(lines[:50])
                    last_lines = '\n'.join(lines[-50:])
                    build_log_text = f"{first_lines}\n\n... ({len(lines) - 100} lines omitted) ...\n\n{last_lines}"
                details_html += f"<li><strong>Build Log:</strong><pre style='background: #f1f1f1; padding: 10px; border-radius: 5px; overflow-x: auto; max-height: 400px; overflow-y: auto;'>{build_log_text}</pre></li>"
            
            details_html += "</ul></div>"
            display(HTML(details_html))

    def _populate_stdout(self):
        """Populate the stdout section."""
        with self.stdout_output:
            self.stdout_output.clear_output(wait=True)
            if self.stdout:
                display(HTML(f"<div><h4>Standard Output</h4><pre style='background: white; padding: 10px; border-radius: 5px; overflow-x: auto;'>{self.stdout}</pre></div>"))
            else:
                display(HTML("<div><h4>Standard Output</h4><p><em>No output</em></p></div>"))

    def _populate_stderr(self):
        """Populate the stderr section."""
        with self.stderr_output:
            self.stderr_output.clear_output(wait=True)
            if self.stderr:
                display(HTML(f"<div><h4>Standard Error</h4><pre style='background: white; padding: 10px; border-radius: 5px; overflow-x: auto; color: red;'>{self.stderr}</pre></div>"))
            else:
                display(HTML("<div><h4>Standard Error</h4><p><em>No errors</em></p></div>"))

    def _populate_code(self):
        """Populate the code section."""
        with self.code_output:
            self.code_output.clear_output(wait=True)
            if self.code:
                # Check if the code is a notebook
                from ._utilities import is_notebook
                if is_notebook(self.code):
                    import json
                    notebook_data = json.loads(self.code)
                    
                    # Extract source code from notebook cells
                    source_code = ""
                    if "cells" in notebook_data:
                        for i, cell in enumerate(notebook_data["cells"]):
                            if cell.get("cell_type") == "code":
                                # Add cell number and source code
                                cell_source = cell.get("source", "")
                                if isinstance(cell_source, list):
                                    cell_source = "".join(cell_source)
                                
                                source_code += f"# Cell {i+1}\n{cell_source}\n\n"
                    
                    display(HTML(f"<div><h4>Executed Code (from notebook)</h4><pre style='background: white; padding: 10px; border-radius: 5px; overflow-x: auto; font-family: monospace;'>{source_code}</pre></div>"))
                else:
                    # Regular code, display as-is
                    display(HTML(f"<div><h4>Executed Code</h4><pre style='background: white; padding: 10px; border-radius: 5px; overflow-x: auto; font-family: monospace;'>{self.code}</pre></div>"))
            else:
                display(HTML("<div><h4>Executed Code</h4><p><em>No code available</em></p></div>"))

    def _populate_output(self):
        """Populate the output section."""
        with self.output_display:
            self.output_display.clear_output(wait=True)
            
            output_html = "<div><h4>Execution Output</h4>"
            
            output_html += self._html_output()
            
            output_html += "</div>"
            display(HTML(output_html))
            
    def _populate_save_notebook(self):
        """Populate the save notebook section."""
        with self.save_notebook_output:
            self.save_notebook_output.clear_output(wait=True)
            
            # Helper function to find first available Untitled filename
            def find_first_available_untitled():
                import os
                counter = 1
                while True:
                    filename = f"Untitled{counter}.ipynb"
                    if not os.path.exists(filename):
                        return filename
                    counter += 1
            
            # Helper function to get all available notebooks recursively
            def get_available_notebooks(result, depth=0):
                notebooks = []
                if result.files and '/display_output/notebook_executed.ipynb' in result.files:
                    notebooks.append((f"Current Result (depth {depth})", result))
                
                if result.former_result:
                    notebooks.extend(get_available_notebooks(result.former_result, depth + 1))
                
                return notebooks
            
            # Get available notebooks
            available_notebooks = get_available_notebooks(self)
            
            if not available_notebooks:
                display(HTML("<div><h4>❌ No notebooks available to save</h4></div>"))
                return
            
            # Create widgets
            filename_input = widgets.Text(
                value=find_first_available_untitled(),
                description='Filename:',
                style={'description_width': '100px'},
                layout=widgets.Layout(width='400px')
            )
            
            notebook_dropdown = widgets.Dropdown(
                options=[(f"{name}", notebook) for name, notebook in available_notebooks],
                value=available_notebooks[0][1] if available_notebooks else None,
                description='Notebook:',
                style={'description_width': '100px'},
                layout=widgets.Layout(width='400px')
            )
            
            save_button = widgets.Button(
                description='Save Notebook',
                button_style='success',
                layout=widgets.Layout(width='150px')
            )
            
            # Output widget for status messages
            status_output = widgets.Output()
            
            # Helper functions to avoid code duplication
            def show_success_message(filename, filepath, current_dir, was_overwritten=False):
                """Display success message after saving notebook."""
                overwrite_note = "<p><em>Previous file was overwritten.</em></p>" if was_overwritten else ""
                success_html = f"""
                <div style='color: green;'>
                    <h4>✅ Notebook Saved Successfully</h4>
                    <p><strong>File:</strong> <a href='{filepath}' target='_blank'>{filename}</a></p>
                    <p><strong>Location:</strong> {current_dir}</p>
                    {overwrite_note}
                </div>
                """
                display(HTML(success_html))
            
            def show_error_message(error):
                """Display error message when saving fails."""
                error_html = f"""
                <div style='color: red;'>
                    <h4>❌ Error Saving Notebook</h4>
                    <p><strong>Error:</strong> {str(error)}</p>
                </div>
                """
                display(HTML(error_html))
            
            def save_notebook_file(filepath, notebook_content):
                """Save the notebook file and return success status."""
                try:
                    with open(filepath, 'wb') as f:
                        f.write(notebook_content)
                    return True
                except Exception as e:
                    return e
            
            # Save button click handler
            def on_save_click(b):
                with status_output:
                    status_output.clear_output(wait=True)
                    
                    try:
                        selected_notebook = notebook_dropdown.value
                        filename = filename_input.value.strip()
                        
                        if not filename:
                            display(HTML("<div style='color: red;'>❌ Please enter a filename</div>"))
                            return
                        
                        if not filename.endswith('.ipynb'):
                            filename += '.ipynb'
                        
                        # Get the notebook content
                        notebook_content = selected_notebook.files['/display_output/notebook_executed.ipynb']
                        
                        # Get current working directory
                        import os
                        current_dir = os.getcwd()
                        filepath = os.path.join(current_dir, filename)
                        
                        # Check if file already exists
                        if os.path.exists(filepath):
                            # Show confirmation dialog instead of auto-overwriting
                            confirm_html = f"""
                            <div style='color: orange;'>
                                <h4>⚠️ File Already Exists</h4>
                                <p>The file <strong>{filename}</strong> already exists. Do you want to overwrite it?</p>
                            </div>
                            """
                            display(HTML(confirm_html))
                            
                            # Create a confirmation button widget
                            confirm_button = widgets.Button(
                                description='Confirm Overwrite',
                                button_style='warning',
                                layout=widgets.Layout(width='200px'),
                                style={'button_color': '#ff8c00'}  # Orange color matching the warning text
                            )
                            
                            def on_confirm_overwrite(b):
                                with status_output:
                                    status_output.clear_output(wait=True)
                                    result = save_notebook_file(filepath, notebook_content)
                                    if result is True:
                                        show_success_message(filename, filepath, current_dir, was_overwritten=True)
                                    else:
                                        show_error_message(result)
                            
                            confirm_button.on_click(on_confirm_overwrite)
                            display(confirm_button)
                            return
                        
                        # Write the notebook file (file doesn't exist)
                        result = save_notebook_file(filepath, notebook_content)
                        if result is True:
                            show_success_message(filename, filepath, current_dir, was_overwritten=False)
                        else:
                            show_error_message(result)
                        
                    except Exception as e:
                        show_error_message(e)
            
            save_button.on_click(on_save_click)
            
            # Create layout
            controls_layout = widgets.VBox([
                widgets.HBox([notebook_dropdown]),
                widgets.HBox([filename_input]),
                widgets.HBox([save_button]),
                status_output
            ])
            
            display(HTML("<div><h4>💾 Save Notebook</h4></div>"))
            display(controls_layout)

    

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
                     memory_limit=memory_limit,
                     gpu_support=gpu_support,
                     executor=executor)


def execute_notebook(notebook_json: str, dependencies: List[str] = [], 
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
                print("Docker daemon is not running. Starting Docker daemon...")
                subprocess.run(["dockerd"], check=True)
                self.client = docker.from_env()
            else:
                raise
        except Exception as e:
            print(f"Error initializing Docker client: {e}")
            self.client = None

        self.containers = []
        self.image_cache = {}  # Cache images by dependencies hash
        self.build_log_output = []  # Store build logs for the current execution
        
    
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
                            # Replace generic cupy with CUDA-compatible version for GPU support
                            if self.gpu_support and dep.strip().lower() == "cupy":
                                # Use cupy-cuda12x for CUDA 12.x compatibility
                                f.write("cupy-cuda12x\n")
                            else:
                                f.write(f"{dep}\n")
                    #print(f"Created requirements.txt with {dependencies}")
                
                # Create Dockerfile for notebook execution
                dockerfile_content = self._create_notebook_dockerfile(requirements_file is not None, display_output_container_path)
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
        
            result.code = notebook_json
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
                result.objects[filename] = content.decode("utf-8")
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

                if result.final_result is None and len(outputs) > 0:
                    result.final_result = str(outputs[-1]["data"]).strip("\n").split("\n")[-1]

        
        return result

    
    def _create_notebook_dockerfile(self, has_dependencies: bool, output_container_path: str) -> str:
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
RUN python3 -m pip install --no-cache-dir jupyter nbconvert

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
"""
        
        if self.gpu_support:
            # For GPU containers, run clinfo first to check GPU detection
            dockerfile += f"""CMD ["/bin/bash", "-c", "echo '=== OpenCL Info ===' && clinfo | head -n 50 && echo '=== Starting Notebook Execution ===' && jupyter nbconvert --to notebook --execute notebook.ipynb --output {output_container_path}/notebook_executed.ipynb"]
"""
        else:
            # Standard notebook execution
            dockerfile += f"""CMD ["jupyter", "nbconvert", "--to", "notebook", "--execute", "notebook.ipynb", "--output", "{output_container_path}/notebook_executed.ipynb"]
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
        display_output_container_path: str = "/display_output",
        dependencies: Optional[List[str]] = None
    ) -> docker.models.containers.Container:
        """Build and run the Docker container."""
        # Create a cache key based on dependencies and base image
        # Use a stable tag name for the same dependencies to leverage Docker layer caching
        import hashlib
        cache_key_parts = [self.base_image]
        if dependencies:
            cache_key_parts.extend(sorted(dependencies))
        cache_key = hashlib.md5("_".join(cache_key_parts).encode()).hexdigest()
        tag_name = f"sand-bob-{cache_key}"
        
        # Build the image - Docker will use layer cache for unchanged layers
        # (base image, system packages, Python dependencies) even if notebook changed
        start_time = time.time()
        
        # Process build logs to capture output (especially errors from pip install)
        self.build_log_output = []
        
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
        
        self.build_time = time.time() - start_time
        
        # Track if this was mostly cached by checking build time
        # Cached builds are typically much faster (<5s vs 30-60s)
        if self.build_time < 5 and cache_key in self.image_cache:
            # This was likely a cached build
            pass
        
        # Store in cache for tracking
        self.image_cache[cache_key] = image
        
        # Prepare container run parameters
        run_params = {
            'image': image.id,
            'detach': True,
            'mem_limit': self.memory_limit,
            'network_disabled': True,  # Disable network for security
            'remove': False
        }
        
        # Add GPU support if enabled
        if self.gpu_support:
            run_params['device_requests'] = [
                docker.types.DeviceRequest(count=-1, capabilities=[['gpu']])
            ]
            # Add NVIDIA environment variables for GPU access
            run_params['environment'] = {
                'NVIDIA_VISIBLE_DEVICES': 'all',
                'NVIDIA_DRIVER_CAPABILITIES': 'compute,utility'
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

class ExecutionResultList:
    """
    A GUI class that represents a list of ExecutionResult objects with tabs.
    Each tab represents one ExecutionResult, and clicking a tab shows that result.
    """
    
    def __init__(self, results: List[ExecutionResult], tab_names: Optional[List[str]] = None):
        """
        Initialize the ExecutionResultList with a list of ExecutionResult objects.
        
        Args:
            results: List of ExecutionResult objects to display
            tab_names: Optional list of custom tab names. If not provided, 
                      tabs will be named "Result 1", "Result 2", etc.
        """
        self.results = results
        if tab_names is not None and len(tab_names) != len(results):
            tab_names = None

        self.tab_names = tab_names or [f"Result {i+1}" for i in range(len(results))]

        # Use find_most_common_indices to identify similar results
        from ._utilities import find_most_common_indices
        similar_indices = find_most_common_indices([result.final_result if hasattr(result, 'final_result') else None for result in results])
        
        # Add a star similar indices even for custom names
        for i in similar_indices:
            if i < len(self.tab_names):
                self.tab_names[i] = f"{self.tab_names[i]}*"
    
        
        # Create the tabbed interface
        self._create_tabbed_interface()
    
    def _create_tabbed_interface(self):
        """Create the tabbed widget interface."""
        # Create tab children (overview + each execution result)
        self.overview_output = widgets.Output()
        self._populate_overview()

        tab_children = [self.overview_output]
        tab_titles = ["Overview"]

        for i, result in enumerate(self.results):
            if result is None:
                continue
            temp = result.render_inline if hasattr(result, 'render_inline') else True
            # Set render_inline to False to prevent automatic display
            result.render_inline = False
            
            # Create the widget for this result
            result._create_widget()
            
            # Combine header and result widget
            if hasattr(result, 'widget'):
                tab_content = result.widget
                tab_children.append(tab_content)
                if i < len(self.tab_names):
                    tab_titles.append(self.tab_names[i])
                else:
                    tab_titles.append(f"Result {i + 1}")

            result.render_inline = temp
        
        # Create the tab widget
        self.tab_widget = widgets.Tab()
        self.tab_widget.children = tab_children
        
        # Set tab titles
        for i, name in enumerate(tab_titles):
            self.tab_widget.set_title(i, name)
        
        # Add some styling to the tab widget
        self.tab_widget.layout = widgets.Layout(
            width='100%',
            height='auto'
        )

    def _get_final_results(self) -> List[Any]:
        """Collect non-empty final results from the list."""
        collected = []
        for result in self.results:
            if result is None or not hasattr(result, 'final_result'):
                continue
            if result.final_result is not None:
                collected.append(result.final_result)
        return collected

    def _classify_final_result(self, value: Any) -> str:
        """Classify final_result values into broad visualization-friendly types."""
        import numbers

        if isinstance(value, bool):
            return "other"
        if isinstance(value, numbers.Number):
            return "numeric"
        if isinstance(value, str):
            return "string"

        value_type = type(value)
        if value_type.__name__ == "DataFrame" and value_type.__module__.startswith("pandas"):
            return "dataframe"

        # Consider image-like arrays and PIL images as images.
        if value_type.__module__.startswith("numpy") and hasattr(value, "ndim"):
            if getattr(value, "ndim", 0) in (2, 3):
                return "image"

        if hasattr(value, "size") and hasattr(value, "mode") and value_type.__module__.startswith("PIL"):
            return "image"

        return "other"

    def _dominant_result_type(self, values: List[Any]) -> str:
        """Return the dominant result type among final results."""
        type_counts = {
            "numeric": 0,
            "string": 0,
            "image": 0,
            "dataframe": 0,
            "other": 0,
        }

        for value in values:
            type_counts[self._classify_final_result(value)] += 1

        dominant = max(type_counts, key=type_counts.get)
        return dominant

    def _render_word_cloud(self, text: str, title: str):
        """Render a word cloud for text data with a fallback when wordcloud is unavailable."""
        import matplotlib.pyplot as plt
        from collections import Counter

        cleaned = " ".join(str(text).split())
        if not cleaned:
            display(HTML("<p><em>No text available for word cloud.</em></p>"))
            return

        try:
            from wordcloud import WordCloud

            wc = WordCloud(width=1000, height=500, background_color="white").generate(cleaned)
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.imshow(wc, interpolation="bilinear")
            ax.axis("off")
            ax.set_title(title)
            display(fig)
            plt.close(fig)
            return
        except Exception:
            pass

        # Fallback: simple frequency chart when wordcloud dependency is unavailable.
        tokens = [t for t in cleaned.split(" ") if t]
        token_counts = Counter(tokens).most_common(20)
        if not token_counts:
            display(HTML("<p><em>No tokens available for fallback frequency plot.</em></p>"))
            return

        labels = [item[0] for item in token_counts]
        counts = [item[1] for item in token_counts]
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.barh(labels[::-1], counts[::-1], color="#4C72B0")
        ax.set_title(f"{title} (fallback frequency chart)")
        ax.set_xlabel("Frequency")
        display(fig)
        plt.close(fig)

    def _render_numeric_histogram(self, values: List[Any]):
        """Render a histogram for numeric final results."""
        import matplotlib.pyplot as plt

        numeric_values = []
        for value in values:
            if self._classify_final_result(value) == "numeric":
                numeric_values.append(float(value))

        if not numeric_values:
            display(HTML("<p><em>No numeric values available for histogram.</em></p>"))
            return

        fig, ax = plt.subplots(figsize=(9, 4))
        bins = min(20, max(5, len(numeric_values)))
        ax.hist(numeric_values, bins=bins, color="#2A9D8F", edgecolor="white")
        ax.set_title("Distribution of final_result values")
        ax.set_xlabel("Value")
        ax.set_ylabel("Count")
        display(fig)
        plt.close(fig)

    def _render_images_grid(self, values: List[Any]):
        """Render image-like final results in a grid."""
        import math
        import matplotlib.pyplot as plt
        import numpy as np

        images = []
        for value in values:
            if self._classify_final_result(value) != "image":
                continue

            array_value = None
            value_type = type(value)
            if value_type.__module__.startswith("numpy"):
                array_value = value
            elif hasattr(value, "size") and hasattr(value, "mode") and value_type.__module__.startswith("PIL"):
                array_value = np.array(value)

            if array_value is not None:
                images.append(array_value)

        if not images:
            display(HTML("<p><em>No image values available for image grid.</em></p>"))
            return

        n_images = len(images)
        n_cols = min(4, n_images)
        n_rows = math.ceil(n_images / n_cols)
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(3.2 * n_cols, 3.2 * n_rows))
        axes = np.array(axes).reshape(-1)

        for idx, ax in enumerate(axes):
            if idx < n_images:
                ax.imshow(images[idx], cmap="gray" if images[idx].ndim == 2 else None)
                ax.set_title(f"Result {idx + 1}")
                ax.axis("off")
            else:
                ax.axis("off")

        fig.suptitle("Image final_result overview", y=1.02)
        fig.tight_layout()
        display(fig)
        plt.close(fig)

    def _render_dataframe_columns_wordcloud(self, values: List[Any]):
        """Render a word cloud based on DataFrame column names."""
        columns = []
        for value in values:
            if self._classify_final_result(value) == "dataframe":
                try:
                    columns.extend([str(c) for c in list(value.columns)])
                except Exception:
                    continue

        if not columns:
            display(HTML("<p><em>No DataFrame columns found.</em></p>"))
            return

        self._render_word_cloud(" ".join(columns), "DataFrame column names")

    def _populate_overview(self):
        """Populate overview tab with adaptive visualization of final_result values."""
        with self.overview_output:
            self.overview_output.clear_output(wait=True)

            final_results = self._get_final_results()
            if not final_results:
                display(HTML("<div><h4>Overview</h4><p><em>No non-empty final_result values available.</em></p></div>"))
                return

            type_counts = {
                "numeric": 0,
                "string": 0,
                "image": 0,
                "dataframe": 0,
                "other": 0,
            }
            for value in final_results:
                type_counts[self._classify_final_result(value)] += 1

            dominant_type = self._dominant_result_type(final_results)

            summary_html = (
                "<div><h4>Overview</h4>"
                f"<p><strong>Total results with final_result:</strong> {len(final_results)}</p>"
                f"<p><strong>Dominant type:</strong> {dominant_type}</p>"
                f"<p>Counts -> Numeric: {type_counts['numeric']}, String: {type_counts['string']}, "
                f"Image: {type_counts['image']}, DataFrame: {type_counts['dataframe']}, Other: {type_counts['other']}</p>"
                "</div>"
            )
            display(HTML(summary_html))

            if dominant_type == "numeric":
                self._render_numeric_histogram(final_results)
            elif dominant_type == "string":
                joined_text = " ".join([str(v) for v in final_results if self._classify_final_result(v) == "string"])
                self._render_word_cloud(joined_text, "Word cloud of final_result text")
            elif dominant_type == "image":
                self._render_images_grid(final_results)
            elif dominant_type == "dataframe":
                self._render_dataframe_columns_wordcloud(final_results)
            else:
                preview = "<br>".join([str(v)[:200] for v in final_results[:10]])
                display(HTML(f"<p><em>Dominant type is not directly visualized. Preview:</em><br>{preview}</p>"))
    
    def display(self):
        """Display the tabbed interface."""
        display(self.tab_widget)
    
    def _repr_html_(self):
        """Return HTML representation for Jupyter display."""
        self.display()
        return ""
    
    def __len__(self):
        """Return the number of results."""
        return len(self.results)
    
    def __getitem__(self, index):
        """Get a result by index."""
        return self.results[index]
    
    def __iter__(self):
        """Iterate over results."""
        return iter(self.results)
    
    def append(self, result: ExecutionResult, tab_name: Optional[str] = None):
        """Add a new result to the list."""
        self.results.append(result)
        
        # Recalculate similar indices with the new result
        from ._utilities import find_most_common_indices
        similar_indices = find_most_common_indices(self.results)
        
        if tab_name is None:
            tab_name = f"Result {len(self.results)}"
        
        # Apply bold formatting if this new result is similar
        if len(self.results) - 1 in similar_indices and len(similar_indices) > 1:
            tab_name = f"<b>{tab_name}</b>"
        
        self.tab_names.append(tab_name)
        
        # Recreate the tabbed interface with the new result
        self._create_tabbed_interface() 


def test_gpu_support() -> ExecutionResult:
    """
    Test if GPU support is working correctly with pyclesperanto.
    
    This function tests basic pyclesperanto functionality in a GPU-enabled container.
    It creates a simple test image, applies a Gaussian blur, and verifies the output.
    
    Returns:
        ExecutionResult with test output showing GPU/pyclesperanto functionality
    """
    test_code = """
import pyclesperanto_prototype as cle
import numpy as np

# Print GPU device information
print("=== GPU Device Information ===")
print(f"Available GPUs: {cle.available_device_names()}")
print(f"Selected GPU: {cle.get_device()}")
print()

# Create a simple test image
print("=== Testing pyclesperanto ===")
test_image = np.random.rand(100, 100).astype(np.float32)
print(f"Created test image with shape: {test_image.shape}")

# Push image to GPU and apply Gaussian blur
gpu_image = cle.push(test_image)
print(f"Pushed image to GPU")

blurred = cle.gaussian_blur(gpu_image, sigma_x=2.0, sigma_y=2.0)
print(f"Applied Gaussian blur")

# Pull result back from GPU
result = cle.pull(blurred)
print(f"Result shape: {result.shape}")
print(f"Result mean: {result.mean():.4f}")
print()
print("✅ pyclesperanto GPU support is working correctly!")
"""
    
    result = execute(
        code=test_code,
        dependencies=[],  # pyclesperanto is already installed in GPU image
        gpu_support=True,
        timeout=60  # Allow more time for GPU initialization
    )
    
    return result
