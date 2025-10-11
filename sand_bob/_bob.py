from IPython.core.magic import register_line_cell_magic

class Context:
    input_host_path: str = None
    dependencies: list = []
    n_codefix_attempts: int = 1
    n_feedback_iterations: int = 1
    n_parallel: int = 1
    n_iterative: int = 1
    initial_temperature: float = None
    delta_temperature: float = 0.4

@register_line_cell_magic
def alice(line, cell=None):
    from sand_bob._code_gen import generate_code
    from IPython.display import display

    user_input = combine_user_input(line, cell)
    res = generate_code(user_input,
                                     dependencies=Context.dependencies,
                                     input_host_path=Context.input_host_path,
                        n_codefix_attempts=Context.n_codefix_attempts,
                        n_feedback_iterations = Context.n_feedback_iterations,
                        n_parallel=Context.n_parallel,
                        n_iterative=Context.n_iterative,
                        initial_temperature=Context.initial_temperature,
                        delta_temperature=Context.delta_temperature)
    #print("="*100)
    display(res)


def initialize(input_host_path: str=None, 
               dependencies: list=["scikit-image", "numpy", "pandas", "matplotlib", "seaborn", "tqdm", "scipy"], 
               n_codefix_attempts: int = 1,
               n_feedback_iterations: int = 1,
               n_parallel: int = 1,
               n_iterative: int = 1,
               initial_temperature: float = None,
               delta_temperature: float = 0.4):
    Context.input_host_path = input_host_path
    Context.dependencies = dependencies
    Context.n_codefix_attempts = n_codefix_attempts
    Context.n_feedback_iterations = n_feedback_iterations
    Context.n_parallel = n_parallel
    Context.n_iterative = n_iterative
    Context.initial_temperature = initial_temperature
    Context.delta_temperature = delta_temperature


def combine_user_input(line, cell):
    if line and cell:
        user_input = line + "\n" + cell
    elif line:
        user_input = line
    elif cell:
        user_input = cell
    else:
        user_input = None
    return user_input

