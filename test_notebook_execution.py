#!/usr/bin/env python3
"""
Test script for notebook execution with output extraction.
"""

import json
from sand_bob._executor import CodeExecutor

def test_notebook_execution():
    """Test notebook execution with output extraction."""
    
    # Create a simple test notebook
    test_notebook = {
        "cells": [
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "import matplotlib.pyplot as plt\n",
                    "import numpy as np\n",
                    "\n",
                    "# Create a simple plot\n",
                    "x = np.linspace(0, 10, 100)\n",
                    "y = np.sin(x)\n",
                    "plt.plot(x, y)\n",
                    "plt.title('Simple Sine Wave')\n",
                    "plt.show()\n",
                    "\n",
                    "# Print some text output\n",
                    "print('Hello from notebook!')\n",
                    "print('This is a test output')\n"
                ]
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
    
    # Convert notebook to JSON string
    notebook_json = json.dumps(test_notebook)
    
    # Create executor
    executor = CodeExecutor(python_version="3.11", timeout=60)
    
    try:
        # Execute the notebook
        result = executor.execute_notebook(
            notebook_json=notebook_json,
            dependencies=["matplotlib", "numpy"]
        )
        
        print(f"Execution completed with exit code: {result.exit_code}")
        print(f"Execution time: {result.execution_time:.2f} seconds")
        
        # Check if notebook outputs were extracted
        if hasattr(result, 'notebook_outputs') and result.notebook_outputs:
            print(f"\nFound {len(result.notebook_outputs)} notebook outputs:")
            for i, output in enumerate(result.notebook_outputs):
                print(f"  Output {i+1}: {output['type']}")
                if output['type'] == 'text':
                    print(f"    Text: {output['data']}")
                elif output['type'] == 'image':
                    print(f"    Image shape: {output['data'].shape}")
        else:
            print("\nNo notebook outputs found.")
            
        # Print stdout and stderr
        if result.stdout:
            print(f"\nStdout:\n{result.stdout}")
        if result.stderr:
            print(f"\nStderr:\n{result.stderr}")
            
    except Exception as e:
        print(f"Error executing notebook: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up
        executor.cleanup()

if __name__ == "__main__":
    test_notebook_execution()
