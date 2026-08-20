import os

SANDBOB_LLM_SERVER = os.environ.get('SANDBOB_LLM_SERVER', "http://localhost:11434/v1")
SANDBOB_LLM_API_KEY = os.environ.get('SANDBOB_LLM_API_KEY', "none")

def prompt_ollama(message:str, model="gpt-oss:20b"):
    return prompt(message, model=model, base_url="http://localhost:11434/v1", api_key="none")

def prompt(message:str, model="gpt-oss:20b", base_url=SANDBOB_LLM_SERVER, api_key=SANDBOB_LLM_API_KEY):
    """A prompt helper function that sends a message to ollama and returns only the text response."""
    import openai
    
    if isinstance(message, str):
        message = [{"role": "user", "content": message}]
        
    # setup connection to the LLM
    client = openai.OpenAI(base_url=base_url, api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=message
    )

    # extract answer
    result = response.choices[0].message.content
    if "</thinking>" in result:
        result = result.split("</thinking>")[1]
    return result


def prompt_scadsai_llm(message:str, model="openai/gpt-oss-120b"):
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



def prompt_blablador(message:str, model="alias-fast"):
    """A prompt helper function that sends a message to Helmholtz Blablador
    and returns only the text response.
    """
    import os
    import openai
    
    # convert message in the right format if necessary
    if isinstance(message, str):
        message = [{"role": "user", "content": message}]
    
    # setup connection to the LLM
    client = openai.OpenAI(base_url="https://api.blablador.fz-juelich.de/v1/",
                           api_key=os.environ.get('BLABLADOR_API_KEY')
    )
    response = client.chat.completions.create(
        model=model,
        messages=message
    )
    
    # extract answer
    return response.choices[0].message.content


def prompt_kiara(message:str, model="openai/gpt-oss-120b"):
    
    """A prompt helper function that sends a message to Kiara LLM server at 
    University of Leipzig and returns only the text response.
    """
    import os
    import openai
    
    # convert message in the right format if necessary
    if isinstance(message, str):
        message = [{"role": "user", "content": message}]
    
    # setup connection to the LLM
    client = openai.OpenAI(base_url="https://kiara.sc.uni-leipzig.de/api/",
                           api_key=os.environ.get('KIARA_API_KEY')
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



