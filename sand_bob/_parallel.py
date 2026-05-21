import functools
import concurrent.futures
import copy
import threading
from typing import Callable, Any, List, Union
from ._statusdisplay import StatusDisplay

def parallel(func: Callable) -> Callable:
    """
    A decorator that executes a function either once or multiple times based on the 'n_parallel' and 'n_iterative' parameters.
    
    When calling the decorated function:
    - If no parameters are passed: executes once and returns the result directly
    - If 'n_parallel' parameter is passed: executes 'n_parallel' times in parallel and returns a list of results
    - If 'n_iterative' parameter is passed: executes 'n_iterative' times sequentially and returns a list of results
    - If both 'n_parallel' and 'n_iterative' are passed: executes a total of 'n_parallel * n_iterative' times with
      continuous execution (new executions start as soon as parallel slots become available), returning a flat list
    
    Features:
    - Shows a StatusDisplay progress bar for multiple executions (in Jupyter notebooks)
    - Continuous execution: when both n_parallel and n_iterative are specified, new executions start immediately
      when previous ones complete, rather than waiting for all parallel executions in an iteration to finish
    - Thread-safe execution with proper error handling
    - Results are returned in execution order (not completion order)
    
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
        
        # Combined parallel and iterative executions with continuous execution
        results = random_number(n_parallel=3, n_iterative=4)  # Returns a flat list of 12 numbers
        # New executions start as soon as parallel slots become available
    """
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Union[Any, List[Any]]:
        # Extract parameters
        n_parallel = kwargs.pop('n_parallel', None)
        n_iterative = kwargs.pop('n_iterative', None)
        vary_algorithm = kwargs.pop('vary_algorithm', False)
        
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
        
        total_executions = n_parallel * n_iterative
        
        # Initialize status display if we have multiple executions
        status_display = None
        if total_executions > 1:
            status_display = StatusDisplay(
                total_steps=total_executions, 
                status_text=f"Process 0/{total_executions} completed",
                color="#2EB870"
            )
        
        # Combined parallel and iterative execution with continuous execution
        return _execute_parallel_iterative(func, args, kwargs, n_parallel, n_iterative, status_display, vary_algorithm=vary_algorithm)
    
    return wrapper




def _execute_parallel_iterative(func, args, kwargs, n_parallel, n_iterative, status_display, vary_algorithm=False):
    """Execute function with both parallel and iterative execution.
    
    This starts new iterative executions as soon as parallel slots become available,
    rather than waiting for all parallel executions in an iteration to complete.
    """
    from ._code_gen import summarize_code

    total_executions = n_parallel * n_iterative
    all_results = [None] * total_executions
    completed_count = 0
    next_execution_id = 0
    
    # Use a lock to protect shared state
    lock = threading.Lock()
    
    def execute_and_track(execution_id, summaries=None):
        nonlocal completed_count
        try:
            kwargs_copy = copy.deepcopy(kwargs)
            if vary_algorithm:    
                for k, v  in (kwargs_copy.items()):
                    if k == "prompt":
                        kwargs_copy[k] = f"{v}\n\nTry to avoid these algorithms: \n{summaries}"
                        break

            result = func(*copy.deepcopy(args), **kwargs_copy)
            if vary_algorithm:
                result.summary = summarize_code(result.code)
            with lock:
                all_results[execution_id] = result
                completed_count += 1
                if status_display:
                    status_display.status_text = f"Process {completed_count}/{total_executions} completed"
                    status_display.add_progress(1)
            return result
        except Exception as exc:
            print(f'Execution {execution_id} generated an exception: {exc}')
            import traceback
            print(traceback.format_exc())
            with lock:
                all_results[execution_id] = None
                completed_count += 1
                if status_display:
                    status_display.status_text = f"Process {completed_count}/{total_executions} completed"
                    status_display.add_progress(1)
            return None
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=n_parallel) as executor:
        # Submit initial batch of parallel executions
        active_futures = {}
        
        # Submit initial n_parallel tasks
        for i in range(min(n_parallel, total_executions)):
            future = executor.submit(execute_and_track, next_execution_id)
            active_futures[future] = next_execution_id
            next_execution_id += 1
        
        # As tasks complete, submit new ones
        while active_futures:
            # Wait for at least one task to complete
            done_futures = set()
            for future in concurrent.futures.as_completed(active_futures):
                done_futures.add(future)
                
                # Remove completed future
                del active_futures[future]
                
                # Submit a new task if we haven't submitted all yet
                if next_execution_id < total_executions:
                    new_future = executor.submit(execute_and_track, next_execution_id)
                    active_futures[new_future] = next_execution_id
                    next_execution_id += 1
                
                # Only process one completion at a time to avoid overwhelming
                break
    status_display.update("")
    return all_results


def collect_summaries(results):
    """Collect summaries from a list of results, handling None values."""
    summaries = []
    for result in results:
        if result is not None and hasattr(result, 'summary'):
            summaries.append(result.summary)
        else:
            summaries.append(None)
    return summaries


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
    print("\nRunning 5 parallel executions...")
    start_time = time.time()
    multiple_results = generate_random(n_parallel=5)
    end_time = time.time()
    print(f"Multiple results: {multiple_results}")
    print(f"Time taken: {end_time - start_time:.3f} seconds")
    
    # Multiple iterative executions
    print("\nRunning 3 iterative executions...")
    start_time = time.time()
    iterative_results = generate_random(n_iterative=3)
    end_time = time.time()
    print(f"Iterative results: {iterative_results}")
    print(f"Time taken: {end_time - start_time:.3f} seconds")
    
    # Example 2: Function with parameters
    @parallel
    def add_numbers(a, b):
        time.sleep(0.1)  # Simulate some work
        return a + b
    
    # Single execution
    single_sum = add_numbers(3, 4)
    print(f"\nSingle sum: {single_sum}")
    
    # Multiple executions - runs in parallel
    print("Running 3 parallel additions...")
    start_time = time.time()
    multiple_sums = add_numbers(3, 4, n_parallel=3)
    end_time = time.time()
    print(f"Multiple sums: {multiple_sums}")
    print(f"Time taken: {end_time - start_time:.3f} seconds")
    
    # Example 3: Combined parallel and iterative executions with continuous execution
    print("\nRunning combined parallel and iterative executions...")
    print("n_parallel=3, n_iterative=4 (should produce 12 results)...")
    print("New executions start as soon as previous ones complete...")
    start_time = time.time()
    combined_results = generate_random(n_parallel=3, n_iterative=4)
    end_time = time.time()
    print(f"Combined results: {combined_results}")
    print(f"Number of results: {len(combined_results)}")
    print(f"Time taken: {end_time - start_time:.3f} seconds")
    
    # Example 4: Demonstrate the continuous execution behavior
    @parallel
    def slow_function(task_id):
        # Simulate variable execution times
        sleep_time = random.uniform(0.1, 0.5)
        time.sleep(sleep_time)
        print(f"Task {task_id} completed after {sleep_time:.2f}s")
        return f"Result_{task_id}"
    
    print("\nDemonstrating continuous execution with variable times...")
    print("Watch how new tasks start as others complete...")
    start_time = time.time()
    continuous_results = slow_function("test", n_parallel=2, n_iterative=3)
    end_time = time.time()
    print(f"Continuous results: {continuous_results}")
    print(f"Total time: {end_time - start_time:.3f} seconds")


