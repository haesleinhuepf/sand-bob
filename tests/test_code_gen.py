import json

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
