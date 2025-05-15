from openai import OpenAI
import os

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
def query_openrouter(prompt: str, api_key: str, max_length: int = 500, model: str = "meta-llama/llama-4-maverick:free", logger = None) -> str:
    print(api_key)
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key
    )
    completion = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}]
    )
    try:
        logger.info("Completion choice Message", completion.choices[0].message.content)
        logger.info("Completion choice Finish Reason", completion.choices[0].finish_reason)
        return completion.choices[0].message.content
    except Exception as e:
        logger.error("api call to llm error", completion.error['message'])
        return ""