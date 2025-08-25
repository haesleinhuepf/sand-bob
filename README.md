# Sand-Bob

A Python library for executing AI-generated code in Docker containers with automated issue detection and fixing.

## Features

- Python code generation using LLMs
- Execute Python code in isolated Docker containers
- Automatic detection of missing dependencies
- Automatic fixing of code errors
- Automatic generation and incorporation of code feedback
- Convenient display in Jupyter

## Installation

```bash
pip install sand-bob
```

## Quick Start

### Prompting for Python Code

```python
from sand_bob import generate_code

result = generate_code(
    prompt="Count the number of 'b's in blueberry.",
    dependencies=[]
)
print(result.final_result)
print(result.code)
```

## Advanced Usage

### 

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