"""Application configuration loaded from environment variables."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "AutoResearcher"
    app_version: str = "0.1.0"
    debug: bool = False

    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o"
    tavily_api_key: str = ""

    chromadb_host: str = "chromadb"
    chromadb_port: int = 8001

    cors_origins: list[str] = ["http://localhost:3000"]

    max_concurrent_research: int = 3
    use_mock: bool = False

    checkpoint_db_path: str = "./data/checkpoints.db"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
