def prompt_scadsai_llm(message:str, model="meta-llama/Llama-3.3-70B-Instruct"):
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

def prompt_openai(message:str, model="gpt-4.1-2025-04-14"):
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