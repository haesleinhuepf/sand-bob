import time
import tempfile
import os
import json
import html
import uuid
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
        if self.save_notebook_output is not None:
            display(self.save_notebook_output)

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
                    parsed_output += f"<pre>{html.escape(str(output['data']))}</pre>"
                else:
                    parsed_output += f"<pre>{html.escape(str(output['data']))}</pre>"

        return parsed_output


    def _create_widget(self, include_chain_selector: bool = True):
            """Create the main interface using HTML tabs and optional history selector."""
            # Keep ipywidgets only for the save notebook section.
            self.save_notebook_output = None
            if self.files and '/display_output/notebook_executed.ipynb' in self.files:
                    self.save_notebook_output = widgets.Output()
                    self._populate_save_notebook()

            chain: List[ExecutionResult] = [self]
            if include_chain_selector:
                    chain = []
                    cursor = self
                    seen = set()
                    while cursor is not None:
                            cursor_id = id(cursor)
                            if cursor_id in seen:
                                    break
                            seen.add(cursor_id)
                            chain.append(cursor)
                            cursor = cursor.former_result
                    chain = list(reversed(chain))

            root_id = f"sb-res-{uuid.uuid4().hex}"
            sections_html = []
            options_html = []

            for i, result in enumerate(chain):
                    label = f"Result {i+1} (exit {getattr(result, 'exit_code', 'n/a')})"
                    options_html.append(f"<option value='{i}'>{html.escape(label)}</option>")
                    section_style = "" if i == len(chain) - 1 else "display:none;"
                    sections_html.append(
                            f"<div class='sb-history-panel' data-index='{i}' style='{section_style}'>"
                            f"{result._build_tabs_html(root_id=f'{root_id}-tabs-{i}')}</div>"
                    )

            history_selector_html = ""
            if include_chain_selector and len(chain) > 1:
                    history_selector_html = (
                            f"<div class='sb-history-bar'>"
                            f"<label for='{root_id}-history' class='sb-history-label'>History:</label>"
                            f"<select id='{root_id}-history' class='sb-history-select'>{''.join(options_html)}</select>"
                            f"</div>"
                    )

            script_html = ""
            if include_chain_selector and len(chain) > 1:
                    default_index = len(chain) - 1
                    script_html = f"""
<script>
(function() {{
    const root = document.getElementById('{root_id}');
    if (!root) return;
    const select = root.querySelector('#{root_id}-history');
    const panels = Array.from(root.querySelectorAll('.sb-history-panel'));
    if (!select) return;
    select.value = '{default_index}';
    const show = function(index) {{
        panels.forEach(function(panel) {{
            panel.style.display = panel.dataset.index === String(index) ? '' : 'none';
        }});
    }};
    select.addEventListener('change', function() {{
        show(select.value);
    }});
    show(select.value);
}})();
</script>
"""

            html_content = f"""
<div id='{root_id}' class='sb-result-root'>
    {ExecutionResult._tabs_css()}
    {history_selector_html}
    {''.join(sections_html)}
</div>
{script_html}
"""
            self.widget = HTML(html_content)

    @staticmethod
    def _tabs_css() -> str:
        return """
<style>
.sb-result-root {
    --sb-border: #c8c8c8;
    --sb-tab-bg: #f1f1f1;
    --sb-tab-hover-bg: #dadada;
    --sb-active-bg: #ffffff;
    --sb-content-bg: #ffffff;
    --sb-text: #2d2d2d;
    --sb-muted-text: #4a4a4a;
    --sb-shadow: rgba(0, 0, 0, 0.06);
    --sb-active-top: #1e6fff;
    margin-top: 8px;
    color: var(--sb-text);
    font-size: 12px;
}

.sb-history-bar {
    margin: 0 0 10px 0;
    display: flex;
    align-items: center;
    gap: 8px;
}

.sb-history-label {
    font-weight: 600;
    font-size: 13px;
}

.sb-history-select {
    min-width: 210px;
    padding: 4px 8px;
    border: 1px solid var(--sb-border);
    border-radius: 4px;
    background: #fff;
    color: var(--sb-text);
}

.sb-history-panel {
    margin: 0;
}

.sb-tabs {
    border: none;
    border-radius: 0;
    background: transparent;
    box-shadow: none;
    overflow: hidden;
}

.sb-tab-buttons {
    display: flex;
    align-items: center;
    gap: 2px;
    padding: 4px 6px 0 6px;
    border-bottom: 1px solid var(--sb-border);
    background: transparent;
    overflow-x: auto;
    overflow-y: hidden;
    scrollbar-width: thin;
}

.sb-tab-btn {
    appearance: none;
    border: 1px solid var(--sb-border);
    border-bottom: none;
    margin: 0;
    background: transparent;
    color: var(--sb-muted-text);
    padding: 5px 12px;
    cursor: pointer;
    font-size: 12px;
    line-height: 1.25;
    white-space: nowrap;
    position: relative;
    border-radius: 2px 2px 0 0;
    transition: background-color 120ms ease, color 120ms ease, border-color 120ms ease;
}

.sb-tab-btn:hover {
    background: transparent;
    color: var(--sb-text);
}

.sb-tab-btn.active {
    background: transparent;
    color: var(--sb-text);
    font-weight: 500;
    border-color: var(--sb-border);
    border-bottom-color: var(--sb-active-bg);
    box-shadow: inset 0 2px 0 var(--sb-active-top);
    z-index: 1;
    margin-bottom: -1px;
}

.sb-tab-content {
    padding: 14px;
    background: transparent;
    border-left: 1px solid var(--sb-border);
    border-right: 1px solid var(--sb-border);
    border-bottom: 1px solid var(--sb-border);
}

.sb-tab-panel {
    display: none;
}

.sb-tab-panel.active {
    display: block;
}

.sb-tab-content pre {
    margin-top: 8px;
    border: 1px solid #e7ebf2;
    border-radius: 6px;
}
</style>
"""

    def _build_tabs_html(self, root_id: str) -> str:
        from ._config import config
        tabs = [
            ("Output", self._output_html()),
            ("Code", self._code_html()),
            ("Details", self._details_html()),
        ]
        if config.debug:
            tabs += [
                ("Prompt", self._prompt_html()),
                ("StdOut", self._stdout_html()),
                ("StdErr", self._stderr_html()),
            ]

        buttons = []
        panels = []
        for i, (title, body) in enumerate(tabs):
            active = " active" if i == 0 else ""
            panel_display = " active" if i == 0 else ""
            buttons.append(
                f"<button class='sb-tab-btn{active}' type='button' data-tab-index='{i}'>{html.escape(title)}</button>"
            )
            panels.append(
                f"<div class='sb-tab-panel{panel_display}' data-panel-index='{i}'>{body}</div>"
            )

        script = f"""
<script>
(function() {{
  const root = document.getElementById('{root_id}');
  if (!root) return;
    const buttonsBar = Array.from(root.children).find(function(child) {{
        return child.classList && child.classList.contains('sb-tab-buttons');
    }});
    const content = Array.from(root.children).find(function(child) {{
        return child.classList && child.classList.contains('sb-tab-content');
    }});
    if (!buttonsBar || !content) return;
    const buttons = Array.from(buttonsBar.children).filter(function(child) {{
        return child.classList && child.classList.contains('sb-tab-btn');
    }});
    const panels = Array.from(content.children).filter(function(child) {{
        return child.classList && child.classList.contains('sb-tab-panel');
    }});
  const activate = function(index) {{
    buttons.forEach(function(btn) {{
      btn.classList.toggle('active', btn.dataset.tabIndex === String(index));
    }});
    panels.forEach(function(panel) {{
      panel.classList.toggle('active', panel.dataset.panelIndex === String(index));
    }});
  }};
  buttons.forEach(function(btn) {{
    btn.addEventListener('click', function() {{
      activate(btn.dataset.tabIndex);
    }});
  }});
  activate(0);
}})();
</script>
"""

        return (
            f"<div id='{root_id}' class='sb-tabs'>"
            f"<div class='sb-tab-buttons'>{''.join(buttons)}</div>"
            f"<div class='sb-tab-content'>{''.join(panels)}</div>"
            f"</div>{script}"
        )




    def _populate_details(self):
        """Populate the details section."""
        display(HTML(self._details_html()))

    def _populate_stdout(self):
        """Populate the stdout section."""
        display(HTML(self._stdout_html()))

    def _populate_stderr(self):
        """Populate the stderr section."""
        display(HTML(self._stderr_html()))

    def _populate_code(self):
        """Populate the code section."""
        display(HTML(self._code_html()))

    def _populate_prompt(self):
        """Populate the prompt section."""
        display(HTML(self._prompt_html()))


    def _populate_output(self):
        """Populate the output section."""
        display(HTML(self._output_html()))

    def _output_html(self) -> str:
        return "<div><h4>Execution Output</h4>" + self._html_output() + "</div>"

    def _stdout_html(self) -> str:
        if self.stdout:
            return (
                "<div>"
                f"<pre style='background: white; padding: 10px; border-radius: 5px; overflow-x: auto;'>{html.escape(self.stdout)}</pre></div>"
            )
        return "<div><em>No output</em></p></div>"

    def _stderr_html(self) -> str:
        if self.stderr:
            return (
                "<div>"
                f"<pre style='background: white; padding: 10px; border-radius: 5px; overflow-x: auto; color: red;'>{html.escape(self.stderr)}</pre></div>"
            )
        return "<div><em>No errors</em></div>"

    def _python_code_to_html(self, source_code: str) -> str:
        """Convert Python source code to a syntax-highlighted HTML pre block."""
        import builtins
        import io
        import keyword
        import tokenize

        if not source_code:
            return (
                "<pre style='background: white; padding: 10px; border-radius: 5px; "
                "overflow-x: auto; font-family: monospace;'></pre>"
            )

        token_styles = {
            "keyword": "color: var(--jp-mirror-editor-keyword-color, #008000); font-weight: 600;",
            "string": "color: var(--jp-mirror-editor-string-color, #BA2121);",
            "comment": "color: var(--jp-mirror-editor-comment-color, #408080); font-style: italic;",
            "number": "color: var(--jp-mirror-editor-number-color, #080);",
            "operator": "color: var(--jp-mirror-editor-operator-color, #AA22FF);",
            "builtin": "color: var(--jp-mirror-editor-builtin-color, #0000FF);",
        }

        builtin_names = set(dir(builtins))
        lines = source_code.splitlines(keepends=True)
        offsets = [0]
        for line in lines:
            offsets.append(offsets[-1] + len(line))

        def _index(line_no: int, col_no: int) -> int:
            # Tokenizer line numbers are 1-based.
            return offsets[line_no - 1] + col_no

        highlighted_parts = []
        last_index = 0

        try:
            tokens = tokenize.generate_tokens(io.StringIO(source_code).readline)
            for token in tokens:
                if token.type == tokenize.ENDMARKER:
                    break

                start_idx = _index(token.start[0], token.start[1])
                end_idx = _index(token.end[0], token.end[1])

                if start_idx > last_index:
                    highlighted_parts.append(html.escape(source_code[last_index:start_idx]))

                token_text = source_code[start_idx:end_idx]
                style = None

                if token.type == tokenize.NAME:
                    if keyword.iskeyword(token.string):
                        style = token_styles["keyword"]
                    elif token.string in builtin_names:
                        style = token_styles["builtin"]
                elif token.type == tokenize.STRING:
                    style = token_styles["string"]
                elif token.type == tokenize.COMMENT:
                    style = token_styles["comment"]
                elif token.type == tokenize.NUMBER:
                    style = token_styles["number"]
                elif token.type == tokenize.OP:
                    style = token_styles["operator"]

                escaped = html.escape(token_text)
                if style:
                    highlighted_parts.append(f"<span style='{style}'>{escaped}</span>")
                else:
                    highlighted_parts.append(escaped)

                last_index = end_idx

            if last_index < len(source_code):
                highlighted_parts.append(html.escape(source_code[last_index:]))

        except (tokenize.TokenError, IndentationError):
            highlighted_parts = [html.escape(source_code)]

        highlighted_code = "".join(highlighted_parts)
        return (
            "<pre style='background: white; "
            "overflow-x: auto; font-family: monospace;'>"
            f"{highlighted_code}</pre>"
        )

    def _code_html(self) -> str:
        if not self.code:
            return "<div><h4>Executed Code</h4><p><em>No code available</em></p></div>"

        from ._utilities import is_notebook
        if is_notebook(self.code):
            notebook_data = json.loads(self.code)
            source_code = ""
            for i, cell in enumerate(notebook_data.get("cells", [])):
                if cell.get("cell_type") == "code":
                    cell_source = cell.get("source", "")
                    if isinstance(cell_source, list):
                        cell_source = "".join(cell_source)
                    source_code += f"# Cell {i+1}\\n{cell_source}\\n\\n"
            return (
                "<div>"
                f"{self._python_code_to_html(source_code)}</div>"
            )

        return (
            "<div>"
            f"{self._python_code_to_html(self.code)}</div>"
        )

    def _prompt_html(self) -> str:
        if self.prompt:
            return (
                "<div>"
                f"<pre style='background: white; padding: 10px; border-radius: 5px; overflow-x: auto; font-family: monospace;'>{html.escape(self.prompt)}</pre></div>"
            )
        return "<div><h4>Prompt</h4><p><em>No prompt available</em></p></div>"

    def _details_html(self) -> str:
        from ._config import config
        details_html = "<div><h4>Execution Details</h4><ul style='list-style: none; padding: 0;'>"

        if self.reason is not None:
            details_html += f"<li><strong>Execution reason:</strong> {html.escape(str(self.reason))}</li>"

        if self.dependencies:
            deps = ', '.join([html.escape(str(dep)) for dep in self.dependencies])
            details_html += f"<li><strong>Dependencies:</strong> {deps}</li>"

        if self.final_result is not None:
            details_html += f"<li><strong>Final result:</strong> {html.escape(str(self.final_result))}</li>"
        if self.summary is not None:
            details_html += f"<li><strong>Summary:</strong> {html.escape(str(self.summary))}</li>"

        if self.build_time is not None:
            details_html += f"<li><strong>Build Time:</strong> {self.build_time:.2f}s</li>"
        if self.run_time is not None:
            details_html += f"<li><strong>Run Time:</strong> {self.run_time:.2f}s</li>"
        details_html += f"<li><strong>Execution Time:</strong> {self.execution_time:.2f}s</li>"

        if self.total_time is not None:
            details_html += f"<li><strong>Total Time:</strong> {self.total_time:.2f}s</li>"

        if self.files and len(self.files) > 0:
            details_html += "<li><strong>Files:</strong><ul>"
            for file, _content in self.files.items():
                details_html += f"<li>{html.escape(str(file))}</li>"
            details_html += "</ul></li>"

        if self.traceback:
            details_html += f"<li><strong>Traceback:</strong><pre style='padding: 10px; border-radius: 5px; color: red;'>{html.escape(self.traceback)}</pre></li>"

        if self.feedback:
            details_html += f"<li><strong>Feedback:</strong><pre style='padding: 10px; border-radius: 5px; color: red;'>{html.escape(self.feedback)}</pre></li>"

        if config.debug:
            details_html += f"<li><strong>Exit Code:</strong> <span style='color: {'green' if self.exit_code == 0 else 'red'};'>{self.exit_code}</span></li>"
            if self.container_id:
                details_html += f"<li><strong>Container ID:</strong> {html.escape(str(self.container_id))}</li>"

            if self.n_codefix_attempts is not None:
                details_html += f"<li><strong>Number of attempts:</strong> {self.n_codefix_attempts}</li>"

            if self.build_log:
                build_log_text = '\n'.join(self.build_log)
                if len(build_log_text) > 10000:
                    lines = self.build_log
                    first_lines = '\n'.join(lines[:50])
                    last_lines = '\n'.join(lines[-50:])
                    build_log_text = f"{first_lines}\n\n... ({len(lines) - 100} lines omitted) ...\n\n{last_lines}"
                details_html += (
                    "<li><strong>Build Log:</strong>"
                    f"<pre style='padding: 10px; border-radius: 5px; overflow-x: auto; max-height: 400px; overflow-y: auto;'>{html.escape(build_log_text)}</pre></li>"
                )

        details_html += "</ul></div>"

        from ._config import config
        config_html = config._repr_html_()

        return details_html + config_html

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
        """Create an HTML tab interface (ipywidgets-free)."""
        tab_titles = ["Overview"]
        tab_panels = [self._populate_overview()]

        for i, result in enumerate(self.results):
            if result is None:
                continue

            temp = result.render_inline if hasattr(result, 'render_inline') else True
            result.render_inline = False
            result._create_widget(include_chain_selector=False)

            if hasattr(result, 'widget'):
                tab_content = result.widget.data if hasattr(result.widget, 'data') else str(result.widget)
                tab_panels.append(tab_content)
                if i < len(self.tab_names):
                    tab_titles.append(self.tab_names[i])
                else:
                    tab_titles.append(f"Result {i + 1}")

            result.render_inline = temp

        root_id = f"sb-list-{uuid.uuid4().hex}"
        buttons = []
        panels = []
        for i, title in enumerate(tab_titles):
            active = " active" if i == 0 else ""
            buttons.append(
                f"<button class='sb-tab-btn{active}' type='button' data-tab-index='{i}'>{html.escape(str(title))}</button>"
            )
            panel_class = "sb-tab-panel active" if i == 0 else "sb-tab-panel"
            panel_html = tab_panels[i] if i < len(tab_panels) else ""
            panels.append(f"<div class='{panel_class}' data-panel-index='{i}'>{panel_html}</div>")

        self.tab_widget_html = HTML(
            f"""
<div id='{root_id}' class='sb-result-root'>
        {ExecutionResult._tabs_css()}
    <div class='sb-tabs'>
        <div class='sb-tab-buttons'>{''.join(buttons)}</div>
        <div class='sb-tab-content'>{''.join(panels)}</div>
    </div>
</div>
<script>
(function() {{
    const root = document.getElementById('{root_id}');
    if (!root) return;
    const topTabs = Array.from(root.children).find(function(child) {{
        return child.classList && child.classList.contains('sb-tabs');
    }});
    if (!topTabs) return;
    const buttonsBar = Array.from(topTabs.children).find(function(child) {{
        return child.classList && child.classList.contains('sb-tab-buttons');
    }});
    const content = Array.from(topTabs.children).find(function(child) {{
        return child.classList && child.classList.contains('sb-tab-content');
    }});
    if (!buttonsBar || !content) return;
    const buttons = Array.from(buttonsBar.children).filter(function(child) {{
        return child.classList && child.classList.contains('sb-tab-btn');
    }});
    const panels = Array.from(content.children).filter(function(child) {{
        return child.classList && child.classList.contains('sb-tab-panel');
    }});
    const activate = function(index) {{
        buttons.forEach(function(btn) {{
            btn.classList.toggle('active', btn.dataset.tabIndex === String(index));
        }});
        panels.forEach(function(panel) {{
            panel.classList.toggle('active', panel.dataset.panelIndex === String(index));
        }});
    }};
    buttons.forEach(function(btn) {{
        btn.addEventListener('click', function() {{
            activate(btn.dataset.tabIndex);
        }});
    }});
    activate(0);
}})();
</script>
"""
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
        from ._utilities import plt_to_html_image

        cleaned = " ".join(str(text).split())
        if not cleaned:
            return "<p><em>No text available for word cloud.</em></p>"
            return

        from wordcloud import WordCloud

        wc = WordCloud(width=1000, height=500, background_color="white").generate(cleaned)
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.imshow(wc, interpolation="bilinear")
        ax.axis("off")
        ax.set_title(title)
        
        return plt_to_html_image(fig)
    

    def _render_numeric_histogram(self, values: List[Any]) -> str:
        """Render a histogram for numeric final results as an embeddable HTML image."""
        import matplotlib.pyplot as plt
        from ._utilities import plt_to_html_image

        numeric_values = []
        for value in values:
            if self._classify_final_result(value) == "numeric":
                numeric_values.append(float(value))

        if not numeric_values:
            return "<p><em>No numeric values available for histogram.</em></p>"

        fig, ax = plt.subplots(figsize=(9, 4))
        bins = min(20, max(5, len(numeric_values)))
        ax.hist(numeric_values, bins=bins, color="#2A9D8F", edgecolor="white")
        ax.set_title("Distribution of final_result values")
        ax.set_xlabel("Value")
        ax.set_ylabel("Count")

        return plt_to_html_image(fig)

    def _render_images_grid(self, values: List[Any]) -> str:
        """Render image-like final results in a grid."""
        import math
        import matplotlib.pyplot as plt
        import numpy as np
        from ._utilities import plt_to_html_image

        images = []
        indices = []
        for i, value in enumerate(values):
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
                indices.append(i)

        if not images:
            return "<p><em>No image values available for image grid.</em></p>"

        n_images = len(images)
        n_cols = min(4, n_images)
        n_rows = math.ceil(n_images / n_cols)
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(3.2 * n_cols, 3.2 * n_rows))
        axes = np.array(axes).reshape(-1)

        for idx, ax in enumerate(axes):
            if idx < n_images:
                ax.imshow(images[idx], cmap="gray" if images[idx].ndim == 2 else None)
                ax.set_title(f"Result {indices[idx] + 1}")
                ax.axis("off")
            else:
                ax.axis("off")

        fig.suptitle("Image results overview", y=1.02)
        fig.tight_layout()

        return plt_to_html_image(fig)

    def _render_dataframe_columns_wordcloud(self, values: List[Any]) -> str:
        """Render a word cloud based on DataFrame column names."""
        columns = []
        for value in values:
            if self._classify_final_result(value) == "dataframe":
                try:
                    columns.extend([str(c) for c in list(value.columns)])
                except Exception:
                    continue

        if not columns:
            return "<p><em>Empty DataFrame</em></p>"

        return self._render_word_cloud(" ".join(columns), "DataFrame column names")

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

        color = "#ffffff"

        if value is None:
            bgcolor = "#b0b0b0"
            color = "#111000"

        result_type = self._classify_final_result(value)

        output = str(value)

        if "Error" in output or "Exception" in output:
            bgcolor = "#e24a4a" 
        elif result_type == "dataframe":
            bgcolor = "#f5b33a"
            output = f"DataFrame ({getattr(value, 'shape', '')})"
        elif result_type == "image":
            bgcolor = "#67cc23"
            output = "Image"
            if hasattr(value, "shape"):
                output += f" ({value.shape})"
        elif result_type == "numeric":
            bgcolor = "#4a90e2"
        elif result_type == "string":
            bgcolor = "#8a4fff"
            preview = html.escape(value[:10])
            length = len(value)
            output = f"{preview}... ({length})" if length > 10 else preview
        else:
            bgcolor = "#555555"
            output = html.escape(str(type(value)))

        return (
            f"<td style='background:{bgcolor};color:{color};padding:6px 10px;"
            f"border:1px solid #ffffff;'>{output}</td>"
        )

    def display_result_summary(self, headline: bool = False):
        display(HTML(self._render_result_summary(headline=headline)))

    def _render_result_summary(self, headline: bool = False):
        type_counts = {
            "numeric": 0,
            "string": 0,
            "image": 0,
            "dataframe": 0,
            "other": 0,
        }

        html = ""

        final_results = self._get_final_results()

        for value in final_results:
            type_counts[self._classify_final_result(value)] += 1

        dominant_type = self._dominant_result_type(final_results)

        if headline:
            html += "<div style='margin:10px 0 14px 0;'><h5 style='margin:0 0 8px 0;'>Result summary</h5></div>"

        def highlight_type(t):
            return f"<strong>{t.capitalize()}</strong>" if t == dominant_type else t.capitalize()

        html += (
            "<div style='margin:10px 0 14px 0;'>"
            f"<p>{len(final_results)} results: {highlight_type('numeric')}: {type_counts['numeric']}, {highlight_type('string')}: {type_counts['string']}, "
            f"{highlight_type('image')}: {type_counts['image']}, {highlight_type('dataframe')}: {type_counts['dataframe']}, {highlight_type('other')}: {type_counts['other']}</p>"
            "</div>"
        )

        if dominant_type == "numeric":
            html += self._render_numeric_histogram(final_results)
        elif dominant_type == "string":
            joined_text = " ".join([str(v) for v in final_results if self._classify_final_result(v) == "string"])
            html += self._render_word_cloud(joined_text, "Word cloud of final_result text")
        elif dominant_type == "image":
            html += self._render_images_grid(final_results)
        elif dominant_type == "dataframe":
            html += self._render_dataframe_columns_wordcloud(final_results)
        else:
            preview = "<br>".join([str(v)[:200] for v in final_results[:10]])
            html += f"<p><em>Preview:</em><br>{preview}</p>"

        return html

    def display_result_history(self, headline: bool = False):
        display(HTML(self._render_result_history(headline=headline)))

    def _render_result_history(self, headline: bool = False):
        """Render a simplified table of former_result chains for each result."""
        html = ""
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
            html += table_html

        table_html = (
            "<div style='overflow-x:auto;'>"
            "<table style='border-collapse:collapse;width:max-content;min-width:100%;font-family:monospace;font-size:12px;'>"
            "<tbody>"
            f"{''.join(rows_html)}"
            "</tbody>"
            "</table>"
            "</div>"
        )

        html += table_html
        return html

    def _populate_overview(self):
        """Build overview tab content as HTML."""
        html = self._render_result_summary(headline=True)
        html += self._render_result_history(headline=True)

        rows_html = []
        for row_index, result in enumerate(self.results):
            chain = self._trace_result_chain(result)

            if not chain:
                row_cells = "<td style='background:#b0b0b0;color:#111;padding:6px 10px;border:1px solid #ffffff;'>None</td>"
            else:
                result_values = [getattr(item, "final_result", None) for item in chain]
                for i, item in enumerate(chain):
                    if item.error is not None:
                        result_values[i] = item.error
                row_cells = "".join(self._format_simplified_final_result_td(r) for r in result_values)

            rows_html.append(
                "<tr>"
                f"<td style='padding:6px 10px;border:1px solid #ddd;background:#f5f5f5;white-space:nowrap;'><strong>Process {row_index + 1}</strong></td>"
                f"{row_cells}"
                "</tr>"
            )

        history_html = (
            "<div style='margin:10px 0 14px 0;'>"
            "<h5 style='margin:0 0 8px 0;'>Result tracing</h5>"
            "Results changed from iteration to iteration as follows (final results on the right):"
            "</div>"
            "<div style='overflow-x:auto;'>"
            "<table style='border-collapse:collapse;width:max-content;min-width:100%;font-family:monospace;font-size:12px;'>"
            "<tbody>"
            f"{''.join(rows_html)}"
            "</tbody>"
            "</table>"
            "</div>"
        )
        
        return html

    def display(self):
        """Display the tabbed interface."""
        display(self.tab_widget_html)
    
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
