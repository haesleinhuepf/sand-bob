#!/usr/bin/env python3
"""
Test script for the execute_notebook function.
"""

import json
import sys
import os

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from sand_bob import execute_notebook
    print("✓ Successfully imported execute_notebook")
except ImportError as e:
    print(f"✗ Failed to import execute_notebook: {e}")
    sys.exit(1)

# Simple test notebook
test_notebook = {
    "cells": [
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": ["print('Hello from notebook!')\n", "print('Test successful!')"]
        }
    ],
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.8.0"}
    },
    "nbformat": 4,
    "nbformat_minor": 4
}

def test_notebook_execution():
    """Test the execute_notebook function."""
    print("\nTesting execute_notebook function...")
    
    try:
        # Convert notebook to JSON string
        notebook_json_str = json.dumps(test_notebook)
        
        # Execute the notebook
        result = execute_notebook(
            notebook_json=notebook_json_str,
            dependencies=[],
            timeout=30
        )
        
        print(f"✓ Notebook execution completed")
        print(f"  Exit code: {result.exit_code}")
        print(f"  Execution time: {result.execution_time:.2f} seconds")
        
        if result.stdout:
            print(f"  STDOUT: {result.stdout.strip()}")
        
        if result.stderr:
            print(f"  STDERR: {result.stderr.strip()}")
        
        if result.exit_code == 0:
            print("✓ Test passed!")
            return True
        else:
            print("✗ Test failed - non-zero exit code")
            return False
            
    except Exception as e:
        print(f"✗ Test failed with exception: {e}")
        return False

if __name__ == "__main__":
    success = test_notebook_execution()
    sys.exit(0 if success else 1)
