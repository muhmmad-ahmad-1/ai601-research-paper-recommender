import os
from groq import Groq
import time

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
def query_openrouter(prompt: str, api_key: str, logger = None, max_length: int = 500, model: str = "llama3-8b-8192") -> str:
    client = Groq(api_key=api_key)

    max_retries = 5
    delay = 1  # seconds

    for attempt in range(max_retries):
        try:
            completion = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            logger.info("Completion choice Message", completion.choices[0].message.content)
            logger.info("Completion choice Finish Reason", completion.choices[0].finish_reason)
            return completion.choices[0].message.content
        except Exception as e:
            logger.error(f"Attempt {attempt + 1} failed: {str(e)}")
            time.sleep(delay)
    
    logger.error("All retry attempts failed.")
    return ""