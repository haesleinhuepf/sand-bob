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
    clean_file_content = clean_file_content.encode("ascii", errors="ignore")

    notebook = json.loads(clean_file_content)
    for cell in notebook.get('cells', []):
        if cell.get('cell_type') == 'code':
            cell['outputs'] = []
            cell['execution_count'] = None
        #cell['id'] = None

    notebook["metadata"] = {}

    notebook_file_content = json.dumps(notebook, indent=1)
    return notebook_file_content

def python_code_to_mystnb(python_code: str):
    """
    Convert a Python code string to a MyST notebook.
    """

    return f"""---
kernelspec:
  name: python3
  display_name: python3
jupytext:
  text_representation:
    extension: .md
    format_name: myst
    format_version: '0.13'
    jupytext_version: 1.13.8
---

```{{code-cell}} ipython3
{python_code}
```

"""



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


def find_most_common_indices(input_list):
    """
    Analyze a list of mixed types, group by type, find the most common items,
    and return their indices in the original list.
    
    Parameters
    ----------
    input_list : list
        A list containing items of various types (strings, numbers, arrays, etc.)
        
    Returns
    -------
    list
        List of indices from the original list corresponding to the most common items
        
    Examples
    --------
    >>> find_most_common_indices([1, 2, 2, 1, 1])
    [0, 3, 4]
    
    >>> find_most_common_indices(['a', 'b', 'a', 1, 2, 1])
    [0, 2, 3, 5]
    """
    import numpy as np
    from collections import Counter

    input_list = input_list.copy()
    
    if not input_list:
        return []
    
    # Group items by type
    type_groups = {}
    type_indices = {}
    
    for i, item in enumerate(input_list):
        # Determine the type category
        if isinstance(item, str):
            type_key = 'string'
        elif isinstance(item, (int, float, np.number)):
            type_key = 'number'
        elif isinstance(item, (list, tuple)):
            type_key = 'sequence'
        elif isinstance(item, np.ndarray):
            type_key = 'array'
        elif isinstance(item, dict):
            type_key = 'dict'
        elif isinstance(item, bool):
            type_key = 'boolean'
        else:
            type_key = 'other'
        
        # Add to type groups
        if type_key not in type_groups:
            type_groups[type_key] = []
            type_indices[type_key] = []
        
        type_groups[type_key].append(item)
        type_indices[type_key].append(i)
    
    # Find most common items in each type group and track the highest frequency
    most_common_indices = []
    highest_frequency = 0
    best_type_groups = []  # Store all type groups with the highest frequency
    
    for type_key, items in type_groups.items():
        if not items:
            continue
            
        # Count occurrences
        if type_key == 'array':
            # For numpy arrays, we need to handle them specially
            # Convert to tuples for hashing, but be careful with large arrays
            try:
                # Try to convert to tuples for counting
                item_tuples = []
                for item in items:
                    if item.size < 1000:  # Only convert small arrays to avoid memory issues
                        item_tuples.append(tuple(item.flatten()))
                    else:
                        # For large arrays, use a hash of the array
                        item_tuples.append(hash(str(item)))
                counter = Counter(item_tuples)
            except:
                # Fallback: treat each array as unique
                counter = Counter(range(len(items)))
        elif type_key == 'sequence':
            # For lists/tuples, convert to tuples for hashing
            try:
                item_tuples = [tuple(item) if isinstance(item, (list, tuple)) else item for item in items]
                counter = Counter(item_tuples)
            except:
                # Fallback: treat each sequence as unique
                counter = Counter(range(len(items)))
        elif type_key == 'dict':
            # For dictionaries, convert to tuples of sorted items
            try:
                item_tuples = [tuple(sorted(item.items())) for item in items]
                counter = Counter(item_tuples)
            except:
                # Fallback: treat each dict as unique
                counter = Counter(range(len(items)))
        else:
            # For other types (strings, numbers, booleans), count directly
            counter = Counter([str(i) for i in items])
        
        if not counter:
            continue
            
        # Find the most common item(s) and their frequency, excluding None
        max_count = max(counter.values())
        most_common_items = [item for item, count in counter.items() if count == max_count and item is not None]
        
        # If all most common items were None, find the next most common non-None items
        if not most_common_items and max_count > 0:
            # Get all items with their counts, excluding None
            non_none_items = [(item, count) for item, count in counter.items() if item is not None]
            if non_none_items:
                # Find the highest count among non-None items
                max_non_none_count = max(count for _, count in non_none_items)
                most_common_items = [item for item, count in non_none_items if count == max_non_none_count]
        
        # Update if this type group has higher or equal frequency
        if max_count > highest_frequency:
            highest_frequency = max_count
            best_type_groups = [(type_key, most_common_items)]
        elif max_count == highest_frequency:
            best_type_groups.append((type_key, most_common_items))
    
    # Process all type groups with the highest frequency
    for best_type_key, best_most_common_items in best_type_groups:
        items = type_groups[best_type_key]
        for common_item in best_most_common_items:
            for i, item in enumerate(items):
                if best_type_key == 'array':
                    # Compare arrays
                    if item.size < 1000:
                        if tuple(item.flatten()) == common_item:
                            most_common_indices.append(type_indices[best_type_key][i])
                    else:
                        if hash(str(item)) == common_item:
                            most_common_indices.append(type_indices[best_type_key][i])
                elif best_type_key == 'sequence':
                    # Compare sequences
                    try:
                        item_tuple = tuple(item) if isinstance(item, (list, tuple)) else item
                        if item_tuple == common_item:
                            most_common_indices.append(type_indices[best_type_key][i])
                    except:
                        pass
                elif best_type_key == 'dict':
                    # Compare dictionaries
                    try:
                        item_tuple = tuple(sorted(item.items()))
                        if item_tuple == common_item:
                            most_common_indices.append(type_indices[best_type_key][i])
                    except:
                        pass
                else:
                    # Direct string comparison for other types
                    if str(item) == str(common_item):
                        most_common_indices.append(type_indices[best_type_key][i])
    
    return sorted(most_common_indices)


import json
import re
import string

_WS = set(" \t\r\n")

def _prev_non_ws(s: str, i: int) -> int:
    j = i - 1
    while j >= 0 and s[j] in _WS:
        j -= 1
    return j

def _next_non_ws(s: str, i: int) -> int:
    j = i
    while j < len(s) and s[j] in _WS:
        j += 1
    return j

def _patch_invalid_escape(s: str, pos: int) -> str:
    # If the char at pos isn't a backslash, try the previous non-ws char.
    if pos >= len(s) or s[pos] != "\\":
        p = _prev_non_ws(s, pos+1 if pos < len(s) else len(s))
        if p >= 0 and s[p] == "\\":
            pos = p
        else:
            return s
    return s[:pos] + "\\\\" + s[pos+1:]

def _patch_missing_comma(s: str, pos: int) -> str:
    """
    Heuristics:
    1) If we're right before a closing } or ], and there's a trailing comma
       immediately before that, remove the trailing comma.
    2) Otherwise, insert a comma just before the current non-ws token,
       unless it would follow {, [, or , (which would be illegal).
    """
    k = _next_non_ws(s, pos)
    # Case 1: trailing comma before } or ]
    if k < len(s) and s[k] in "}]":
        # Find previous non-ws position; if it's a comma, remove it
        p = _prev_non_ws(s, k)
        if p >= 0 and s[p] == ",":
            return s[:p] + s[p+1:]
        # Otherwise, nothing to fix here
        return s

    # Case 2: insert a comma before the next token if previous token isn't an opener or comma
    prev = _prev_non_ws(s, k)
    if prev >= 0 and s[prev] not in "{[,":
        return s[:k] + "," + s[k:]
    return s

def fix_json(s: str, max_retries: int = 20):
    """
    Try to load JSON string `s`. On specific errors, attempt minimal edits and retry:
      - Invalid \\escape -> double the offending backslash
      - Expecting ',' delimiter -> insert missing comma OR remove trailing comma
    Raises the last exception if it cannot be repaired within `max_retries`.
    """
    for _ in range(max_retries):
        try:
            json.loads(s)
            return s
        except json.decoder.JSONDecodeError as e:
            msg = str(e)
            m = re.search(r"\(char (\d+)\)", msg)
            pos = int(m.group(1)) if m else None

            if pos is None:
                # Can't locate; give up gracefully
                print(f"Warning: Failed to fix JSON: {e}")
                raise

            if "Invalid \\escape" in msg:
                s2 = _patch_invalid_escape(s, pos)
                if s2 == s:
                    raise
                s = s2
                continue

            if "Expecting ',' delimiter" in msg:
                s2 = _patch_missing_comma(s, pos)
                if s2 == s:
                    raise
                s = s2
                continue

            # Different error: fail fast (or add more heuristics as needed)
            raise
    raise ValueError("Failed to repair JSON after multiple attempts")


def objects_identical(object1, object2):
    """
    Check if two objects are identical by comparing their JSON representations.
    """
    try:
        json1 = json.dumps(object1, sort_keys=True)
        json2 = json.dumps(object2, sort_keys=True)
        return json1 == json2
    except (TypeError, ValueError):
        # If objects are not JSON serializable, fall back to direct comparison
        return object1 == object2