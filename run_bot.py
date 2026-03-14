#!/usr/bin/env python3
"""
ktunDepo Telegram Bot — Giriş Noktası
Bot'u başlatmak için bu scripti çalıştırın.

Kullanım:
    python run_bot.py

Gerekli ortam değişkenleri:
    TELEGRAM_BOT_TOKEN  - Bot token'ı
    ADMIN_CHAT_ID       - Admin Telegram ID
"""

import os
import sys
from pathlib import Path

# Proje kökünü Python path'e ekle
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def main():
    # Ortam değişkenlerini yükle
    from dotenv import load_dotenv

    load_dotenv()

    # Logging'i kur
    from agent.logging_config import setup_logging, get_logger

    setup_logging()
    logger = get_logger("run_bot")

    # Token kontrolü
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error(
            "TELEGRAM_BOT_TOKEN ortam değişkeni ayarlanmamış! .env dosyasını oluşturun veya export edin."
        )
        sys.exit(1)

    logger.info("""
    ╔═══════════════════════════════════════════╗
    ║      ktunDepo Telegram Bot v1.0.0         ║
    ║      Öğrenci Katkı Yönetimi               ║
    ╚═══════════════════════════════════════════╝
    """)

    try:
        from bot.telegram_bot import create_bot

        bot = create_bot()
        if bot:
            logger.info(
                "Bot başlatılıyor... Komutlar: /start, /upload, /status, /stats, /request"
            )
            logger.info("Admin komutları: /pending_list, /approve, /reject, /resume")
            logger.info("Durdurmak için: Ctrl+C")
            bot.run()
        else:
            logger.error("Bot oluşturulamadı. Token'ı kontrol edin.")
            sys.exit(1)

    except ImportError as e:
        logger.error(
            f"Modül hatası: {e} — 'uv add python-telegram-bot>=22.0' çalıştırın."
        )
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Bot durduruldu.")


if __name__ == "__main__":
    main()
