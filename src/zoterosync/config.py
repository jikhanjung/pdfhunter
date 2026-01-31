"""Configuration for ZoteroSync."""

from pathlib import Path

from pydantic_settings import BaseSettings


class ZoteroSyncConfig(BaseSettings):
    """Zotero sync configuration, loaded from environment variables."""

    zotero_api_key: str = ""
    zotero_library_id: str = ""
    zotero_library_type: str = "user"  # "user" or "group"
    zotero_data_dir: Path = Path("data/zotero")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    @property
    def db_path(self) -> Path:
        return self.zotero_data_dir / "zotero.db"
