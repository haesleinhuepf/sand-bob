from IPython.core.magic import register_line_cell_magic

class Context:
    input_host_path: str = None
    dependencies: list = []
    n_attempts: int = 3

@register_line_cell_magic
def bob(line, cell=None):
    from sand_bob._code_gen import generate_and_optimize_code
    from IPython.display import display

    user_input = combine_user_input(line, cell)
    res = generate_and_optimize_code(user_input,
                                     dependencies=Context.dependencies,
                                     input_host_path=Context.input_host_path)
    print("="*100)
    display(res)


def initialize(input_host_path: str=None, 
               dependencies: list=["scikit-image", "numpy", "pandas", "matplotlib", "seaborn", "tqdm", "scipy"], 
               n_attempts: int=3):
    Context.input_host_path = input_host_path
    Context.dependencies = dependencies
    Context.n_attempts = n_attempts


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

