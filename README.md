# Sand-Bob

A Python library for executing code in Docker containers with automatic dependency management.

## Features

- Execute Python code in isolated Docker containers
- Automatic dependency installation
- Support for custom Python versions
- Volume mounting for file processing
- Clean container lifecycle management
- Error handling and output capture

## Installation

```bash
pip install sand-bob
```

## Quick Start

```python
from sand_bob import execute

# Execute code with dependencies
code = """
import pandas as pd

df = pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})

print(df)
"""

result = execute(code, dependencies=["pandas"])
print(result.stdout)
print(f"Exit code: {result.exit_code}")
```

## Advanced Usage

### Custom Python Version

```python
from sand_bob import CodeExecutor

code = """
import sys
print(f"Python version: {sys.version}")
"""

result = execute(code, dependencies=[], python_version="3.11")
print(result.stdout)
```

### Volume Mounting for File Processing

```python
from sand_bob import execute
import tempfile
import os

# Create a temporary directory with files to process
with tempfile.TemporaryDirectory() as host_dir:
    # Create sample files
    sample_file = os.path.join(host_dir, "data.txt")
    with open(sample_file, 'w') as f:
        f.write("Hello, Sand-Bob!\nThis is a test file.")
    
    # Code to process files in the mounted directory
    code = """
import os

mounted_dir = "/mounted_data"
print("Files in mounted directory:")
for file in os.listdir(mounted_dir):
    file_path = os.path.join(mounted_dir, file)
    if os.path.isfile(file_path):
        with open(file_path, 'r') as f:
            content = f.read()
            print(f"  {file}: {content}")
    """
    
    # Execute with volume mounting
    result = execute(
        code,
        dependencies=[],
        host_path=host_dir,  # Host directory to mount
        container_path="/mounted_data"  # Container path
    )
    print(result.stdout)
```

### Error Handling

```python
from sand_bob import execute

code = """
import nonexistent_module
print("This won't execute")
"""

result = execute(code, dependencies=[])
if result.exit_code != 0:
    print(f"Error: {result.stderr}")
```

## API Reference

### execute

- `code` (str): The code to execute.
- `dependencies` (List[str]): The dependencies to install.
- `host_path` (Optional[str]): The path to the directory on the host to mount (optional).
- `container_path` (str): The path inside the container where the volume will be mounted (optional).
- `python_version` (str): The Python version to use (optional).
- `base_image` (str): The base image to use (optional).
- `timeout` (int): The timeout for the execution (optional).
- `memory_limit` (str): The memory limit for the container (optional).

#### Result Attributes

- `stdout` (str): Standard output
- `stderr` (str): Standard error
- `exit_code` (int): Exit code of the execution
- `execution_time` (float): Execution time in seconds
- `container_id` (Optional[str]): ID of the container used for execution

## Examples

Check out the `examples/` directory for more detailed examples.

## Requirements

- Docker
- Docker Compose
- Python 3.8+

## Similar Projects

* [SandboxAI](https://github.com/substratusai/sandboxai)


## License

BSD-3 License 