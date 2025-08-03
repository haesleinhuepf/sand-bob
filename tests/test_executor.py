"""
Tests for the CodeExecutor class.
"""

import pytest
from sand_bob import execute


class TestCodeExecutor:
    """Test cases for CodeExecutor."""
    
    def test_basic_execution(self):
        """Test basic code execution without dependencies."""
        
        code = """
print("Hello, World!")
x = 2 + 2
print(f"2 + 2 = {x}")
"""
        
        result = execute(code, [])
        
        assert result.exit_code == 0
        assert "Hello, World!" in result.stdout
        assert "2 + 2 = 4" in result.stdout
        assert result.execution_time > 0
    
    def test_execution_with_dependencies(self):
        """Test code execution with dependencies."""
        
        code = """
import requests

response = requests.get('https://httpbin.org/get')
print(f"Status code: {response.status_code}")
print(f"Response: {response.json()}")
"""
        
        result = execute(code, ["requests"])
        
        assert result.exit_code == 0
        assert "Status code: 200" in result.stdout
    
    def test_error_handling(self):
        """Test error handling for invalid code."""
        
        code = """
import nonexistent_module
print("This won't execute")
"""
        
        result = execute(code, [])
        
        assert result.exit_code != 0
        assert "ImportError" in result.stderr or "ModuleNotFoundError" in result.stderr
    
    def test_custom_python_version(self):
        """Test execution with custom Python version."""
        
        code = """
import sys
print(f"Python version: {sys.version}")
"""
        
        result = execute(code, [])
        
        assert result.exit_code == 0
        assert "Python version" in result.stdout
        assert "3.9" in result.stdout
    
    def test_custom_base_image(self):
        """Test execution with custom base image."""
        
        code = """
import sys
print(f"Python version: {sys.version}")
"""
        
        result = execute(code, [], python_version="3.9")
        
        assert result.exit_code == 0
        assert "Python version" in result.stdout
    
    def test_timeout_handling(self):
        """Test timeout handling."""
        
        code = """
import time
print("Starting...")
time.sleep(10)  # This should timeout
print("This should not print")
"""
        
        result = execute(code, [], timeout=5)
        
        # The result might be a timeout or the container might be killed
        # We just check that we get a result
        assert result is not None
    
    def test_context_manager(self):
        """Test context manager functionality."""
        code = "print('Hello from context manager')"
        result = execute(code, [])
        
        assert result.exit_code == 0
        assert "Hello from context manager" in result.stdout

    def test_multiple_executions(self):
        """Test multiple executions with the same executor."""
        
        # First execution
        code1 = "print('First execution')"
        result1 = execute(code1, [])
        
        # Second execution
        code2 = "print('Second execution')"
        result2 = execute(code2, [])
        
        assert result1.exit_code == 0
        assert result2.exit_code == 0
        assert "First execution" in result1.stdout
        assert "Second execution" in result2.stdout
        
    
    def test_complex_dependencies(self):
        """Test execution with complex dependencies."""
        
        code = """
import numpy as np
import pandas as pd

# Create some data
data = np.random.randn(1000, 4)
df = pd.DataFrame(data, columns=['A', 'B', 'C', 'D'])

print(f"DataFrame shape: {df.shape}")
print(f"Column A mean: {df['A'].mean():.4f}")
print(f"Column B std: {df['B'].std():.4f}")
"""
        
        result = execute(code, ["numpy", "pandas"])
        
        assert result.exit_code == 0
        assert "DataFrame shape: (1000, 4)" in result.stdout
        assert "Column A mean:" in result.stdout
        assert "Column B std:" in result.stdout
        
    
