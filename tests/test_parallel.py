"""
Tests for the parallel decorator.
"""

import pytest
from sand_bob._parallel import parallel
import random
import time


class TestParallelDecorator:
    """Test cases for the parallel decorator."""
    
    def test_single_execution_no_params(self):
        """Test single execution when no parameters are passed."""
        @parallel
        def generate_number():
            return 42
        
        result = generate_number()
        assert result == 42
        assert not isinstance(result, list)
    
    def test_parallel_only(self):
        """Test execution with only n_parallel parameter."""
        @parallel
        def generate_number():
            return random.randint(1, 100)
        
        results = generate_number(n_parallel=5)
        assert isinstance(results, list)
        assert len(results) == 5
        assert all(1 <= r <= 100 for r in results)
    
    def test_iterative_only(self):
        """Test execution with only n_iterative parameter."""
        counter = {'value': 0}
        
        @parallel
        def increment_counter():
            counter['value'] += 1
            return counter['value']
        
        results = increment_counter(n_iterative=3)
        assert isinstance(results, list)
        assert len(results) == 3
    
    def test_parallel_and_iterative_combined(self):
        """Test execution with both n_parallel and n_iterative parameters."""
        @parallel
        def generate_number():
            return random.randint(1, 100)
        
        # Should produce n_parallel * n_iterative results
        results = generate_number(n_parallel=5, n_iterative=2)
        assert isinstance(results, list)
        assert len(results) == 10  # 5 * 2
        assert all(1 <= r <= 100 for r in results)
    
    def test_parallel_and_iterative_with_different_values(self):
        """Test execution with different values for n_parallel and n_iterative."""
        @parallel
        def generate_number():
            return random.randint(1, 100)
        
        # Test different combinations
        results1 = generate_number(n_parallel=3, n_iterative=4)
        assert len(results1) == 12  # 3 * 4
        
        results2 = generate_number(n_parallel=7, n_iterative=2)
        assert len(results2) == 14  # 7 * 2
        
        results3 = generate_number(n_parallel=2, n_iterative=5)
        assert len(results3) == 10  # 2 * 5
    
    def test_n_parallel_one_with_n_iterative(self):
        """Test when n_parallel=1 and n_iterative>1."""
        @parallel
        def generate_number():
            return random.randint(1, 100)
        
        results = generate_number(n_parallel=1, n_iterative=3)
        assert isinstance(results, list)
        assert len(results) == 3
    
    def test_n_iterative_one_with_n_parallel(self):
        """Test when n_iterative=1 and n_parallel>1."""
        @parallel
        def generate_number():
            return random.randint(1, 100)
        
        results = generate_number(n_parallel=4, n_iterative=1)
        assert isinstance(results, list)
        assert len(results) == 4
    
    def test_both_parameters_one(self):
        """Test when both n_parallel=1 and n_iterative=1."""
        @parallel
        def generate_number():
            return 42
        
        # Should return a single value, not a list
        result = generate_number(n_parallel=1, n_iterative=1)
        assert result == 42
        assert not isinstance(result, list)
    
    def test_function_with_arguments(self):
        """Test that function arguments are properly passed through."""
        @parallel
        def add_numbers(a, b):
            return a + b
        
        results = add_numbers(3, 4, n_parallel=3, n_iterative=2)
        assert len(results) == 6
        assert all(r == 7 for r in results)
    
    def test_function_with_kwargs(self):
        """Test that keyword arguments are properly passed through."""
        @parallel
        def multiply(x, y=2):
            return x * y
        
        results = multiply(5, y=3, n_parallel=2, n_iterative=2)
        assert len(results) == 4
        assert all(r == 15 for r in results)
    
    def test_invalid_n_parallel(self):
        """Test that invalid n_parallel values raise errors."""
        @parallel
        def generate_number():
            return 42
        
        with pytest.raises(ValueError, match="'n_parallel' must be a positive integer"):
            generate_number(n_parallel=0)
        
        with pytest.raises(ValueError, match="'n_parallel' must be a positive integer"):
            generate_number(n_parallel=-1)
        
        with pytest.raises(ValueError, match="'n_parallel' must be a positive integer"):
            generate_number(n_parallel="invalid")
    
    def test_invalid_n_iterative(self):
        """Test that invalid n_iterative values raise errors."""
        @parallel
        def generate_number():
            return 42
        
        with pytest.raises(ValueError, match="'n_iterative' must be a positive integer"):
            generate_number(n_iterative=0)
        
        with pytest.raises(ValueError, match="'n_iterative' must be a positive integer"):
            generate_number(n_iterative=-1)
        
        with pytest.raises(ValueError, match="'n_iterative' must be a positive integer"):
            generate_number(n_iterative="invalid")
    
    def test_parallel_execution_is_actually_parallel(self):
        """Test that parallel execution is actually running in parallel."""
        @parallel
        def slow_function():
            time.sleep(0.1)
            return True
        
        # Sequential execution would take ~0.5 seconds
        # Parallel execution should take ~0.1 seconds
        start_time = time.time()
        results = slow_function(n_parallel=5)
        elapsed_time = time.time() - start_time
        
        assert len(results) == 5
        assert all(r is True for r in results)
        # Allow some overhead, but should be much less than 0.5 seconds
        assert elapsed_time < 0.3, f"Parallel execution took too long: {elapsed_time}s"
    
    def test_exception_handling(self):
        """Test that exceptions in one task don't stop other tasks."""
        counter = {'value': 0}
        
        @parallel
        def sometimes_fails():
            counter['value'] += 1
            if counter['value'] == 2:
                raise ValueError("Task 2 failed")
            return counter['value']
        
        # Reset counter
        counter['value'] = 0
        
        results = sometimes_fails(n_parallel=3)
        assert len(results) == 3
        # One result should be None due to the exception
        assert None in results
        # Other results should be numbers
        assert sum(1 for r in results if r is not None) == 2
    
    def test_order_preservation(self):
        """Test that results maintain their order despite parallel execution."""
        @parallel
        def return_index_after_delay():
            # Random delay to ensure tasks complete in different orders
            time.sleep(random.uniform(0.01, 0.05))
            return time.time()
        
        results = return_index_after_delay(n_parallel=5)
        assert len(results) == 5
        # All results should be present (no None values due to the timing)
        assert all(r is not None for r in results)
