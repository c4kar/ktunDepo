#!/usr/bin/env python3
"""
ktunDepo Agent — Ana Giriş Noktası
Agent'ı başlatmak için bu scripti çalıştırın.

Kullanım:
    python run_agent.py              # Watchdog modu (dosya izleme)
    python run_agent.py --process    # Bekleyen dosyaları işle
    python run_agent.py --health     # Sağlık kontrolü
    python run_agent.py --status     # Durum bilgisi
"""

import os
import sys
import argparse
from pathlib import Path

# Proje kökünü Python path'e ekle
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def main():
    parser = argparse.ArgumentParser(
        description="ktunDepo Agent — Ders Materyali Yönetim Sistemi"
    )
    parser.add_argument(
        "--process", action="store_true", help="Bekleyen dosyaları işle ve çık"
    )
    parser.add_argument("--health", action="store_true", help="Sağlık kontrolü yap")
    parser.add_argument("--status", action="store_true", help="Agent durumunu göster")
    parser.add_argument("--file", type=str, help="Tek dosya işle")
    parser.add_argument(
        "--reset-daily", action="store_true", help="Günlük sayaçları sıfırla"
    )

    args = parser.parse_args()

    # Logging'i kur (pipeline da setup_logging çağırır ama burada erken başlat)
    from agent.logging_config import setup_logging, get_logger

    setup_logging()
    logger = get_logger("run_agent")

    # Config ve state'i yükle
    try:
        from agent.config_loader import get_config
        from agent.state_manager import get_state_manager
        from agent.pipeline import create_pipeline

        config = get_config()
        state = get_state_manager()

    except Exception as e:
        logger.error(f"Başlatma hatası: {e}")
        sys.exit(1)

    # Status
    if args.status:
        summary = state.get_status_summary()
        print("\n📊 ktunDepo Agent Durumu")
        print("=" * 40)
        print(f"Mod: {summary['mode'].upper()}")
        print(f"Bugün işlenen: {summary['processed_today']}")
        print(f"Bugün reddedilen: {summary['rejected_today']}")
        print(f"Token kullanımı: {summary['token_usage_today']:,}")
        print(f"Kuyruk: {summary['queue_size']} dosya")
        if summary["maintenance_reason"]:
            print(f"⚠️ Bakım sebebi: {summary['maintenance_reason']}")
        print("=" * 40)
        return

    # Health check
    if args.health:
        pipeline = create_pipeline()
        report = pipeline.run_health_check()

        print("\n🏥 Sağlık Kontrolü Raporu")
        print("=" * 40)
        status = "✅ SAĞLIKLI" if report["healthy"] else "❌ SORUNLU"
        print(f"Durum: {status}")
        print(f"Disk kullanımı: %{report.get('disk_usage_percent', 0):.1f}")
        print(f"Bekleyen dosya: {report.get('incoming_files', 0)}")

        if report.get("issues"):
            print("\n⚠️ Sorunlar:")
            for issue in report["issues"]:
                print(f"  - {issue}")

        if report.get("warnings"):
            print("\n📢 Uyarılar:")
            for warning in report["warnings"]:
                print(f"  - {warning}")

        print("=" * 40)
        return

    # Reset daily
    if args.reset_daily:
        state.reset_daily_counters()
        print("✅ Günlük sayaçlar sıfırlandı")
        return

    # Tek dosya işle
    if args.file:
        if not os.path.exists(args.file):
            print(f"❌ Dosya bulunamadı: {args.file}")
            sys.exit(1)

        pipeline = create_pipeline()
        result = pipeline.process_file(args.file)

        print(f"\n📄 Dosya: {args.file}")
        print(f"Karar: {result.decision}")
        print(f"Sebep: {result.reason}")
        if result.new_path:
            print(f"Yeni konum: {result.new_path}")
        return

    # Bekleyen dosyaları işle
    if args.process:
        pipeline = create_pipeline()
        results = pipeline.process_pending_files()

        print(f"\n📦 İşlenen dosya sayısı: {len(results)}")
        for r in results:
            status = "✅" if r.decision == "ACCEPTED" else "❌"
            print(f"  {status} {Path(r.file_path).name}: {r.decision}")
        return

    # Watchdog modu (varsayılan)
    logger.info("""
    ╔═══════════════════════════════════════════╗
    ║      ktunDepo Agent v1.0.0                ║
    ║      Event-Driven Material Manager        ║
    ╚═══════════════════════════════════════════╗
    """)

    pipeline = create_pipeline()

    import asyncio

    # Yeni bir event loop oluştur
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    if pipeline.start_watching(loop):
        logger.info("_incoming klasörü izleniyor...")
        logger.info("Telegram bot için: python -m bot.telegram_bot")
        logger.info("Durdurmak için: Ctrl+C")

        try:
            loop.run_forever()
        except KeyboardInterrupt:
            pipeline.stop_watching()
            logger.info("Agent durduruldu.")
        finally:
            loop.close()
    else:
        logger.error("Watchdog başlatılamadı. 'uv add watchdog' çalıştırın.")
        sys.exit(1)


if __name__ == "__main__":
    main()
