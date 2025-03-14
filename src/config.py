from functools import lru_cache
from pydantic import BaseSettings

class Settings(BaseSettings):
    openrouter_api_key: str = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    
    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

@lru_cache()
def get_settings() -> Settings:
    return Settings()
