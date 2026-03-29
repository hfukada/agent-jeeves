from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://jeeves:jeeves@localhost:5432/jeeves"
    chroma_host: str = "localhost"
    chroma_port: int = 8000
    ollama_base_url: str = "http://localhost:11434"
    github_token: str = ""

    model_config = {"env_file": ".env"}


settings = Settings()
