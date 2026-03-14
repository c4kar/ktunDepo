"""
ktunDepo Agent — Configuration Loader
YAML config dosyasını yükleyen ve doğrulayan modül.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
import yaml
from dotenv import load_dotenv

from agent.logging_config import get_logger

logger = get_logger("config")


class ConfigurationError(Exception):
    """Yapılandırma hatası."""

    pass


class Config:
    """
    Agent yapılandırmasını yöneten sınıf.
    config.yaml ve .env dosyalarını birleştirir.
    """

    def __init__(self, config_path: str = "agent/config.yaml"):
        """
        Config başlat.

        Args:
            config_path: config.yaml dosya yolu
        """
        self.config_path = Path(config_path)
        self._config: Dict[str, Any] = {}
        self._load_env()
        self._load_config()
        self._validate_config()

    def _load_env(self) -> None:
        """Ortam değişkenlerini yükle."""
        # Önce .env dosyasını bul
        env_paths = [
            Path(".env"),
            Path(".env.local"),
            Path(__file__).parent.parent / ".env",
        ]

        for env_path in env_paths:
            if env_path.exists():
                load_dotenv(env_path)
                logger.debug(f".env yüklendi: {env_path}")
                break
        else:
            logger.warning(".env dosyası bulunamadı")

    def _load_config(self) -> None:
        """YAML config dosyasını yükle."""
        try:
            if not self.config_path.exists():
                raise ConfigurationError(
                    f"Config dosyası bulunamadı: {self.config_path}"
                )

            with open(self.config_path, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f)

            logger.info(f"Config yüklendi: {self.config_path}")
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Config dosyası parse edilemedi: {e}")

    def _validate_config(self) -> None:
        """Config değerlerini doğrula."""
        required_sections = ["quality", "duplicate_detection", "telegram", "paths"]

        for section in required_sections:
            if section not in self._config:
                raise ConfigurationError(f"Eksik config bölümü: {section}")

        # Kritik ortam değişkenlerini kontrol et
        if not self.telegram_bot_token:
            logger.warning("TELEGRAM_BOT_TOKEN ayarlanmamış")

        if not self.openrouter_api_key:
            logger.warning("OPENROUTER_API_KEY ayarlanmamış")

    # --- Quality Settings ---

    @property
    def reject_threshold(self) -> int:
        return self._config.get("quality", {}).get("reject_threshold", 30)

    @property
    def llm_threshold(self) -> int:
        return self._config.get("quality", {}).get("llm_threshold", 60)

    @property
    def manual_review(self) -> bool:
        return self._config.get("quality", {}).get("manual_review", False)

    @property
    def min_file_size_kb(self) -> int:
        return self._config.get("quality", {}).get("min_file_size_kb", 50)

    @property
    def max_file_size_mb(self) -> int:
        return self._config.get("quality", {}).get("max_file_size_mb", 200)

    @property
    def min_pages(self) -> int:
        return self._config.get("quality", {}).get("min_pages", 2)

    @property
    def supported_extensions(self) -> list:
        return self._config.get("quality", {}).get(
            "supported_extensions", [".pdf", ".pptx", ".docx"]
        )

    # --- Duplicate Detection ---

    @property
    def reject_similarity(self) -> float:
        return self._config.get("duplicate_detection", {}).get(
            "reject_similarity", 0.92
        )

    @property
    def warn_similarity(self) -> float:
        return self._config.get("duplicate_detection", {}).get("warn_similarity", 0.75)

    @property
    def check_pages(self) -> int:
        return self._config.get("duplicate_detection", {}).get("check_pages", 3)

    # --- OCR Settings ---

    @property
    def ocr_engine(self) -> str:
        return self._config.get("ocr", {}).get("engine", "docling")

    @property
    def ocr_language(self) -> str:
        return self._config.get("ocr", {}).get("language", "tr")

    @property
    def format_model(self) -> str:
        return self._config.get("ocr", {}).get(
            "format_model", "claude-sonnet-4-20250514"
        )

    # --- Docling Settings ---

    @property
    def docling_enabled(self) -> bool:
        return bool(self._config.get("docling", {}).get("enabled", True))

    @property
    def docling_mode(self) -> str:
        return str(self._config.get("docling", {}).get("mode", "enforce")).lower()

    @property
    def docling_min_extracted_chars(self) -> int:
        return int(self._config.get("docling", {}).get("min_extracted_chars", 180))

    @property
    def docling_optimize_pdf_over_mb(self) -> float:
        return float(self._config.get("docling", {}).get("optimize_pdf_over_mb", 20))

    @property
    def docling_optimize_min_saving_percent(self) -> float:
        return float(
            self._config.get("docling", {}).get("optimize_min_saving_percent", 20)
        )

    @property
    def docling_optimize_max_pages(self) -> int:
        return int(self._config.get("docling", {}).get("optimize_max_pages", 120))

    @property
    def docling_optimize_dpi(self) -> int:
        return int(self._config.get("docling", {}).get("optimize_dpi", 150))

    @property
    def docling_optimize_jpeg_quality(self) -> int:
        return int(self._config.get("docling", {}).get("optimize_jpeg_quality", 60))

    # --- LLM Settings ---

    @property
    def llm_quality_model(self) -> str:
        return self._config.get("llm", {}).get(
            "quality_model", "anthropic/claude-3-haiku-20240307"
        )

    @property
    def llm_fallback_model(self) -> str:
        return self._config.get("llm", {}).get("fallback_model", "openai/gpt-4o-mini")

    @property
    def llm_timeout(self) -> int:
        return int(self._config.get("llm", {}).get("timeout_seconds", 30))

    # --- Embedding Settings ---

    @property
    def embedding_model(self) -> str:
        return self._config.get("embedding", {}).get(
            "model", "intfloat/multilingual-e5-large"
        )

    @property
    def embedding_batch_size(self) -> int:
        return self._config.get("embedding", {}).get("batch_size", 32)

    # --- Git Settings ---

    @property
    def git_auto_commit(self) -> bool:
        return self._config.get("git", {}).get("auto_commit", True)

    @property
    def git_branch(self) -> str:
        return self._config.get("git", {}).get("branch", "main")

    # --- Telegram Settings ---

    @property
    def daily_upload_limit(self) -> int:
        return self._config.get("telegram", {}).get("daily_upload_limit", 10)

    @property
    def hourly_group_limit(self) -> int:
        return self._config.get("telegram", {}).get("hourly_group_limit", 30)

    @property
    def allowed_material_types(self) -> list:
        return self._config.get("telegram", {}).get(
            "allowed_material_types",
            ["Ders Notu", "Sınav Sorusu", "Sunum", "Özet", "Diğer"],
        )

    # --- Paths ---

    @property
    def incoming_path(self) -> str:
        return self._config.get("paths", {}).get("incoming", "_incoming")

    @property
    def vector_db_path(self) -> str:
        return self._config.get("paths", {}).get("vector_db", "vector_db")

    @property
    def logs_path(self) -> str:
        return self._config.get("paths", {}).get("logs", "agent/logs")

    @property
    def prompts_path(self) -> str:
        return self._config.get("paths", {}).get("prompts", "agent/prompts")

    # --- Logging ---

    @property
    def log_level(self) -> str:
        return self._config.get("logging", {}).get("level", "INFO")

    @property
    def max_log_size_mb(self) -> int:
        return self._config.get("logging", {}).get("max_log_size_mb", 50)

    @property
    def log_retention_days(self) -> int:
        return self._config.get("logging", {}).get("retention_days", 30)

    # --- Environment Variables ---

    @property
    def telegram_bot_token(self) -> Optional[str]:
        return os.getenv("TELEGRAM_BOT_TOKEN")

    @property
    def admin_chat_id(self) -> Optional[str]:
        return os.getenv("ADMIN_CHAT_ID")

    @property
    def group_chat_id(self) -> Optional[str]:
        return os.getenv("GROUP_CHAT_ID")

    @property
    def openrouter_api_key(self) -> Optional[str]:
        return os.getenv("OPENROUTER_API_KEY")

    @property
    def qdrant_host(self) -> str:
        return os.getenv("QDRANT_HOST", "localhost")

    @property
    def qdrant_port(self) -> int:
        return int(os.getenv("QDRANT_PORT", "6333"))

    @property
    def qdrant_api_key(self) -> Optional[str]:
        return os.getenv("QDRANT_API_KEY")

    @property
    def github_token(self) -> Optional[str]:
        return os.getenv("GITHUB_TOKEN")

    @property
    def agent_base_path(self) -> str:
        return os.getenv("AGENT_BASE_PATH", os.getcwd())

    # --- Helpers ---

    def get(self, key: str, default: Any = None) -> Any:
        """Nokta notasyonu ile nested config değeri al."""
        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default

            if value is None:
                return default

        return value

    def to_dict(self) -> Dict[str, Any]:
        """Tüm config'i dict olarak döndür."""
        return self._config.copy()


# Singleton instance
_config: Optional[Config] = None


def get_config(config_path: str = "agent/config.yaml") -> Config:
    """
    Global Config instance döndür (singleton pattern).

    Args:
        config_path: config.yaml dosya yolu

    Returns:
        Config instance
    """
    global _config
    if _config is None:
        _config = Config(config_path)
    return _config
