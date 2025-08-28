import functools
import concurrent.futures
import copy
from typing import Callable, Any, List, Union


def parallel(func: Callable) -> Callable:
    """
    A decorator that executes a function either once or multiple times based on the 'n' parameter.
    
    When calling the decorated function:
    - If no 'n' parameter is passed: executes once and returns the result directly
    - If 'n' parameter is passed: executes 'n' times and returns a list of results
    
    Args:
        func: The function to be decorated
    
    Returns:
        A function that can be called with or without an 'n' parameter
    
    Example:
        @parallel
        def random_number():
            return random.randint(1, 100)
        
        # Single execution (no n parameter)
        result = random_number()  # Returns a single number
        
        # Multiple executions (with n parameter)
        results = random_number(n=5)  # Returns a list of 5 numbers
    """
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Union[Any, List[Any]]:
        # Check if 'n' parameter was passed
        if 'n_parallel' in kwargs:
            n = kwargs.pop('n_parallel')  # Remove 'n' from kwargs before calling the original function
            
            if n == 1:
                # Single execution - return result directly
                return func(*args, **kwargs)
            elif n > 1:
                # Multiple executions - run in parallel using ThreadPoolExecutor
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    # Submit all tasks
                    future_to_index = {
                        executor.submit(func, *copy.deepcopy(args), **copy.deepcopy(kwargs)): i 
                        for i in range(n)
                    }
                    
                    # Collect results in order
                    results = [None] * n
                    for future in concurrent.futures.as_completed(future_to_index):
                        index = future_to_index[future]
                        try:
                            results[index] = future.result()
                        except Exception as exc:
                            print(f'Task {index} generated an exception: {exc}')
                            # print the traceback
                            import traceback
                            print(traceback.format_exc())
                            results[index] = None
                    
                    return results
            else:
                raise ValueError("Parameter 'n_parallel' must be a positive integer")
        else:
            # No 'n' parameter - execute once and return result directly
            return func(*args, **kwargs)
    
    return wrapper


# Usage example
if __name__ == "__main__":
    import random
    import time
    
    # Example 1: Using the parallel decorator
    @parallel
    def generate_random():
        time.sleep(0.1)  # Simulate some work
        return random.randint(1, 100)
    
    # Single execution (no n parameter)
    single_result = generate_random()
    print(f"Single result: {single_result}")
    
    # Multiple executions (with n parameter) - now runs in parallel!
    print("Running 5 parallel executions...")
    start_time = time.time()
    multiple_results = generate_random(n=5)
    end_time = time.time()
    print(f"Multiple results: {multiple_results}")
    print(f"Time taken: {end_time - start_time:.3f} seconds")
    
    # Example 2: Function with parameters
    @parallel
    def add_numbers(a, b):
        time.sleep(0.1)  # Simulate some work
        return a + b
    
    # Single execution
    single_sum = add_numbers(3, 4)
    print(f"Single sum: {single_sum}")
    
    # Multiple executions - runs in parallel
    print("Running 3 parallel additions...")
    start_time = time.time()
    multiple_sums = add_numbers(3, 4, n=3)
    end_time = time.time()
    print(f"Multiple sums: {multiple_sums}")
    print(f"Time taken: {end_time - start_time:.3f} seconds")


