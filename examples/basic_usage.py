#!/usr/bin/env python3
"""
Basic usage example for Sand-Bob.
"""

from sand_bob import execute


def main():
    """Demonstrate basic usage of Sand-Bob."""
    print("🚀 Sand-Bob - Basic Usage Example")
    print("=" * 50)
    
    # Example 1: Simple code execution
    print("\n1. Simple code execution:")
    code1 = """
print("Hello from Docker!")
x = 10
y = 20
print(f"Sum: {x + y}")
"""
    
    result1 = execute(code1, [])
    print(f"Output: {result1.stdout.strip()}")
    print(f"Exit code: {result1.exit_code}")
    print(f"Execution time: {result1.execution_time:.2f}s")
    
    # Example 2: Code with dependencies
    print("\n2. Code with dependencies:")
    code2 = """
import requests
import json

# Make a simple API call
response = requests.get('https://httpbin.org/json')
data = response.json()
print(f"API Response: {data['slideshow']['author']}")
"""
    
    result2 = execute(code2, ["requests"])
    print(f"Output: {result2.stdout.strip()}")
    print(f"Exit code: {result2.exit_code}")
    
    # Example 3: Error handling
    print("\n3. Error handling:")
    code3 = """
import nonexistent_module
print("This won't execute")
"""
    
    result3 = execute(code3, [])
    print(f"Error: {result3.stderr.strip()}")
    print(f"Exit code: {result3.exit_code}")
    
    # Example 4: Custom Python version
    print("\n4. Custom Python version:")
    code4 = """
import sys
print(f"Python version: {sys.version}")
"""
    
    result4 = execute(code4, [], python_version="3.9")
    print(f"Output: {result4.stdout.strip()}")
    
    print("\n✅ All examples completed successfully!")


if __name__ == "__main__":
    main() 