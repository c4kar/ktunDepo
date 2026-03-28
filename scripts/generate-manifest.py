#!/usr/bin/env python3
"""
ktunDepo manifest generator
Çalıştır: python scripts/generate-manifest.py
ktunDepo'nun root klasöründen çalıştırılmalıdır.
"""
import os, json, hashlib, pathlib
from datetime import datetime, timezone

ROOT = pathlib.Path(".")
GITHUB_RAW = "https://raw.githubusercontent.com/c4kar/ktunDepo/main"

ALLOWED_EXTENSIONS = {".pdf", ".md", ".docx", ".pptx", ".zip", ".png", ".jpg", ".jpeg", ".mp4"}
SEMESTER_PATTERN = ["EEM-1", "EEM-2", "EEM-3", "EEM-4", "EEM-5", "EEM-6", "EEM-7", "EEM-8"]

def derive_type(ext: str) -> str:
    return {
        ".pdf": "pdf",
        ".md": "note",
        ".docx": "note",
        ".pptx": "slides",
        ".zip": "archive",
        ".png": "image",
        ".jpg": "image",
        ".jpeg": "image",
        ".mp4": "other",
    }.get(ext, "other")

def make_id(path: str) -> str:
    return hashlib.sha1(path.encode()).hexdigest()[:12]

files = []
for f in sorted(ROOT.rglob("*")):
    if f.is_dir():
        continue
    if f.suffix not in ALLOWED_EXTENSIONS:
        continue
    if any(p.startswith(".") for p in f.parts):
        continue
    if "manifest.json" in f.name:
        continue

    parts = list(f.parts)
    semester = next((p for p in parts if p in SEMESTER_PATTERN), "other")
    course = parts[parts.index(semester) + 1] if semester in parts and parts.index(semester) + 1 < len(parts) - 1 else "genel"
    rel_path = str(f).replace("\\", "/")
    
    # Try to get git commit date, fall back to mtime
    try:
        import subprocess
        git_date = subprocess.check_output(
            ["git", "log", "-1", "--format=%aI", "--", str(f)],
            text=True
        ).strip()
        added_at = git_date or datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc).isoformat()
    except Exception:
        added_at = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc).isoformat()

    files.append({
        "id": make_id(rel_path),
        "path": rel_path,
        "name": f.stem.replace("-", " ").replace("_", " "),
        "semester": semester,
        "course": course.replace("-", " ").replace("_", " "),
        "ext": f.suffix.lstrip(".").lower(),
        "type": derive_type(f.suffix.lower()),
        "size_kb": round(f.stat().st_size / 1024, 1),
        "added_at": added_at,
        "download_url": f"{GITHUB_RAW}/{rel_path}",
    })

manifest = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "file_count": len(files),
    "files": files
}

output = ROOT / "manifest.json"
with open(output, "w", encoding="utf-8") as fp:
    json.dump(manifest, fp, ensure_ascii=False, indent=2)

print(f"✓ manifest.json oluşturuldu: {len(files)} dosya")
