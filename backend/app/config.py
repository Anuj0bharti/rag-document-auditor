from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "sqlite:///./data/auditor.db"
    qdrant_url: str = ""
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_provider: str = "local"
    llm_mode: str = "mock"
    jwt_secret: str = "development-only-change-me"
    upload_dir: str = "./uploads"
    max_file_size_mb: int = 25
    cors_origins: str = "http://localhost:3000"
    chunk_size: int = 900
    chunk_overlap: int = 150

    @property
    def upload_path(self) -> Path:
        path = Path(self.upload_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path


settings = Settings()

