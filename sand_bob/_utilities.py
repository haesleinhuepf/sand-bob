def simplify(text):
    return text.strip().strip("\n").strip()

def extract_code(text):
    if "```python" in text:
        return simplify(text.split("```python")[1].split("```")[0])
    else:
        return simplify(text)
