"""
ktunDepo Telegram Bot — Ana Modül
Öğrenci katkılarını yöneten Telegram bot.

Komutlar:
- /start: Hoşgeldin mesajı
- /upload: Materyal yükleme akışı
- /status: Agent durumu
- /request: Materyal talebi
- /stats: Depo istatistikleri
- /resume: [ADMIN] Bakım modundan çık
"""

import os
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from collections import defaultdict

from agent.logging_config import get_logger, setup_logging

# Lazy imports
try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import (
        Application,
        CommandHandler,
        MessageHandler,
        CallbackQueryHandler,
        ContextTypes,
        filters,
    )
    from telegram.error import NetworkError, TimedOut
    import httpx
    import time

    HAS_TELEGRAM = True
except ImportError:
    HAS_TELEGRAM = False

logger = get_logger("bot")


class RateLimiter:
    """Kullanıcı bazlı rate limiting."""

    def __init__(self, daily_limit: int = 10, hourly_group_limit: int = 30):
        self.daily_limit = daily_limit
        self.hourly_group_limit = hourly_group_limit
        self._user_uploads: Dict[int, list] = defaultdict(list)
        self._group_uploads: list = []

    def can_upload(self, user_id: int) -> tuple[bool, str]:
        """Kullanıcı yükleme yapabilir mi kontrol et."""
        now = datetime.now()

        # Eski kayıtları temizle
        self._cleanup()

        # Kullanıcı günlük limiti
        user_today = [t for t in self._user_uploads[user_id] if t.date() == now.date()]
        if len(user_today) >= self.daily_limit:
            return (
                False,
                f"Günlük yükleme limitine ulaştın ({self.daily_limit}). Yarın tekrar dene.",
            )

        # Grup saatlik limiti
        hour_ago = now - timedelta(hours=1)
        recent_group = [t for t in self._group_uploads if t > hour_ago]
        if len(recent_group) >= self.hourly_group_limit:
            return False, "Grup saatlik yükleme limitine ulaştı. Biraz bekle."

        return True, ""

    def record_upload(self, user_id: int) -> None:
        """Yükleme kaydı ekle."""
        now = datetime.now()
        self._user_uploads[user_id].append(now)
        self._group_uploads.append(now)

    def _cleanup(self) -> None:
        """Eski kayıtları temizle."""
        now = datetime.now()
        yesterday = now - timedelta(days=1)

        for user_id in list(self._user_uploads.keys()):
            self._user_uploads[user_id] = [
                t for t in self._user_uploads[user_id] if t > yesterday
            ]

        hour_ago = now - timedelta(hours=2)
        self._group_uploads = [t for t in self._group_uploads if t > hour_ago]


class UserSession:
    """Kullanıcı oturum yönetimi (upload akışı için)."""

    def __init__(self):
        self._sessions: Dict[int, Dict[str, Any]] = {}

    def start_upload(self, user_id: int, file_info: dict) -> None:
        """Yükleme oturumu başlat."""
        self._sessions[user_id] = {
            "state": "awaiting_course",
            "file_info": file_info,
            "started_at": datetime.now(),
        }

    def set_course(self, user_id: int, course: str) -> None:
        """Ders bilgisi ekle."""
        if user_id in self._sessions:
            self._sessions[user_id]["course"] = course
            self._sessions[user_id]["state"] = "awaiting_type"

    def set_type(self, user_id: int, material_type: str) -> None:
        """Materyal türü ekle."""
        if user_id in self._sessions:
            self._sessions[user_id]["material_type"] = material_type
            self._sessions[user_id]["state"] = "ready"

    def get_session(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Oturum bilgisi al."""
        session = self._sessions.get(user_id)
        if session:
            # 10 dakikadan eski oturumları temizle
            if datetime.now() - session["started_at"] > timedelta(minutes=10):
                self.clear_session(user_id)
                return None
        return session

    def clear_session(self, user_id: int) -> None:
        """Oturumu temizle."""
        self._sessions.pop(user_id, None)


class KtunDepoBot:
    """ktunDepo Telegram Bot."""

    # Materyal türleri
    MATERIAL_TYPES = [
        "Ders Notu",
        "Sınav Sorusu",
        "Sunum",
        "Özet",
        "Laboratuvar",
        "Diğer",
    ]

    # Minimum dosya boyutu (KB)
    MIN_FILE_SIZE_KB = 50

    # Desteklenen uzantılar
    SUPPORTED_EXTENSIONS = [".pdf", ".pptx", ".docx", ".mp4", ".mkv"]

    def __init__(
        self,
        token: str,
        admin_chat_id: Optional[str] = None,
        incoming_path: str = "_incoming",
    ):
        """
        Bot başlat.

        Args:
            token: Telegram bot token
            admin_chat_id: Admin chat ID
            incoming_path: Gelen dosyaların kaydedileceği klasör
        """
        if not HAS_TELEGRAM:
            raise ImportError("python-telegram-bot yüklü değil")

        self.token = token
        self.admin_chat_id = admin_chat_id
        self.incoming_path = Path(incoming_path)
        self.incoming_path.mkdir(exist_ok=True)

        self.rate_limiter = RateLimiter()
        self.sessions = UserSession()
        self.application: Optional[Application] = None
        setup_logging()
        self.logger = get_logger("bot")

        # Reconnection tracking
        self._consecutive_errors = 0
        self._current_backoff = 1.0
        self._outage_start_time = None
        self._admin_notified = False
        self._last_error_log_time = 0

    async def start_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        /start komutu handler.
        """
        welcome_text = """
🎓 **ktunDepo'ya Hoşgeldin!**

Ben KTÜN Elektrik-Elektronik Mühendisliği ders materyali deposunu yönetiyorum.

**Komutlar:**
📤 /upload - Materyal yükle
📊 /status - Sistem durumu
📋 /request - Materyal talep et
📈 /stats - Depo istatistikleri

**Nasıl Çalışır:**
1. Materyal dosyasını (PDF, PPTX, DOCX) gönder
2. Hangi ders için olduğunu belirt
3. Materyal türünü seç
4. Agent otomatik değerlendirir ve uygunsa depoya ekler

💡 Kaliteli materyaller otomatik kabul edilir. Düşük kaliteli veya duplicate materyaller reddedilir.
        """
        await update.message.reply_text(welcome_text, parse_mode="Markdown")

    async def status_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        /status komutu handler.
        """
        # State manager'dan bilgi al (import zamanında yüklenecek)
        try:
            from agent.state_manager import get_state_manager

            state = get_state_manager()
            summary = state.get_status_summary()

            status_emoji = {"sleeping": "😴", "active": "🟢", "maintenance": "🔧"}

            mode = summary.get("mode", "unknown")
            emoji = status_emoji.get(mode, "❓")

            status_text = f"""
{emoji} **Agent Durumu: {mode.upper()}**

📊 **Bugünkü İstatistikler:**
• İşlenen: {summary.get("processed_today", 0)} materyal
• Reddedilen: {summary.get("rejected_today", 0)} materyal
• Token kullanımı: {summary.get("token_usage_today", 0):,}

📋 **Kuyruk:** {summary.get("queue_size", 0)} materyal bekliyor
            """

            if mode == "maintenance":
                status_text += f"\n⚠️ **Bakım Sebebi:** {summary.get('maintenance_reason', 'Bilinmiyor')}"

        except Exception as e:
            status_text = f"⚠️ Durum alınamadı: {str(e)}"

        await update.message.reply_text(status_text, parse_mode="Markdown")

    async def stats_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        /stats komutu handler.
        """
        # Depo istatistiklerini hesapla
        try:
            from scripts.course_resolver import get_course_resolver

            resolver = get_course_resolver()
            courses = resolver.list_courses()

            total_courses = sum(len(c) for c in courses.values())
            total_semesters = len(courses)

            # Dosya sayısını hesapla (basit versiyon)
            total_files = 0
            base_path = self.incoming_path.parent  # Depo kök dizini
            for semester, course_list in courses.items():
                semester_path = base_path / semester
                if semester_path.exists():
                    for course in course_list:
                        course_path = semester_path / course
                        if course_path.exists():
                            total_files += len(list(course_path.rglob("*")))

            stats_text = f"""
📈 **ktunDepo İstatistikleri**

🎓 **Dönem sayısı:** {total_semesters}
📚 **Ders sayısı:** {total_courses}
📁 **Toplam dosya:** ~{total_files}

**Dönemlere Göre Dersler:**
"""
            for semester in sorted(courses.keys()):
                course_count = len(courses[semester])
                stats_text += f"• {semester}: {course_count} ders\n"

        except Exception as e:
            stats_text = f"⚠️ İstatistikler alınamadı: {str(e)}"

        await update.message.reply_text(stats_text, parse_mode="Markdown")

    async def upload_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        /upload komutu handler.
        """
        await update.message.reply_text(
            "📤 **Materyal Yükleme**\n\n"
            "Yüklemek istediğin dosyayı (PDF, PPTX, DOCX) doğrudan bu sohbete gönder.",
            parse_mode="Markdown",
        )

    async def request_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        /request komutu handler.
        """
        if not context.args:
            await update.message.reply_text(
                "📋 **Materyal Talebi**\n\n"
                "Kullanım: `/request <ders adı>`\n"
                "Örnek: `/request Devre Analizi`",
                parse_mode="Markdown",
            )
            return

        course_name = " ".join(context.args)
        user_id = update.effective_user.id
        user_name = update.effective_user.full_name or str(user_id)

        # Talebi JSON dosyasına kaydet
        import json

        requests_path = self.incoming_path.parent / "_requests.json"
        try:
            if requests_path.exists():
                with open(requests_path, "r", encoding="utf-8") as f:
                    requests_data = json.load(f)
            else:
                requests_data = []

            requests_data.append(
                {
                    "course": course_name,
                    "user_id": user_id,
                    "user_name": user_name,
                    "requested_at": datetime.now().isoformat(),
                }
            )

            with open(requests_path, "w", encoding="utf-8") as f:
                json.dump(requests_data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass  # Kayıt başarısız olsa bile kullanıcıya bildir

        # Admin'e bildir
        if self.admin_chat_id:
            safe_course = self._escape_markdown(course_name)
            safe_user = self._escape_markdown(user_name)
            await self.send_admin_notification(
                f"📋 **Yeni Materyal Talebi**\n\n"
                f"Ders: {safe_course}\n"
                f"Kullanıcı: {safe_user} ({user_id})"
            )

        await update.message.reply_text(
            f"✅ **Talep Kaydedildi**\n\n"
            f"Ders: {course_name}\n\n"
            "Diğer öğrencilerin katkılarıyla materyal eklendiğinde bilgilendirileceksin.",
            parse_mode="Markdown",
        )

    async def resume_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        /resume komutu handler (sadece admin).
        """
        user_id = str(update.effective_user.id)

        if user_id != self.admin_chat_id:
            await update.message.reply_text(
                "⛔ Bu komut sadece admin tarafından kullanılabilir."
            )
            return

        try:
            from agent.state_manager import get_state_manager

            state = get_state_manager()

            if not state.is_maintenance:
                await update.message.reply_text("ℹ️ Agent zaten bakım modunda değil.")
                return

            if state.exit_maintenance():
                await update.message.reply_text(
                    "✅ Bakım modundan çıkıldı. Agent aktif."
                )
            else:
                await update.message.reply_text("⚠️ Bakım modundan çıkılamadı.")

        except Exception as e:
            await update.message.reply_text(f"⚠️ Hata: {str(e)}")

    async def pending_list_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """/pending_list komutu (admin)."""
        if str(update.effective_user.id) != self.admin_chat_id:
            await update.message.reply_text("⛔ Bu komut sadece adminler içindir.")
            return

        try:
            pending_path = Path("_pending")
            pending_path.mkdir(exist_ok=True)
            files = sorted(
                [
                    f
                    for f in pending_path.glob("*")
                    if f.is_file() and not f.name.endswith(".meta.json")
                ]
            )

            if not files:
                await update.message.reply_text("✅ Bekleyen dosya yok.")
                return

            msg = "⏳ **Onay Bekleyen Dosyalar:**\n\n"
            for i, f in enumerate(files, 1):
                size_kb = f.stat().st_size / 1024
                msg += f"**{i}**. `{f.name}` ({size_kb:.1f}KB)\n"

            msg += "\nOnaylamak için: `/approve <numara>`\nReddetmek için: `/reject <numara>`"
            await update.message.reply_text(msg, parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"⚠️ Hata: {str(e)}")

    async def approve_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """/approve <numara> komutu (admin). Dosyayı doğrudan repoya ekler."""
        if str(update.effective_user.id) != self.admin_chat_id:
            await update.message.reply_text("⛔ Bu komut sadece adminler içindir.")
            return

        if not context.args:
            await update.message.reply_text(
                "Kullanım: `/approve <numara>`", parse_mode="Markdown"
            )
            return

        try:
            idx = int(context.args[0]) - 1
            pending_path = Path("_pending")
            files = sorted(
                [
                    f
                    for f in pending_path.glob("*")
                    if f.is_file() and not f.name.endswith(".meta.json")
                ]
            )

            if idx < 0 or idx >= len(files):
                await update.message.reply_text(f"⚠️ Geçersiz numara: {idx + 1}")
                return

            file_to_approve = files[idx]

            # Metadata oku
            import json

            meta_path = file_to_approve.with_suffix(
                file_to_approve.suffix + ".meta.json"
            )
            metadata = {}
            if meta_path.exists():
                try:
                    with open(meta_path, "r", encoding="utf-8") as f:
                        metadata = json.load(f)
                except Exception:
                    pass

            course_name = metadata.get("course")
            material_type = metadata.get("material_type", "Diğer")
            semester = metadata.get("semester")

            if not course_name:
                await update.message.reply_text(
                    f"⚠️ `{file_to_approve.name}` için ders bilgisi eksik.\n"
                    "Metadata bulunamadı. `/publish` komutunu kullanın.",
                    parse_mode="Markdown",
                )
                return

            from scripts.course_resolver import get_course_resolver, CourseNotFoundError
            from scripts.git_manager import get_git_manager

            resolver = get_course_resolver()
            try:
                match = resolver.resolve(course_name, semester)
            except CourseNotFoundError as e:
                await update.message.reply_text(
                    f"⚠️ Ders bulunamadı: {e}\n`/publish` komutuyla manuel yayınlayın.",
                    parse_mode="Markdown",
                )
                return

            target_dir = match.full_path
            git_manager = get_git_manager()

            success, new_path = git_manager.move_file_to_course(
                str(file_to_approve), target_dir, file_to_approve.name
            )

            if not success:
                await update.message.reply_text(f"❌ Dosya taşıma hatası: {new_path}")
                return

            # Git commit
            git_result = git_manager.commit_material(
                new_path, course_name, material_type
            )

            # Metadata sil
            if meta_path.exists():
                try:
                    meta_path.unlink()
                except Exception:
                    pass

            msg = f"✅ `{file_to_approve.name}` onaylandı ve repoya eklendi.\n📂 Konum: `{new_path}`"
            if not git_result.success:
                msg += f"\n⚠️ Git Hatası: {git_result.error}"

            await update.message.reply_text(msg, parse_mode="Markdown")

        except ValueError:
            await update.message.reply_text("⚠️ Lütfen geçerli bir sayı girin.")
        except Exception as e:
            await update.message.reply_text(f"⚠️ Hata: {str(e)}")

    async def reject_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """/reject <numara> komutu (admin)."""
        if str(update.effective_user.id) != self.admin_chat_id:
            await update.message.reply_text("⛔ Bu komut sadece adminler içindir.")
            return

        if not context.args:
            await update.message.reply_text(
                "Kullanım: `/reject <numara>`", parse_mode="Markdown"
            )
            return

        try:
            idx = int(context.args[0]) - 1
            pending_path = Path("_pending")
            files = sorted(
                [
                    f
                    for f in pending_path.glob("*")
                    if f.is_file() and not f.name.endswith(".meta.json")
                ]
            )

            if idx < 0 or idx >= len(files):
                await update.message.reply_text(f"⚠️ Geçersiz numara: {idx + 1}")
                return

            file_to_reject = files[idx]
            target_dir = Path("_rejected")
            target_dir.mkdir(exist_ok=True)
            target_path = target_dir / file_to_reject.name

            import shutil

            shutil.move(str(file_to_reject), str(target_path))

            # Meta varsa taşı
            meta_path = file_to_reject.with_suffix(file_to_reject.suffix + ".meta.json")
            if meta_path.exists():
                shutil.move(
                    str(meta_path),
                    str(target_path.with_suffix(target_path.suffix + ".meta.json")),
                )

            await update.message.reply_text(
                f"❌ `{file_to_reject.name}` reddedildi ve arşive kaldırıldı."
            )

        except ValueError:
            await update.message.reply_text("⚠️ Lütfen geçerli bir sayı girin.")
        except Exception as e:
            await update.message.reply_text(f"⚠️ Hata: {str(e)}")

    def _escape_markdown(self, text: str) -> str:
        """Markdown özel karakterlerini temizle."""
        # Alt çizgi, yıldız gibi karakterleri kaçır
        escape_chars = r"_*`["
        for char in escape_chars:
            text = text.replace(char, f"\\{char}")
        return text

    async def handle_document(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Dosya mesajı handler.
        """
        document = update.message.document
        user_id = update.effective_user.id

        # Rate limit kontrolü
        can_upload, reason = self.rate_limiter.can_upload(user_id)
        if not can_upload:
            await update.message.reply_text(f"⚠️ {reason}")
            return

        # Dosya boyutu kontrolü
        file_size_kb = document.file_size / 1024
        if file_size_kb < self.MIN_FILE_SIZE_KB:
            await update.message.reply_text(
                f"⚠️ Dosya çok küçük ({file_size_kb:.1f}KB). "
                f"Minimum {self.MIN_FILE_SIZE_KB}KB olmalı."
            )
            return

        # Uzantı kontrolü
        filename = document.file_name or "unnamed"
        extension = Path(filename).suffix.lower()
        if extension not in self.SUPPORTED_EXTENSIONS:
            await update.message.reply_text(
                f"⚠️ Desteklenmeyen format: {extension}\n"
                f"Desteklenen: {', '.join(self.SUPPORTED_EXTENSIONS)}"
            )
            return

        # Oturum başlat
        self.sessions.start_upload(
            user_id,
            {
                "file_id": document.file_id,
                "file_name": filename,
                "file_size": document.file_size,
                "mime_type": document.mime_type,
            },
        )

        safe_filename = self._escape_markdown(filename)
        await update.message.reply_text(
            f"📁 **Dosya alındı:** {safe_filename}\n\n"
            "Bu materyal hangi ders için?\n"
            "_(Ders adını veya kodunu yaz)_",
            parse_mode="Markdown",
        )

    async def handle_text(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Metin mesajı handler (upload akışı için).
        """
        user_id = update.effective_user.id
        text = update.message.text.strip()

        session = self.sessions.get_session(user_id)
        if not session:
            return  # Aktif oturum yok

        state = session.get("state")

        if state == "awaiting_course":
            # Ders bilgisi alındı
            self.sessions.set_course(user_id, text)

            # Materyal türü seçimi için butonlar
            keyboard = [
                [InlineKeyboardButton(t, callback_data=f"type_{t}")]
                for t in self.MATERIAL_TYPES
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            safe_text = self._escape_markdown(text)
            await update.message.reply_text(
                f"✅ Ders: **{safe_text}**\n\nMateryal türünü seç:",
                reply_markup=reply_markup,
                parse_mode="Markdown",
            )

    async def handle_callback(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Inline button callback handler.
        """
        query = update.callback_query
        await query.answer()

        user_id = query.from_user.id
        data = query.data

        if data.startswith("type_"):
            material_type = data[5:]  # "type_" prefix'ini kaldır

            session = self.sessions.get_session(user_id)
            if not session:
                await query.edit_message_text(
                    "⚠️ Oturum sona erdi. Lütfen dosyayı tekrar gönder."
                )
                return

            self.sessions.set_type(user_id, material_type)

            # Dosyayı indir ve kaydet
            file_info = session.get("file_info", {})
            course = session.get("course", "Bilinmiyor")

            try:
                # Telegram'dan dosyayı indir
                file = await context.bot.get_file(file_info["file_id"])

                # Benzersiz dosya adı oluştur
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_filename = f"{timestamp}_{file_info['file_name']}"
                save_path = self.incoming_path / safe_filename

                await file.download_to_drive(save_path)

                # Metadata dosyası oluştur
                metadata = {
                    "original_filename": file_info["file_name"],
                    "saved_as": safe_filename,
                    "user_id": user_id,
                    "course": course,
                    "material_type": material_type,
                    "file_size": file_info["file_size"],
                    "uploaded_at": datetime.now().isoformat(),
                    "chat_id": update.effective_chat.id,  # Geri bildirim için chat_id ekle
                }

                metadata_path = save_path.with_suffix(save_path.suffix + ".meta.json")
                import json

                with open(metadata_path, "w", encoding="utf-8") as f:
                    json.dump(metadata, f, indent=2, ensure_ascii=False)

                # Rate limit kaydı
                self.rate_limiter.record_upload(user_id)

                # Oturumu temizle
                self.sessions.clear_session(user_id)

                escaped_filename = self._escape_markdown(file_info["file_name"])
                escaped_course = self._escape_markdown(course)

                await query.edit_message_text(
                    f"✅ **Materyal alındı!**\n\n"
                    f"📁 Dosya: {escaped_filename}\n"
                    f"📚 Ders: {escaped_course}\n"
                    f"📋 Tür: {material_type}\n\n"
                    "Agent değerlendirmeyi tamamladığında sonucu bildireceğim.",
                    parse_mode="Markdown",
                )

                # Agent'ı uyandır
                try:
                    from agent.state_manager import get_state_manager

                    state = get_state_manager()
                    state.wake_up("telegram_upload")
                except Exception:
                    pass  # Agent modülü yüklü değilse sessizce geç

            except Exception as e:
                await query.edit_message_text(f"⚠️ Dosya kaydedilemedi: {str(e)}")
                self.sessions.clear_session(user_id)

    async def send_admin_notification(self, message: str) -> None:
        """Admin'e bildirim gönder."""
        if self.admin_chat_id and self.application:
            try:
                await self.application.bot.send_message(
                    chat_id=self.admin_chat_id, text=message, parse_mode="Markdown"
                )
            except Exception:
                pass

    async def error_handler(
        self, update: object, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Hataları yakala ve logla. Ağ hatalarını özel olarak işle."""
        current_time = time.time()

        # Ağ hatalarını tespit et
        is_network_error = isinstance(context.error, (NetworkError, TimedOut))
        if isinstance(context.error, Exception):
            is_network_error = is_network_error or isinstance(
                context.error.__cause__, httpx.ConnectError
            )

        if is_network_error:
            self._consecutive_errors += 1

            # Rate-limited logging (30 saniyede bir)
            if current_time - self._last_error_log_time >= 30:
                self.logger.warning(
                    f"Ağ hatası tespit edildi (ardışık: {self._consecutive_errors}): {context.error}"
                )
                self._last_error_log_time = current_time

            # Kesinti başlangıcını kaydet
            if self._outage_start_time is None:
                self._outage_start_time = current_time
                self.logger.info("Ağ kesintisi başladı, yeniden bağlanma denenecek")

            # 5 dakikadan uzun kesintilerde admin'i bilgilendir
            outage_duration = current_time - self._outage_start_time
            if outage_duration >= 300 and not self._admin_notified:
                try:
                    await self.send_admin_notification(
                        f"⚠️ Bot {int(outage_duration / 60)} dakikadır bağlantı kuramıyor. "
                        f"Otomatik yeniden deneme devam ediyor..."
                    )
                    self._admin_notified = True
                except Exception as e:
                    self.logger.error(f"Admin bildirimi gönderilemedi: {e}")
        else:
            # Ağ harici hatalar için normal loglama
            self.logger.error(
                f"Telegram hatası: {context.error}", exc_info=context.error
            )

    async def review_list_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """/review_list komutu (admin)."""
        if str(update.effective_user.id) != self.admin_chat_id:
            await update.message.reply_text("⛔ Bu komut sadece adminler içindir.")
            return

        try:
            review_path = Path("_review")
            review_path.mkdir(exist_ok=True)
            files = sorted(
                [
                    f
                    for f in review_path.glob("*")
                    if f.is_file() and not f.name.endswith(".meta.json")
                ]
            )

            if not files:
                await update.message.reply_text("✅ İnceleme bekleyen dosya yok.")
                return

            msg = "🔍 **İnceleme Bekleyen Dosyalar:**\n\n"
            for i, f in enumerate(files, 1):
                size_kb = f.stat().st_size / 1024
                msg += f"**{i}**. `{f.name}` ({size_kb:.1f}KB)\n"

            msg += "\nOnaylayıp yayınlamak için: `/publish <numara>`\nReddetmek için: `/reject_review <numara>`"
            await update.message.reply_text(msg, parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"⚠️ Hata: {str(e)}")

    async def publish_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """/publish <numara> komutu (admin)."""
        if str(update.effective_user.id) != self.admin_chat_id:
            await update.message.reply_text("⛔ Bu komut sadece adminler içindir.")
            return

        if not context.args:
            await update.message.reply_text(
                "Kullanım: `/publish <numara>`", parse_mode="Markdown"
            )
            return

        try:
            idx = int(context.args[0]) - 1
            review_path = Path("_review")
            files = sorted(
                [
                    f
                    for f in review_path.glob("*")
                    if f.is_file() and not f.name.endswith(".meta.json")
                ]
            )

            if idx < 0 or idx >= len(files):
                await update.message.reply_text(f"⚠️ Geçersiz numara: {idx + 1}")
                return

            file_to_publish = files[idx]

            # Metadata'dan hedef yolu bul
            meta_path = file_to_publish.with_suffix(
                file_to_publish.suffix + ".meta.json"
            )
            if not meta_path.exists():
                await update.message.reply_text(
                    "⚠️ Dosyanın metadata bilgisi bulunamadı, otomatik yayınlanamaz."
                )
                return

            import json

            with open(meta_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)

            course_name = metadata.get("course")
            material_type = metadata.get("material_type", "Diğer")
            semester = metadata.get("semester")

            if not course_name:
                await update.message.reply_text("⚠️ Ders bilgisi eksik.")
                return

            from scripts.course_resolver import get_course_resolver
            from scripts.git_manager import get_git_manager

            resolver = get_course_resolver()
            match = resolver.resolve(course_name, semester)
            target_dir = match.full_path

            git_manager = get_git_manager()
            success, new_path = git_manager.move_file_to_course(
                str(file_to_publish), target_dir, file_to_publish.name
            )

            if success:
                # Commit
                git_result = git_manager.commit_material(
                    new_path, course_name, material_type
                )

                # Metadata sil
                meta_path.unlink()

                msg = f"🚀 `{file_to_publish.name}` başarıyla yayınlandı.\nKonum: `{new_path}`"
                if not git_result.success:
                    msg += f"\n⚠️ Git Hatası: {git_result.error}"

                await update.message.reply_text(msg, parse_mode="Markdown")
            else:
                await update.message.reply_text(f"❌ Dosya taşıma hatası: {new_path}")

        except ValueError:
            await update.message.reply_text("⚠️ Lütfen geçerli bir sayı girin.")
        except Exception as e:
            await update.message.reply_text(f"⚠️ Hata: {str(e)}")

    async def reject_review_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """/reject_review <numara> komutu (admin)."""
        if str(update.effective_user.id) != self.admin_chat_id:
            await update.message.reply_text("⛔ Bu komut sadece adminler içindir.")
            return

        if not context.args:
            await update.message.reply_text(
                "Kullanım: `/reject_review <numara>`", parse_mode="Markdown"
            )
            return

        try:
            idx = int(context.args[0]) - 1
            review_path = Path("_review")
            files = sorted(
                [
                    f
                    for f in review_path.glob("*")
                    if f.is_file() and not f.name.endswith(".meta.json")
                ]
            )

            if idx < 0 or idx >= len(files):
                await update.message.reply_text(f"⚠️ Geçersiz numara: {idx + 1}")
                return

            file_to_reject = files[idx]
            target_dir = Path("_rejected")
            target_dir.mkdir(exist_ok=True)

            import shutil

            shutil.move(str(file_to_reject), str(target_dir / file_to_reject.name))

            # Meta varsa sil veya taşı
            meta_path = file_to_reject.with_suffix(file_to_reject.suffix + ".meta.json")
            if meta_path.exists():
                shutil.move(str(meta_path), str(target_dir / meta_path.name))

            await update.message.reply_text(
                f"❌ `{file_to_reject.name}` reddedildi ve arşive kaldırıldı."
            )

        except ValueError:
            await update.message.reply_text("⚠️ Lütfen geçerli bir sayı girin.")
        except Exception as e:
            await update.message.reply_text(f"⚠️ Hata: {str(e)}")

    def build_application(self) -> Application:
        """Telegram Application oluştur."""
        self.application = Application.builder().token(self.token).build()

        # Handler'ları ekle
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("stats", self.stats_command))
        self.application.add_handler(CommandHandler("upload", self.upload_command))
        self.application.add_handler(CommandHandler("request", self.request_command))
        self.application.add_handler(CommandHandler("resume", self.resume_command))
        self.application.add_handler(
            CommandHandler("pending_list", self.pending_list_command)
        )
        self.application.add_handler(CommandHandler("approve", self.approve_command))
        self.application.add_handler(CommandHandler("reject", self.reject_command))
        self.application.add_handler(
            CommandHandler("review_list", self.review_list_command)
        )
        self.application.add_handler(CommandHandler("publish", self.publish_command))
        self.application.add_handler(
            CommandHandler("reject_review", self.reject_review_command)
        )

        # Dosya handler
        self.application.add_handler(
            MessageHandler(filters.Document.ALL, self.handle_document)
        )

        # Metin handler (upload akışı için)
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text)
        )

        # Callback handler
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))

        # Error handler
        self.application.add_error_handler(self.error_handler)

        return self.application

    def run(self) -> None:
        """Bot'u çalıştır (polling mode)."""
        app = self.build_application()
        logger.info("ktunDepo Bot başlatılıyor...")
        app.run_polling(allowed_updates=Update.ALL_TYPES)


def create_bot() -> Optional[KtunDepoBot]:
    """
    Ortam değişkenlerinden bot oluştur.

    Returns:
        KtunDepoBot instance veya None
    """
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        return None

    return KtunDepoBot(
        token=token,
        admin_chat_id=os.getenv("ADMIN_CHAT_ID"),
        incoming_path=os.getenv("INCOMING_PATH", "_incoming"),
    )


if __name__ == "__main__":
    bot = create_bot()
    if bot:
        bot.run()
    else:
        logger.warning("TELEGRAM_BOT_TOKEN ayarlanmamış")
