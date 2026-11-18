from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url_readonly: str
    database_url_backend: str
    openai_api_key: str
    openai_model: str = "gpt-4.1-mini"
    cors_origins: str = "http://localhost:5173"
    demo_mode: str = "live"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def origins(self):
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]
