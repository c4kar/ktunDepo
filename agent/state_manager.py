"""
ktunDepo Agent — State Manager
Agent durumunu yöneten modül (sleeping, active, maintenance).
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from enum import Enum

from agent.logging_config import get_logger, log_event

logger = get_logger("state")


class AgentMode(Enum):
    """Agent çalışma modları."""

    SLEEPING = "sleeping"  # Varsayılan — kaynak tüketimi sıfır
    ACTIVE = "active"  # Bir olay tetiklendi, işlem yapılıyor
    MAINTENANCE = "maintenance"  # Kritik hata — admin bildirimi gönderildi


class StateManager:
    """
    Agent state.json dosyasını yöneten sınıf.
    Thread-safe değil — tek process varsayılıyor.
    """

    def __init__(self, state_path: str = "agent/state.json"):
        """
        StateManager başlat.

        Args:
            state_path: state.json dosya yolu
        """
        self.state_path = Path(state_path)
        self._state: Dict[str, Any] = {}
        self._load_state()

    def _load_state(self) -> None:
        """State dosyasını oku."""
        try:
            if self.state_path.exists():
                with open(self.state_path, "r", encoding="utf-8") as f:
                    self._state = json.load(f)
                logger.debug(f"State yüklendi: {self._state.get('mode', 'unknown')}")
            else:
                logger.warning("State dosyası bulunamadı, varsayılan oluşturuluyor")
                self._state = self._default_state()
                self._save_state()
        except json.JSONDecodeError as e:
            logger.error(f"State dosyası bozuk: {e}")
            self._state = self._default_state()
            self._save_state()

    def _default_state(self) -> Dict[str, Any]:
        """Varsayılan state değerleri."""
        return {
            "mode": AgentMode.SLEEPING.value,
            "last_event": None,
            "last_event_type": None,
            "maintenance_reason": None,
            "queue_size": 0,
            "processed_today": 0,
            "rejected_today": 0,
            "token_usage_today": 0,
            "last_health_check": None,
            "uptime_start": None,
            "version": "1.0.0",
            "pending_files": {},  # id -> path mapping
            "review_files": {},  # id -> path mapping
        }

    def _save_state(self) -> None:
        """State dosyasını kaydet."""
        try:
            with open(self.state_path, "w", encoding="utf-8") as f:
                json.dump(self._state, f, indent=2, ensure_ascii=False)
            logger.debug("State kaydedildi")
        except Exception as e:
            logger.error(f"State kaydedilemedi: {e}")

    @property
    def mode(self) -> AgentMode:
        """Mevcut agent modunu döndür."""
        return AgentMode(self._state.get("mode", AgentMode.SLEEPING.value))

    @property
    def is_sleeping(self) -> bool:
        return self.mode == AgentMode.SLEEPING

    @property
    def is_active(self) -> bool:
        return self.mode == AgentMode.ACTIVE

    @property
    def is_maintenance(self) -> bool:
        return self.mode == AgentMode.MAINTENANCE

    def wake_up(self, event_type: str) -> bool:
        """
        Agent'ı uyandır (SLEEPING → ACTIVE).

        Args:
            event_type: Uyandıran event türü

        Returns:
            True eğer başarıyla uyandıysa, False eğer maintenance modundaysa
        """
        if self.is_maintenance:
            logger.warning(
                f"Agent maintenance modunda, uyandırılamıyor. Sebep: {self._state.get('maintenance_reason')}"
            )
            return False

        self._state["mode"] = AgentMode.ACTIVE.value
        self._state["last_event"] = datetime.now().isoformat()
        self._state["last_event_type"] = event_type

        if self._state.get("uptime_start") is None:
            self._state["uptime_start"] = datetime.now().isoformat()

        self._save_state()
        log_event("agent_wake_up", {"event_type": event_type})
        logger.info(f"Agent uyandı: {event_type}")
        return True

    def go_to_sleep(self) -> None:
        """Agent'ı uyut (ACTIVE → SLEEPING)."""
        if not self.is_active:
            logger.debug("Agent zaten uyuyor veya maintenance modunda")
            return

        self._state["mode"] = AgentMode.SLEEPING.value
        self._save_state()
        log_event(
            "agent_sleep", {"processed_today": self._state.get("processed_today", 0)}
        )
        logger.info("Agent uykuya geçti")

    def enter_maintenance(self, reason: str) -> None:
        """
        Bakım moduna geç (→ MAINTENANCE).

        Args:
            reason: Bakım sebebi
        """
        self._state["mode"] = AgentMode.MAINTENANCE.value
        self._state["maintenance_reason"] = reason
        self._state["maintenance_entered"] = datetime.now().isoformat()
        self._save_state()
        log_event("maintenance_entered", {"reason": reason})
        logger.critical(f"BAKIM MODU AKTİF: {reason}")

    def exit_maintenance(self) -> bool:
        """
        Bakım modundan çık (MAINTENANCE → ACTIVE).

        Returns:
            True eğer başarıyla çıkıldıysa
        """
        if not self.is_maintenance:
            logger.warning("Agent maintenance modunda değil")
            return False

        self._state["mode"] = AgentMode.SLEEPING.value
        self._state["maintenance_reason"] = None
        self._state["maintenance_exited"] = datetime.now().isoformat()
        self._save_state()
        log_event("maintenance_exited", {})
        logger.info("Bakım modundan çıkıldı")
        return True

    def increment_processed(self) -> int:
        """İşlenen materyal sayısını artır."""
        self._state["processed_today"] = self._state.get("processed_today", 0) + 1
        self._save_state()
        return self._state["processed_today"]

    def increment_rejected(self) -> int:
        """Reddedilen materyal sayısını artır."""
        self._state["rejected_today"] = self._state.get("rejected_today", 0) + 1
        self._save_state()
        return self._state["rejected_today"]

    def add_token_usage(self, tokens: int) -> int:
        """Token kullanımını ekle."""
        self._state["token_usage_today"] = (
            self._state.get("token_usage_today", 0) + tokens
        )
        self._save_state()
        return self._state["token_usage_today"]

    def update_queue_size(self, size: int) -> None:
        """Kuyruk boyutunu güncelle."""
        self._state["queue_size"] = size
        self._save_state()

    def update_health_check(self) -> None:
        """Son sağlık kontrolü zamanını güncelle."""
        self._state["last_health_check"] = datetime.now().isoformat()
        self._save_state()

    def reset_daily_counters(self) -> None:
        """Günlük sayaçları sıfırla (gece yarısı çağrılır)."""
        self._state["processed_today"] = 0
        self._state["rejected_today"] = 0
        self._state["token_usage_today"] = 0
        self._save_state()
        log_event("daily_reset", {})
        logger.info("Günlük sayaçlar sıfırlandı")

    def add_pending_file(self, file_id: str, file_path: str) -> None:
        """Bekleyen (pending) dosya ekle."""
        if "pending_files" not in self._state:
            self._state["pending_files"] = {}
        self._state["pending_files"][file_id] = file_path
        self._save_state()

    def remove_pending_file(self, file_id: str) -> Optional[str]:
        """Bekleyen dosyayı sil ve yolunu dön."""
        if "pending_files" in self._state and file_id in self._state["pending_files"]:
            path = self._state["pending_files"].pop(file_id)
            self._save_state()
            return path
        return None

    def get_pending_files(self) -> Dict[str, str]:
        """Bekleyen dosyaları dön."""
        return self._state.get("pending_files", {}).copy()

    def add_review_file(self, file_id: str, file_path: str) -> None:
        """İnceleme bekleyen (review) dosya ekle."""
        if "review_files" not in self._state:
            self._state["review_files"] = {}
        self._state["review_files"][file_id] = file_path
        self._save_state()

    def remove_review_file(self, file_id: str) -> Optional[str]:
        """İnceleme bekleyen dosyayı sil ve yolunu dön."""
        if "review_files" in self._state and file_id in self._state["review_files"]:
            path = self._state["review_files"].pop(file_id)
            self._save_state()
            return path
        return None

    def get_review_files(self) -> Dict[str, str]:
        """İnceleme bekleyen dosyaları dön."""
        return self._state.get("review_files", {}).copy()

    def get_status_summary(self) -> Dict[str, Any]:
        """Telegram /status komutu için özet bilgi."""
        return {
            "mode": self.mode.value,
            "processed_today": self._state.get("processed_today", 0),
            "rejected_today": self._state.get("rejected_today", 0),
            "token_usage_today": self._state.get("token_usage_today", 0),
            "queue_size": self._state.get("queue_size", 0),
            "last_event": self._state.get("last_event"),
            "last_event_type": self._state.get("last_event_type"),
            "maintenance_reason": self._state.get("maintenance_reason"),
            "last_health_check": self._state.get("last_health_check"),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Tüm state'i dict olarak döndür."""
        return self._state.copy()


# Singleton instance
_state_manager: Optional[StateManager] = None


def get_state_manager(state_path: str = "agent/state.json") -> StateManager:
    """
    Global StateManager instance döndür (singleton pattern).

    Args:
        state_path: state.json dosya yolu

    Returns:
        StateManager instance
    """
    global _state_manager
    if _state_manager is None:
        _state_manager = StateManager(state_path)
    return _state_manager
