def simplify(text):
    return text.strip().strip("\n").strip()

def extract_code(text):
    return remove_outer_markdown(text)


POSSBILE_MARKDOWN_FENCES = ["```python", "```Python", "```nextflow", "```java", "```javascript", "```macro", "```groovy", "```cmd"
                           "```jython", "```md", "```markdown", "```plaintext", "```tex", "```latex",
                           "```txt", "```csv", "```yml", "```yaml", "```json", "```JSON", "```py", "```svg", "```xml", "<FILE>", "```"]

def remove_outer_markdown(text):
    """
    Remove outer markdown syntax from the given text.

    Parameters
    ----------
    text : str
        The input text with potential markdown syntax.

    Returns
    -------
    str
        The text with outer markdown syntax removed and stripped.
    """
    text = text.strip("\n").strip(" ")

    possible_beginnings = POSSBILE_MARKDOWN_FENCES

    possible_endings = ["```", "</FILE>"]

    if any([text.startswith(beginning) for beginning in possible_beginnings]) and any([text.endswith(ending) for ending in possible_endings]):

        for beginning in possible_beginnings:
            if text.startswith(beginning):
                text = text[len(beginning):]
                break

        for ending in possible_endings:
            if text.endswith(ending):
                text = text[:-len(ending)]
                break
    elif any([ beginning in text for beginning in possible_beginnings]) and any([ ending in text for ending in possible_endings]):
        for beginning in possible_beginnings:
            if beginning in text:
                text = text.split(beginning)[1]
                break
        for ending in possible_endings:
            if ending in text:
                text = text.split(ending)[0]
                break

    text = text.strip("\n")

    return text


def load_base64_image(base64_image: str):
    """
    Load a base64 encoded image into a PIL image and a NumPy array.
    """
    import base64
    import io
    from PIL import Image
    import numpy as np
    
    # Decode the base64 string into bytes
    png_bytes_decoded = base64.b64decode(base64_image)
    
    # Load the byte array as a Pillow image
    image = Image.open(io.BytesIO(png_bytes_decoded))
    
    # Convert the Pillow image to a NumPy array
    image_array = np.array(image)
    
    return image, image_array

def np_image_to_base64_png(image_array):
    import base64
    import io
    from PIL import Image
    import numpy as np
    
    image = Image.fromarray(image_array)
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return img_str


def erase_outputs_of_code_cells(notebook_file_content: str):
    """
    Erase outputs of code cells in a Jupyter notebook.

    Parameters
    ----------
    notebook : str
        The notebook content as a string.
    """
    import re
    import json

    # removed invalid characters
    clean_file_content = re.sub(r'[\x00-\x1f\x7f]', '', notebook_file_content)

    notebook = json.loads(clean_file_content)
    for cell in notebook.get('cells', []):
        if cell.get('cell_type') == 'code':
            cell['outputs'] = []
            cell['execution_count'] = None
        #cell['id'] = None

    notebook["metadata"] = {}

    notebook_file_content = json.dumps(notebook, indent=1)
    return notebook_file_content


def python_code_to_notebook(python_code: str):
    """
    Convert a Python code string to a Jupyter notebook.
    """
    import json
    
    notebook = {
        "cells": [
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [p + "\n" for p in python_code.split("\n")]
                
            }
        ],
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3"
            },
            "language_info": {
                "codemirror_mode": {
                    "name": "ipython",
                    "version": 3
                },
                "file_extension": ".py",
                "mimetype": "text/x-python",
                "name": "python",
                "nbconvert_exporter": "python",
                "pygments_lexer": "ipython3",
                "version": "3.8.0"
            }
        },
        "nbformat": 4,
        "nbformat_minor": 4
    }
    return json.dumps(notebook, indent=1)


def is_notebook(code):
    import json
    stripped = code.strip()
    if stripped.startswith("{"):
        try:
            json.loads(stripped)
            return True
        except:
            return False
    return False


def strip_ansi(text):
    import re
    return re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', text)


def markdown_to_html(markdown_text):
    """
    Convert simple markdown to HTML.
    Supports: headers, bold, italic, links, code, lists, and paragraphs.
    """
    import re
    lines = markdown_text.split('\n')
    html_lines = []
    in_ul = False
    in_ol = False
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Check for unordered list items (-, *, +)
        ul_match = re.match(r'^[\s]*[-*+]\s+(.*)', line)
        if ul_match:
            if not in_ul:
                html_lines.append('<ul>')
                in_ul = True
            if in_ol:
                html_lines.append('</ol>')
                in_ol = False
            html_lines.append(f'<li>{ul_match.group(1)}</li>')
            i += 1
            continue
        
        # Check for ordered list items (1., 2., etc.)
        ol_match = re.match(r'^[\s]*\d+\.\s+(.*)', line)
        if ol_match:
            if not in_ol:
                html_lines.append('<ol>')
                in_ol = True
            if in_ul:
                html_lines.append('</ul>')
                in_ul = False
            html_lines.append(f'<li>{ol_match.group(1)}</li>')
            i += 1
            continue
        
        # Close list tags if we're no longer in a list
        if in_ul:
            html_lines.append('</ul>')
            in_ul = False
        if in_ol:
            html_lines.append('</ol>')
            in_ol = False
        
        # Add the line as-is for now
        html_lines.append(line)
        i += 1
    
    # Close any remaining open list tags
    if in_ul:
        html_lines.append('</ul>')
    if in_ol:
        html_lines.append('</ol>')
    
    # Join lines back together
    html = '\n'.join(html_lines)
    
    # Headers (# ## ### #### ##### ######)
    html = re.sub(r'^#{6}\s+(.*?)$', r'<h6>\1</h6>', html, flags=re.MULTILINE)
    html = re.sub(r'^#{5}\s+(.*?)$', r'<h5>\1</h5>', html, flags=re.MULTILINE)
    html = re.sub(r'^#{4}\s+(.*?)$', r'<h4>\1</h4>', html, flags=re.MULTILINE)
    html = re.sub(r'^#{3}\s+(.*?)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^#{2}\s+(.*?)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^#{1}\s+(.*?)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
    
    # Bold (**text** or __text__)
    html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'__(.*?)__', r'<strong>\1</strong>', html)
    
    # Italic (*text* or _text_)
    html = re.sub(r'\*(.*?)\*', r'<em>\1</em>', html)
    html = re.sub(r'_(.*?)_', r'<em>\1</em>', html)
    
    # Code (`code`)
    html = re.sub(r'```(.*?)```', r'<pre>\1</pre>', html)
    html = re.sub(r'`(.*?)`', r'<pre>\1</coprede>', html)
    
    # Links [text](url)
    html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', html)
        
    # Clean up empty paragraphs and extra whitespace
    html = re.sub(r'<p></p>', '', html)
    html = re.sub(r'\n+', '\n', html)
    
    return html.strip()


def we_are_in_a_notebook() -> bool:
    """Returns true if the code is currently executed in a Jupyter notebook."""
    # adapted from: https://stackoverflow.com/questions/15411967/how-can-i-check-if-code-is-executed-in-the-ipython-notebook
    from IPython.core.getipython import get_ipython

    try:
        shell = get_ipython().__class__.__name__
        if shell == 'ZMQInteractiveShell':
            return True   # Jupyter notebook or qtconsole
        elif shell == 'TerminalInteractiveShell':
            return False  # Terminal running IPython
        else:
            return False  # Other type (?)
    except NameError:
        return False      # Probably standard Python interpreter