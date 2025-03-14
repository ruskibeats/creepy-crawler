from functools import lru_cache

try:
    from pydantic_settings import BaseSettings
    
    class Settings(BaseSettings):
        openrouter_api_key: str = None
        openrouter_base_url: str = "https://openrouter.ai/api/v1"
        default_model: str = "mistralai/ministral-8b"
        analysis_model: str = "mistralai/ministral-8b"
        
        class Config:
            env_file = ".env"
            env_file_encoding = 'utf-8'
except ImportError:
    # Fallback settings class if pydantic_settings is not available
    class Settings:
        def __init__(self):
            self.openrouter_api_key = None
            self.openrouter_base_url = "https://openrouter.ai/api/v1"
            self.default_model = "mistralai/ministral-8b"
            self.analysis_model = "mistralai/ministral-8b"

@lru_cache()
def get_settings() -> Settings:
    return Settings()
