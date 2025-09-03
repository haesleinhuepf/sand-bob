
def prompt_ollama(message:str, model="gpt-oss:20b"):
    """A prompt helper function that sends a message to ollama and returns only the text response."""
    import openai
    
    if isinstance(message, str):
        message = [{"role": "user", "content": message}]
        
    # setup connection to the LLM
    client = openai.OpenAI()
    client.base_url = "http://localhost:11434/v1"
    client.api_key = "none"
    response = client.chat.completions.create(
        model=model,
        messages=message
    )

    print("OLLAMA model: ", model)
    
    # extract answer
    result = response.choices[0].message.content
    print(result)
    if "</thinking>" in result:
        result = result.split("</thinking>")[1]
    return result


def prompt_scadsai_llm(message:str, model="openai/gpt-oss-120b"):
#def prompt_scadsai_llm(message:str, model="meta-llama/Llama-3.3-70B-Instruct"):
#def prompt_scadsai_llm(message:str, model="deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct"):
    """A prompt helper function that sends a message to ScaDS.AI LLM server at 
    ZIH TU Dresden and returns only the text response.
    """
    import os
    import openai
    
    # convert message in the right format if necessary
    if isinstance(message, str):
        message = [{"role": "user", "content": message}]
    
    # setup connection to the LLM
    client = openai.OpenAI(base_url="https://llm.scads.ai/v1",
                           api_key=os.environ.get('SCADSAI_API_KEY')
    )
    response = client.chat.completions.create(
        model=model,
        messages=message
    )
    
    # extract answer
    return response.choices[0].message.content


def prompt_openai(message:str, model="gpt-5-mini"):
    """A prompt helper function that sends a message to openAI
    and returns only the text response.
    """
    import openai
    
    # convert message in the right format if necessary
    if isinstance(message, str):
        message = [{"role": "user", "content": message}]
        
    # setup connection to the LLM
    client = openai.OpenAI()
    
    # submit prompt
    response = client.chat.completions.create(
        model=model,
        messages=message
    )
    
    # extract answer
    return response.choices[0].message.content


def prompt_kisski(message:str, model="openai-gpt-oss-120b"):
    """A prompt helper function that sends a message to LLM server of
    KISSKI / GWDG and returns only the text response.
    """
    import os
    import openai
    
    # convert message in the right format if necessary
    if isinstance(message, str):
        message = [{"role": "user", "content": message}]
    
    # setup connection to the LLM
    client = openai.OpenAI(base_url="https://chat-ai.academiccloud.de/v1",
                           api_key=os.environ.get('KISSKI_API_KEY')
    )
    response = client.chat.completions.create(
        model=model,
        messages=message
    )
    
    # extract answer
    return response.choices[0].message.content



