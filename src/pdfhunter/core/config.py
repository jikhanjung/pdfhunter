"""Configuration management for PDFHunter."""

import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# Load .env file from current directory or project root
def _find_dotenv() -> Path | None:
    """Find .env file in current directory or parent directories."""
    current = Path.cwd()
    for _ in range(5):  # Check up to 5 levels
        env_file = current / ".env"
        if env_file.exists():
            return env_file
        if current.parent == current:
            break
        current = current.parent
    return None


# Load .env file
_env_file = _find_dotenv()
if _env_file:
    load_dotenv(_env_file)


class OCRConfig(BaseModel):
    """OCR-related configuration."""

    engine: Literal["paddleocr", "tesseract"] = "paddleocr"
    languages: list[str] = Field(default_factory=lambda: ["en", "fr", "ru"])
    low_dpi: int = 150
    high_dpi: int = 300
    confidence_threshold: float = 0.75


class ExtractionConfig(BaseModel):
    """Extraction-related configuration."""

    # Pages to always process for scanned PDFs
    default_pages_ocr: list[str] = Field(
        default_factory=lambda: ["first", "second", "last"]
    )
    # Pages to always process for text PDFs
    default_pages_text: list[str] = Field(
        default_factory=lambda: ["first", "second", "third", "last"]
    )
    # Maximum pages to process in expansion loop
    max_expansion_pages: int = 5
    # Maximum agent loop iterations
    max_agent_iterations: int = 3


class LLMConfig(BaseModel):
    """LLM-related configuration."""

    provider: Literal["openai", "anthropic"] = "openai"
    model: str = "gpt-4o-mini"
    temperature: float = 0.0
    max_tokens: int = 2000


class Config(BaseSettings):
    """Main configuration for PDFHunter.

    Loads settings from environment variables and .env file.
    Environment variable names are prefixed with PDFHUNTER_ or use standard names.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API Keys (loaded from environment)
    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    anthropic_api_key: str | None = Field(default=None, validation_alias="ANTHROPIC_API_KEY")

    # Sub-configs
    ocr: OCRConfig = Field(default_factory=OCRConfig)
    extraction: ExtractionConfig = Field(default_factory=ExtractionConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)

    # Output directories
    records_dir: Path = Path("data/records")
    evidence_dir: Path = Path("data/evidence")

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    @classmethod
    def load(cls, path: Path | None = None) -> "Config":
        """Load configuration from file or return defaults.

        API keys are always loaded from environment variables/.env file.
        """
        if path and path.exists():
            import json
            data = json.loads(path.read_text())
            return cls(**data)
        return cls()

    def get_api_key(self, provider: str | None = None) -> str | None:
        """Get API key for the specified or configured provider."""
        provider = provider or self.llm.provider
        if provider == "openai":
            return self.openai_api_key or os.getenv("OPENAI_API_KEY")
        elif provider == "anthropic":
            return self.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        return None
