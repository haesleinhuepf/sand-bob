import json


def test_system_prompt_code_generation_is_configurable():
    from sand_bob._code_gen import system_prompt_code_generation
    from sand_bob._config import config

    original_template = config.prompt_template_code_generation
    try:
        config.prompt_template_code_generation = (
            "Allowed dependencies: {dependencies_str}\n"
            "Output path: {display_output_path}"
        )
        prompt = system_prompt_code_generation("/tmp/out", ["numpy", "pandas"])
        assert prompt == "Allowed dependencies: numpy, pandas\nOutput path: /tmp/out"
    finally:
        config.prompt_template_code_generation = original_template


def test_system_prompt_code_feedback_is_configurable():
    from sand_bob._code_gen import system_prompt_code_feedback
    from sand_bob._config import config

    original_template = config.prompt_template_code_feedback
    try:
        config.prompt_template_code_feedback = "Feedback output: {display_output_path}"
        prompt = system_prompt_code_feedback("/tmp/out")
        assert prompt == "Feedback output: /tmp/out"
    finally:
        config.prompt_template_code_feedback = original_template


def test_determine_missing_dependencies_prompt_is_configurable():
    from sand_bob._code_gen import determine_missing_dependencies
    from sand_bob._config import config

    original_template = config.prompt_template_determine_missing_dependencies
    original_prompt_function = config.prompt_function_determine_dependencies
    try:
        captured_prompt = {"value": None}

        config.prompt_template_determine_missing_dependencies = (
            "CODE={code}\nOUT={stdout}\nERR={stderr}"
        )
        config.prompt_function_determine_dependencies = (
            lambda prompt: captured_prompt.update(value=prompt) or "[]"
        )
        dependencies = determine_missing_dependencies("print(1)", "ok", "nope")
        assert dependencies == []
        assert captured_prompt["value"] == "CODE=print(1)\nOUT=ok\nERR=nope"
    finally:
        config.prompt_template_determine_missing_dependencies = original_template
        config.prompt_function_determine_dependencies = original_prompt_function


def test_fix_error_in_code_prompt_is_configurable():
    from sand_bob._code_gen import fix_error_in_code
    from sand_bob._config import config

    original_template = config.prompt_template_fix_error_in_code
    original_prompt_function = config.prompt_function_fix_code
    try:
        config.prompt_template_fix_error_in_code = (
            "CODE={code}\nOUT={stdout}\nERR={stderr}"
        )
        config.prompt_function_fix_code = lambda prompt: "print('fixed')"
        new_code, prompt = fix_error_in_code("print(1)", "ok", "nope")
        assert new_code == "print('fixed')"
        assert prompt == "CODE=print(1)\nOUT=ok\nERR=nope"
    finally:
        config.prompt_template_fix_error_in_code = original_template
        config.prompt_function_fix_code = original_prompt_function


def test_python_code_to_beautiful_notebook_returns_valid_json():
    """Test that python_code_to_beautiful_notebook result is valid JSON"""
    from sand_bob._code_gen import python_code_to_beautiful_notebook

    code = """

# Load the image file
image = imread('input_data/blobs.tif')

# Preprocess the image to reduce dimensionality and noise
image_gray = image
image_resized = np.array(Image.fromarray(image_gray).resize((100, 100)))

# Load the pre-trained Cellpose model
model = models.CellposeModel(gpu=False)

# Perform segmentation with flow threshold and cellprob_threshold set to None
masks, flows, styles = model.eval(image_resized, batch_size=32,
                                  flow_threshold=None,
                                  cellprob_threshold=None)

# Display the segmented labels
stackview.insight(masks)
"""
    
    result = python_code_to_beautiful_notebook(code).code
    
    # Verify result is a valid JSON string
    parsed = json.loads(result)
    assert isinstance(parsed, (dict, list))
