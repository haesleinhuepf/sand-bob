import functools
import concurrent.futures
import copy
from typing import Callable, Any, List, Union


def parallel(func: Callable) -> Callable:
    """
    A decorator that executes a function either once or multiple times based on the 'n_parallel' and 'n_iterative' parameters.
    
    When calling the decorated function:
    - If no parameters are passed: executes once and returns the result directly
    - If 'n_parallel' parameter is passed: executes 'n_parallel' times in parallel and returns a list of results
    - If 'n_iterative' parameter is passed: executes 'n_iterative' times sequentially and returns a list of results
    - If both 'n_parallel' and 'n_iterative' are passed: executes 'n_iterative' iterations, each with 'n_parallel' parallel executions, returning a flat list of n_parallel * n_iterative results
    
    Args:
        func: The function to be decorated
    
    Returns:
        A function that can be called with or without 'n_parallel' and 'n_iterative' parameters
    
    Example:
        @parallel
        def random_number():
            return random.randint(1, 100)
        
        # Single execution (no parameters)
        result = random_number()  # Returns a single number
        
        # Multiple parallel executions
        results = random_number(n_parallel=5)  # Returns a list of 5 numbers
        
        # Multiple iterative executions
        results = random_number(n_iterative=3)  # Returns a list of 3 numbers
        
        # Combined parallel and iterative executions
        results = random_number(n_parallel=5, n_iterative=2)  # Returns a flat list of 10 numbers
    """
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Union[Any, List[Any]]:
        # Extract parameters
        n_parallel = kwargs.pop('n_parallel', None)
        n_iterative = kwargs.pop('n_iterative', None)
        
        # If neither parameter is specified, execute once
        if n_parallel is None and n_iterative is None:
            return func(*args, **kwargs)
        
        # Set defaults
        if n_parallel is None:
            n_parallel = 1
        if n_iterative is None:
            n_iterative = 1
            
        # Validate parameters
        if not isinstance(n_parallel, int) or n_parallel < 1:
            raise ValueError("Parameter 'n_parallel' must be a positive integer")
        if not isinstance(n_iterative, int) or n_iterative < 1:
            raise ValueError("Parameter 'n_iterative' must be a positive integer")
        
        # If both are 1, execute once and return directly
        if n_parallel == 1 and n_iterative == 1:
            return func(*args, **kwargs)
        
        # Collect all results in a flat list
        all_results = []
        
        # Iterate n_iterative times
        for iteration in range(n_iterative):
            if n_parallel == 1:
                # Single execution for this iteration
                result = func(*copy.deepcopy(args), **copy.deepcopy(kwargs))
                all_results.append(result)
            else:
                # Multiple executions in parallel for this iteration
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    # Submit all tasks
                    future_to_index = {
                        executor.submit(func, *copy.deepcopy(args), **copy.deepcopy(kwargs)): i 
                        for i in range(n_parallel)
                    }
                    
                    # Collect results in order for this iteration
                    iteration_results = [None] * n_parallel
                    for future in concurrent.futures.as_completed(future_to_index):
                        index = future_to_index[future]
                        try:
                            iteration_results[index] = future.result()
                        except Exception as exc:
                            print(f'Task {index} in iteration {iteration} generated an exception: {exc}')
                            # print the traceback
                            import traceback
                            print(traceback.format_exc())
                            iteration_results[index] = None
                    
                    # Add this iteration's results to the overall list
                    all_results.extend(iteration_results)
        
        return all_results
    
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
    
    # Multiple executions (with n_parallel parameter) - now runs in parallel!
    print("Running 5 parallel executions...")
    start_time = time.time()
    multiple_results = generate_random(n_parallel=5)
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
    multiple_sums = add_numbers(3, 4, n_parallel=3)
    end_time = time.time()
    print(f"Multiple sums: {multiple_sums}")
    print(f"Time taken: {end_time - start_time:.3f} seconds")
    
    # Example 3: Combined parallel and iterative executions
    print("\nRunning combined parallel and iterative executions...")
    print("n_parallel=5, n_iterative=2 (should produce 10 results)...")
    start_time = time.time()
    combined_results = generate_random(n_parallel=5, n_iterative=2)
    end_time = time.time()
    print(f"Combined results: {combined_results}")
    print(f"Number of results: {len(combined_results)}")
    print(f"Time taken: {end_time - start_time:.3f} seconds")


