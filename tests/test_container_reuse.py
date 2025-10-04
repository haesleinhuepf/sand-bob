"""
Tests for container and image reuse functionality.
"""

import pytest
from sand_bob._executor import execute, CodeExecutor


class TestContainerReuse:
    """Test cases for container and image reuse."""
    
    def test_executor_image_cache(self):
        """Test that Docker layer caching works when reusing executor with same dependencies."""
        
        executor = CodeExecutor()
        
        # Use numpy to ensure we have a longer build time for first execution
        # First execution - will install numpy
        code1 = """
import numpy as np
print('First execution')
print(f'NumPy version: {np.__version__}')
"""
        result1 = execute(code1, ["numpy"], executor=executor)
        
        # Second execution with same dependency - should reuse cached layers
        code2 = """
import numpy as np
print('Second execution')
arr = np.array([1, 2, 3])
print(f'Array: {arr}')
"""
        result2 = execute(code2, ["numpy"], executor=executor)
        
        # Check both succeeded
        assert result1.exit_code == 0, f"First execution failed with exit code {result1.exit_code}"
        assert result2.exit_code == 0, f"Second execution failed with exit code {result2.exit_code}"
        
        # Check outputs are correct
        assert 'First execution' in result1.final_result or any('First execution' in str(o.get('data', '')) for o in (result1.outputs or []))
        assert 'Second execution' in result2.final_result or any('Second execution' in str(o.get('data', '')) for o in (result2.outputs or []))
        
        # Check that second execution has faster or similar build time (Docker layer caching)
        # The second build should be no slower than first (usually much faster)
        print(f"Build times - First: {result1.build_time}s, Second: {result2.build_time}s")
        assert result2.build_time <= result1.build_time + 2, \
            f"Expected second build to be faster or similar. " \
            f"First: {result1.build_time}s, Second: {result2.build_time}s"
        
        # Clean up
        executor.cleanup()
    
    def test_executor_image_cache_with_dependencies(self):
        """Test that Docker layer caching works correctly with different dependencies."""
        
        executor = CodeExecutor()
        
        # First execution with numpy
        code1 = """
import numpy as np
print(f"NumPy version: {np.__version__}")
"""
        result1 = execute(code1, ["numpy"], executor=executor)
        assert result1.exit_code == 0
        build_time1 = result1.build_time
        
        # Second execution with same dependency should use cached layers
        code2 = """
import numpy as np
arr = np.array([1, 2, 3])
print(f"Array: {arr}")
"""
        result2 = execute(code2, ["numpy"], executor=executor)
        assert result2.exit_code == 0
        # Should be faster or similar due to layer caching
        assert result2.build_time <= build_time1 + 2, \
            f"Expected build_time to be similar for cached layers. " \
            f"First: {build_time1}s, Second: {result2.build_time}s"
        
        # Third execution with different dependency should build new image
        code3 = """
import pandas as pd
df = pd.DataFrame({'a': [1, 2, 3]})
print(f"DataFrame: {df}")
"""
        result3 = execute(code3, ["pandas"], executor=executor)
        assert result3.exit_code == 0
        # Just verify it succeeded, build time varies
        print(f"Build times - numpy: {build_time1}s, numpy again: {result2.build_time}s, pandas: {result3.build_time}s")
        
        # Clean up
        executor.cleanup()
    
    def test_executor_reuse_across_multiple_runs(self):
        """Test that a single executor can be reused across many executions."""
        
        executor = CodeExecutor()
        
        # Run multiple executions with the same executor
        for i in range(5):
            code = f"print('Execution {i}')"
            result = execute(code, [], executor=executor)
            assert result.exit_code == 0
            # Check the output is in the result (it's stored in outputs/final_result)
            assert result.final_result == f"Execution {i}", \
                f"Expected 'Execution {i}', got '{result.final_result}'"
            
            print(f"Execution {i}: build_time={result.build_time}s")
        
        # Clean up
        executor.cleanup()
    
    def test_executor_cleanup(self):
        """Test that cleanup properly removes containers."""
        
        executor = CodeExecutor()
        
        # Run some executions
        code = "print('Test')"
        result = execute(code, [], executor=executor)
        assert result.exit_code == 0
        
        # Verify containers were created
        assert len(executor.containers) > 0, "Expected at least one container to be created"
        
        # Clean up
        initial_count = len(executor.containers)
        executor.cleanup()
        
        # Verify containers list is cleared
        assert len(executor.containers) == 0, f"Expected containers to be cleared, but {len(executor.containers)} remain"
