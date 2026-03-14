"""
ktunDepo Agent — Git Manager
Otomatik commit/push ve bakım modu yönetimi.

Commit format: feat({course_code}): add {material_type} [{date}]
"""

import os
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass

# Lazy import
try:
    import git
    from git import Repo, GitCommandError

    HAS_GIT = True
except ImportError:
    HAS_GIT = False


@dataclass
class GitResult:
    """Git işlem sonucu."""

    success: bool
    message: str = ""
    commit_hash: Optional[str] = None
    error: Optional[str] = None


class GitManager:
    """
    Git deposu yönetimi.

    - Otomatik commit ve push
    - Conflict tespiti
    - Bakım modu tetikleyicileri
    """

    def __init__(
        self, repo_path: str = ".", auto_commit: bool = True, branch: str = "main"
    ):
        """
        GitManager başlat.

        Args:
            repo_path: Git deposu yolu
            auto_commit: Otomatik commit aktif mi
            branch: Varsayılan branch
        """
        self.repo_path = Path(repo_path)
        self.auto_commit = auto_commit
        self.branch = branch
        self._repo: Optional[Repo] = None

    def _get_repo(self) -> Optional[Repo]:
        """Git repo lazy init."""
        if not HAS_GIT:
            return None

        if self._repo is None:
            try:
                self._repo = Repo(self.repo_path)
            except Exception:
                return None
        return self._repo

    def is_repo_healthy(self) -> tuple[bool, str]:
        """
        Depo sağlık kontrolü.

        Returns:
            (healthy, reason) tuple
        """
        repo = self._get_repo()
        if repo is None:
            return False, "Git deposu bulunamadı"

        try:
            # Dirty state kontrolü (uncommitted changes)
            if repo.is_dirty(untracked_files=True):
                # Bu uyarı değil, bilgi amaçlı
                pass

            # Head kontrolü
            if repo.head.is_detached:
                return False, "HEAD detached durumda"

            # Remote kontrolü
            if "origin" not in [r.name for r in repo.remotes]:
                return False, "Origin remote bulunamadı"

            return True, "Depo sağlıklı"

        except Exception as e:
            return False, f"Depo kontrolü başarısız: {str(e)}"

    def commit_material(
        self,
        file_path: str,
        course_code: str,
        material_type: str,
        message_suffix: str = "",
    ) -> GitResult:
        """
        Materyal için commit oluştur.

        Args:
            file_path: Eklenen dosya yolu
            course_code: Ders kodu
            material_type: Materyal türü
            message_suffix: Ek commit mesajı

        Returns:
            GitResult objesi
        """
        repo = self._get_repo()
        if repo is None:
            return GitResult(success=False, error="Git deposu bulunamadı")

        try:
            # Dosyayı staging'e ekle
            repo.index.add([file_path])

            # Commit mesajı oluştur
            date_str = datetime.now().strftime("%Y-%m-%d")
            type_slug = material_type.lower().replace(" ", "_")

            commit_msg = f"feat({course_code}): add {type_slug} [{date_str}]"
            if message_suffix:
                commit_msg += f" - {message_suffix}"

            # Commit yap
            commit = repo.index.commit(commit_msg)

            return GitResult(
                success=True, message=commit_msg, commit_hash=commit.hexsha[:7]
            )

        except GitCommandError as e:
            return GitResult(success=False, error=f"Git commit hatası: {str(e)}")
        except Exception as e:
            return GitResult(success=False, error=f"Beklenmeyen hata: {str(e)}")

    def push_changes(self) -> GitResult:
        """
        Değişiklikleri remote'a push et.

        Returns:
            GitResult objesi
        """
        repo = self._get_repo()
        if repo is None:
            return GitResult(success=False, error="Git deposu bulunamadı")

        try:
            origin = repo.remote("origin")
            push_info = origin.push()[0]

            # Push sonucu kontrol
            if push_info.flags & push_info.ERROR:
                return GitResult(
                    success=False, error=f"Push hatası: {push_info.summary}"
                )

            return GitResult(success=True, message="Push başarılı")

        except GitCommandError as e:
            return GitResult(success=False, error=f"Git push hatası: {str(e)}")
        except Exception as e:
            return GitResult(success=False, error=f"Beklenmeyen hata: {str(e)}")

    def pull_changes(self) -> GitResult:
        """
        Remote'dan pull yap.

        Returns:
            GitResult objesi
        """
        repo = self._get_repo()
        if repo is None:
            return GitResult(success=False, error="Git deposu bulunamadı")

        try:
            origin = repo.remote("origin")
            pull_info = origin.pull()

            return GitResult(
                success=True, message=f"Pull başarılı: {len(pull_info)} güncelleme"
            )

        except GitCommandError as e:
            error_msg = str(e)

            # Merge conflict tespiti
            if "conflict" in error_msg.lower():
                return GitResult(success=False, error="MERGE_CONFLICT")

            return GitResult(success=False, error=f"Git pull hatası: {error_msg}")
        except Exception as e:
            return GitResult(success=False, error=f"Beklenmeyen hata: {str(e)}")

    def get_status(self) -> Dict[str, Any]:
        """
        Depo durumunu döndür.

        Returns:
            Durum dict'i
        """
        repo = self._get_repo()
        if repo is None:
            return {"error": "Git deposu bulunamadı"}

        try:
            return {
                "branch": repo.active_branch.name,
                "is_dirty": repo.is_dirty(),
                "untracked_files": len(repo.untracked_files),
                "staged_files": len(repo.index.diff("HEAD")),
                "modified_files": len(repo.index.diff(None)),
                "last_commit": {
                    "hash": repo.head.commit.hexsha[:7],
                    "message": repo.head.commit.message.strip(),
                    "author": str(repo.head.commit.author),
                    "date": repo.head.commit.committed_datetime.isoformat(),
                },
            }
        except Exception as e:
            return {"error": str(e)}

    def get_recent_commits(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Son commit'leri listele.

        Args:
            limit: Maksimum commit sayısı

        Returns:
            Commit listesi
        """
        repo = self._get_repo()
        if repo is None:
            return []

        try:
            commits = []
            for commit in repo.iter_commits(max_count=limit):
                commits.append(
                    {
                        "hash": commit.hexsha[:7],
                        "message": commit.message.strip(),
                        "author": str(commit.author),
                        "date": commit.committed_datetime.isoformat(),
                    }
                )
            return commits
        except Exception:
            return []

    def commit_and_push(
        self, file_path: str, course_code: str, material_type: str
    ) -> GitResult:
        """
        Commit yap ve hemen push et.

        Args:
            file_path: Dosya yolu
            course_code: Ders kodu
            material_type: Materyal türü

        Returns:
            GitResult objesi
        """
        # Commit
        commit_result = self.commit_material(file_path, course_code, material_type)
        if not commit_result.success:
            return commit_result

        # Push
        push_result = self.push_changes()
        if not push_result.success:
            return GitResult(
                success=False,
                message=commit_result.message,
                commit_hash=commit_result.commit_hash,
                error=f"Commit başarılı ama push başarısız: {push_result.error}",
            )

        return GitResult(
            success=True,
            message=f"{commit_result.message} (pushed)",
            commit_hash=commit_result.commit_hash,
        )

    def move_file_to_course(
        self, source_path: str, course_path: str, filename: Optional[str] = None
    ) -> tuple[bool, str]:
        """
        Dosyayı _incoming'den ders klasörüne taşı.

        Args:
            source_path: Kaynak dosya yolu
            course_path: Hedef ders klasörü
            filename: Yeni dosya adı (None ise orijinal kullanılır)

        Returns:
            (success, new_path) tuple
        """
        source = Path(source_path)
        if not source.exists():
            return False, f"Kaynak dosya bulunamadı: {source_path}"

        dest_dir = Path(course_path)
        dest_dir.mkdir(parents=True, exist_ok=True)

        dest_filename = filename or source.name
        dest_path = dest_dir / dest_filename

        # Aynı isimde dosya varsa numara ekle
        counter = 1
        while dest_path.exists():
            stem = Path(dest_filename).stem
            suffix = Path(dest_filename).suffix
            dest_path = dest_dir / f"{stem}_{counter}{suffix}"
            counter += 1

        try:
            shutil.move(str(source), str(dest_path))
            return True, str(dest_path)
        except Exception as e:
            return False, str(e)


class MaintenanceChecker:
    """
    Bakım modu kontrol ve tetikleyici.
    """

    TRIGGERS = [
        "git push failed",
        "git merge conflict",
        "qdrant connection failed",
        "disk_usage > 90%",
        "corruption_detected",
    ]

    def __init__(self, base_path: str = "."):
        """
        MaintenanceChecker başlat.

        Args:
            base_path: Depo kök dizini
        """
        self.base_path = Path(base_path)

    def check_disk_usage(self) -> tuple[float, bool]:
        """
        Disk kullanımını kontrol et.

        Returns:
            (usage_percent, is_critical) tuple
        """
        try:
            total, used, free = shutil.disk_usage(self.base_path)
            usage_percent = (used / total) * 100
            is_critical = usage_percent > 90
            return usage_percent, is_critical
        except Exception:
            return 0.0, False

    def check_incoming_folder(self) -> tuple[int, int]:
        """
        _incoming klasörünü kontrol et.

        Returns:
            (file_count, total_size_mb) tuple
        """
        incoming = self.base_path / "_incoming"
        if not incoming.exists():
            return 0, 0

        files = list(incoming.glob("*"))
        # .gitkeep ve .meta.json hariç
        files = [
            f
            for f in files
            if f.is_file() and not f.name.endswith((".gitkeep", ".meta.json"))
        ]

        total_size = sum(f.stat().st_size for f in files)
        return len(files), int(total_size / (1024 * 1024))

    def run_health_check(self) -> Dict[str, Any]:
        """
        Tam sağlık kontrolü.

        Returns:
            Sağlık raporu dict'i
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "healthy": True,
            "issues": [],
            "warnings": [],
        }

        # Git kontrolü
        git_manager = GitManager(str(self.base_path))
        git_healthy, git_reason = git_manager.is_repo_healthy()
        if not git_healthy:
            report["healthy"] = False
            report["issues"].append(f"Git: {git_reason}")

        # Disk kontrolü
        disk_usage, disk_critical = self.check_disk_usage()
        if disk_critical:
            report["healthy"] = False
            report["issues"].append(f"Disk kullanımı kritik: %{disk_usage:.1f}")
        elif disk_usage > 80:
            report["warnings"].append(f"Disk kullanımı yüksek: %{disk_usage:.1f}")

        # Incoming klasörü kontrolü
        incoming_count, incoming_size = self.check_incoming_folder()
        if incoming_count > 50:
            report["warnings"].append(f"Bekleyen dosya sayısı yüksek: {incoming_count}")

        report["disk_usage_percent"] = disk_usage
        report["incoming_files"] = incoming_count
        report["incoming_size_mb"] = incoming_size

        return report


# Singleton instances
_git_manager: Optional[GitManager] = None
_maintenance_checker: Optional[MaintenanceChecker] = None


def get_git_manager(repo_path: str = ".") -> GitManager:
    """Global GitManager instance."""
    global _git_manager
    if _git_manager is None:
        _git_manager = GitManager(repo_path)
    return _git_manager


def get_maintenance_checker(base_path: str = ".") -> MaintenanceChecker:
    """Global MaintenanceChecker instance."""
    global _maintenance_checker
    if _maintenance_checker is None:
        _maintenance_checker = MaintenanceChecker(base_path)
    return _maintenance_checker
