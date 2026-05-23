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
    """Result of code execution with details, outputs, and an interactive widget interface."""
    stdout: str
    stderr: str
    exit_code: int
    execution_time: float
    run_time: Optional[float] = None
    build_time: Optional[float] = None
    container_id: Optional[str] = None
    prompt: Optional[str] = None
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
    render_inline: bool = False
    build_log: Optional[List[str]] = None
    summary: Optional[str] = None
    error: Optional[str] = None
    reason: Optional[str] = None

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
        self.prompt_output = widgets.Output()
        self.output_display = widgets.Output()
        
        # Create save notebook output if notebook file exists
        self.save_notebook_output = None
        if self.files and '/display_output/notebook_executed.ipynb' in self.files:
            self.save_notebook_output = widgets.Output()
            # Populate save notebook content immediately
            self._populate_save_notebook()
        
        # Create tab children in the specified order: output, code, details, stdout, stderr, save notebook
        tab_children = [self.output_display, self.code_output, self.prompt_output, self.details_output, self.stdout_output, self.stderr_output]
        tab_titles = ["Output", "Code", "Prompt", "Details", "StdOut", "StdErr"]
        
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
        self._populate_prompt()
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
            if self.reason is not None:
                details_html += f"<li><strong>Execution reason:</strong> {self.reason}</li>"
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

    def _populate_prompt(self):
        """Populate the prompt section."""
        with self.prompt_output:
            self.prompt_output.clear_output(wait=True)
            if self.prompt:
                display(HTML(f"<div><h4>Prompt</h4><pre style='background: white; padding: 10px; border-radius: 5px; overflow-x: auto; font-family: monospace;'>{self.prompt}</pre></div>"))
            else:
                display(HTML("<div><h4>Prompt</h4><p><em>No prompt available</em></p></div>"))


    def _populate_output(self):
        """Populate the output section."""
        with self.output_display:
            self.output_display.clear_output(wait=True)
            
            output_html = "<div><h4>Execution Output</h4>"
            
            output_html += self._html_output()
            
            output_html += "</div>"
            display(HTML(output_html))

    def display_output(self):
        display(HTML("<pre>" + self._html_output() + "</pre>"))    

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

    def _trace_result_chain(self, result: Optional[ExecutionResult]) -> List[ExecutionResult]:
        """Return a result chain from oldest to newest following former_result links."""
        if result is None:
            return []

        chain = []
        seen = set()
        cursor = result

        while cursor is not None:
            cursor_id = id(cursor)
            if cursor_id in seen:
                break
            seen.add(cursor_id)
            chain.append(cursor)
            cursor = getattr(cursor, "former_result", None)

        return list(reversed(chain))

    def _format_simplified_final_result_td(self, value: Any) -> str:
        """Format one simplified table cell for a final_result value."""
        import html

        if value is None:
            return "<td style='background:#b0b0b0;color:#111;padding:6px 10px;border:1px solid #ffffff;'>None</td>"

        if isinstance(value, bool):
            return (
                "<td style='background:#e2904a;color:white;padding:6px 10px;"
                f"border:1px solid #ffffff;'>{value}</td>"
            )
        if isinstance(value, int) or isinstance(value, float):
            return (
                "<td style='background:#4a90e2;color:white;padding:6px 10px;"
                f"border:1px solid #ffffff;'>{value}</td>"
            )

        if isinstance(value, str):
            if "Error" in value or "Exception" in value:
                return (
                    "<td style='background:#e24a4a;color:white;padding:6px 10px;"
                    f"border:1px solid #ffffff;'>{value}</td>"
                )
            preview = html.escape(value[:10])
            length = len(value)
            if len(value) > 10:
                return (
                    "<td style='background:#8a4fff;color:white;padding:6px 10px;"
                    f"border:1px solid #ffffff;'>{preview}... ({length})</td>"
                )
            else:
                return (
                    "<td style='background:#8a4fff;color:white;padding:6px 10px;"
                    f"border:1px solid #ffffff;'>{preview}</td>"
                )


        type_text = html.escape(str(type(value)))
        return (
            "<td style='background:#555555;color:white;padding:6px 10px;"
            f"border:1px solid #ffffff;'>{type_text}</td>"
        )


    def display_result_summary(self, headline: bool = False):
        type_counts = {
            "numeric": 0,
            "string": 0,
            "image": 0,
            "dataframe": 0,
            "other": 0,
        }

        final_results = self._get_final_results()

        for value in final_results:
            type_counts[self._classify_final_result(value)] += 1

        dominant_type = self._dominant_result_type(final_results)

        if headline:
            display(HTML("<div style='margin:10px 0 14px 0;'><h5 style='margin:0 0 8px 0;'>Result summary</h5><p>Summary of final_result values across all results:</p></div>"))

        summary_html = (
            "<div style='margin:10px 0 14px 0;'>"
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

    def display_result_history(self, headline: bool = False):
        """Render a simplified table of former_result chains for each result."""
        rows_html = []

        for row_index, result in enumerate(self.results):
            chain = self._trace_result_chain(result)

            if not chain:
                row_cells = "<td style='background:#b0b0b0;color:#111;padding:6px 10px;border:1px solid #ffffff;'>None</td>"
            else:
                result_values = [getattr(item, "final_result", None) for item in chain]
                for i, result in enumerate(chain):
                    if result.error is not None:
                        result_values[i] = result.error

                row_cells = "".join(self._format_simplified_final_result_td(r) for r in result_values)

            row_html = (
                "<tr>"
                f"<td style='padding:6px 10px;border:1px solid #ddd;background:#f5f5f5;white-space:nowrap;'><strong>Process {row_index + 1}</strong></td>"
                f"{row_cells}"
                "</tr>"
            )
            rows_html.append(row_html)

        if headline:
            table_html = (
                "<div style='margin:10px 0 14px 0;'>"
                "<h5 style='margin:0 0 8px 0;'>Result tracing</h5>"
                "Results changed from iteration to iteration as follows (final results on the right):"
                "</div>")
            display(HTML(table_html))

        table_html = (
            "<div style='overflow-x:auto;'>"
            "<table style='border-collapse:collapse;width:max-content;min-width:100%;font-family:monospace;font-size:12px;'>"
            "<tbody>"
            f"{''.join(rows_html)}"
            "</tbody>"
            "</table>"
            "</div>"
        )

        display(HTML(table_html))

    def _populate_overview(self):
        """Populate overview tab with adaptive visualization of final_result values."""
        with self.overview_output:
            self.overview_output.clear_output(wait=True)

            final_results = self._get_final_results()
            if final_results:
                
                self.display_result_summary(headline=True)

            self.display_result_history(headline=True)

            from  ._config import config
            display(HTML(config._repr_html_()))

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

    @property
    def consistency(self) -> float:
        """Return the consistency of the results.
        
        Consistency is defined as the maximum count of any identical final_result
        divided by the total number of results. Returns 0.0 if there are no results.
        """
        if not self.results:
            return 0.0

        counts = {}
        for result in self.results:
            value = result.final_result if hasattr(result, 'final_result') else None
            if value is not None:
                try:
                    key = value
                    hash(key)
                except TypeError:
                    key = id(value)
                counts[key] = counts.get(key, 0) + 1

        try:
            return max(counts.values()) / len(self.results)
        except ValueError:
            return 0.0
