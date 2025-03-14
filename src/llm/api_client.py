from tenacity import retry, wait_exponential, stop_after_attempt
import httpx
from config import get_settings
import logging

logger = logging.getLogger(__name__)

class OpenRouterClient:
    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.openrouter_base_url
        self.headers = {
            "Authorization": f"Bearer {self.settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://crawl4ai.com",
            "X-Title": "Crawl4AI LLM Integration"
        }
        
    @retry(
        wait=wait_exponential(multiplier=1, min=4, max=10),
        stop=stop_after_attempt(3),
        reraise=True
    )
    async def chat_completion(self, prompt: str, model: str = "openai/gpt-3.5-turbo", **kwargs) -> str:
        """
        Execute LLM request with exponential backoff retry
        """
        if not self.settings.openrouter_api_key:
            logger.error("OpenRouter API key not configured")
            raise ValueError("OpenRouter API credentials missing")

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": kwargs.get("temperature", 0.1),
            "max_tokens": kwargs.get("max_tokens", 1000)
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=self.headers,
                timeout=30
            )
            
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
