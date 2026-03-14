"""
ktunDepo Agent — Logging Modülü
Merkezi loglama sistemi için yardımcı fonksiyonlar.
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from loguru import logger


# Config'den log ayarlarını oku
def setup_logging(
    log_level: str = "INFO",
    log_dir: str = "agent/logs",
    max_size_mb: int = 50,
    retention_days: int = 30,
) -> None:
    """
    Loguru logger'ı yapılandır.

    Args:
        log_level: Log seviyesi (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Log dosyalarının saklanacağı klasör
        max_size_mb: Maksimum log dosyası boyutu (MB)
        retention_days: Log saklama süresi (gün)
    """
    # Log klasörünü oluştur
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Varsayılan handler'ı kaldır
    logger.remove()

    # Konsol handler (renkli çıktı)
    logger.add(
        sys.stderr,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>",
        colorize=True,
    )

    # Dosya handler - genel log
    logger.add(
        log_path / "agent_{time:YYYY-MM-DD}.log",
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        rotation=f"{max_size_mb} MB",
        retention=f"{retention_days} days",
        compression="zip",
        encoding="utf-8",
    )

    # Ayrı hata log dosyası
    logger.add(
        log_path / "errors_{time:YYYY-MM-DD}.log",
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}\n{exception}",
        rotation=f"{max_size_mb} MB",
        retention=f"{retention_days} days",
        compression="zip",
        encoding="utf-8",
    )

    logger.info(f"Logging sistemi başlatıldı | Seviye: {log_level} | Klasör: {log_dir}")


def get_logger(name: str = "ktunDepo"):
    """
    İsimlendirilmiş logger döndür.

    Args:
        name: Logger adı (modül adı olarak kullanılır)

    Returns:
        Yapılandırılmış logger instance
    """
    return logger.bind(name=name)


# Event logging için özel fonksiyonlar
def log_event(event_type: str, details: dict) -> None:
    """
    Agent event'ini logla.

    Args:
        event_type: Event türü (telegram_upload, file_processed, git_push, vb.)
        details: Event detayları
    """
    event_logger = get_logger("events")
    event_logger.info(f"EVENT: {event_type} | {details}")


def log_material_decision(
    material_path: str, decision: str, reason: str, score: Optional[int] = None
) -> None:
    """
    Materyal kabul/red kararını logla.

    Args:
        material_path: Materyal dosya yolu
        decision: Karar (ACCEPTED, REJECTED, DUPLICATE, PENDING_LLM)
        reason: Karar sebebi
        score: Kalite skoru (varsa)
    """
    decision_logger = get_logger("decisions")
    log_msg = f"MATERYAL: {material_path} | KARAR: {decision} | SEBEP: {reason}"
    if score is not None:
        log_msg += f" | SKOR: {score}"

    if decision == "ACCEPTED":
        decision_logger.success(log_msg)
    elif decision == "REJECTED":
        decision_logger.warning(log_msg)
    else:
        decision_logger.info(log_msg)


def log_maintenance(reason: str, error_details: Optional[str] = None) -> None:
    """
    Bakım modu geçişini logla.

    Args:
        reason: Bakım sebebi
        error_details: Hata detayları (varsa)
    """
    maint_logger = get_logger("maintenance")
    maint_logger.critical(f"BAKIM MODU: {reason}")
    if error_details:
        maint_logger.critical(f"HATA DETAYI: {error_details}")


def log_token_usage(operation: str, tokens_used: int) -> None:
    """
    Token kullanımını logla (maliyet takibi için).

    Args:
        operation: İşlem adı
        tokens_used: Kullanılan token sayısı
    """
    token_logger = get_logger("tokens")
    token_logger.debug(f"TOKEN: {operation} | {tokens_used} token kullanıldı")


# Modül yüklendiğinde varsayılan ayarlarla başlat
if __name__ != "__main__":
    # Import edildiğinde henüz setup çağırma,
    # ana modül config'den okuyup çağıracak
    pass
