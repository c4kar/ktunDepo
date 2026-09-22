#!/usr/bin/env python3
"""
ktunDepo STEM Multi-Department Manifest Generator
Çalıştır: python scripts/generate-manifest.py
ktunDepo veya ktunEcoSystem kök klasöründen çalıştırılabilir.
"""
import os
import json
import hashlib
import pathlib
import subprocess
from datetime import datetime, timezone

ALL_STEM_DEPTS = ["EEM", "CENG", "MECH", "MKT", "CIVIL", "CHEM", "IE", "GEO"]

# Common STEM courses mapping: which departments share this course?
COMMON_COURSES = {
    "fizik 1": ALL_STEM_DEPTS,
    "fizik 2": ALL_STEM_DEPTS,
    "matematik 1": ALL_STEM_DEPTS,
    "matematik 2": ALL_STEM_DEPTS,
    "kimya": ALL_STEM_DEPTS,
    "genel kimya": ALL_STEM_DEPTS,
    "lineer cebir": ALL_STEM_DEPTS,
    "diferansiyel denklemler": ALL_STEM_DEPTS,
    "bilgisayar programlama 1": ALL_STEM_DEPTS,
    "bilgisayar programlama 2": ["EEM", "CENG", "MECH", "MKT"],
    "bilgisayar destekli teknik resim": ["EEM", "MECH", "CIVIL", "MKT", "IE"],
    "ataturk ilkeleri ve inkilap tarihi": ALL_STEM_DEPTS,
    "is sagligi ve guvenligi 1": ALL_STEM_DEPTS,
    "is sagligi ve guvenligi 2": ALL_STEM_DEPTS,
    "muhendislik mekanigi": ["EEM", "MECH", "CIVIL", "MKT"],
    "olasilik ve istatistik": ["EEM", "CENG", "MECH", "MKT", "CIVIL", "IE"],
    "sayisal yontemler": ["EEM", "CENG", "MECH", "CIVIL", "CHEM", "IE"],
}

ALLOWED_EXTENSIONS = {".pdf", ".md", ".docx", ".pptx", ".zip", ".png", ".jpg", ".jpeg", ".mp4"}
GITHUB_RAW = "https://raw.githubusercontent.com/c4kar/ktunDepo/main"


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


def slugify(text: str) -> str:
    cleaned = ""
    for c in text:
        if c in "ıiİI":
            cleaned += "I"
        elif c in "öÖ":
            cleaned += "O"
        elif c in "üÜ":
            cleaned += "U"
        elif c in "çÇ":
            cleaned += "C"
        elif c in "şŞ":
            cleaned += "S"
        elif c in "ğĞ":
            cleaned += "G"
        elif c.isalnum():
            cleaned += c.upper()
        else:
            cleaned += "_"
    parts = [p for p in cleaned.split("_") if p]
    return "_".join(parts)


def resolve_roots():
    cur = pathlib.Path(".").resolve()
    # Check if we are inside ktunDepo or ktunEcoSystem
    if (cur / "ktunDepo").is_dir():
        depo_root = cur / "ktunDepo"
        materials_root = cur / "storage" / "materials"
    else:
        depo_root = cur
        materials_root = cur.parent / "storage" / "materials"
    return depo_root, materials_root


def main():
    depo_root, materials_root = resolve_roots()
    print(f"Tarama kök dizini: {depo_root}")

    files = []
    seen_paths = set()

    # Search candidates: EEM folder inside ktunDepo, and storage/materials if exists
    search_dirs = [depo_root / "EEM"]
    if materials_root.exists():
        search_dirs.append(materials_root)

    for search_dir in search_dirs:
        if not search_dir.exists():
            continue

        for f in sorted(search_dir.rglob("*")):
            if f.is_dir():
                continue
            if f.suffix.lower() not in ALLOWED_EXTENSIONS:
                continue
            if any(p.startswith(".") for p in f.parts):
                continue
            if "manifest.json" in f.name:
                continue

            rel_to_depo = os.path.relpath(f, depo_root).replace("\\", "/")
            if rel_to_depo in seen_paths:
                continue
            seen_paths.add(rel_to_depo)

            parts = list(f.parts)
            # Detect department & semester
            department = "EEM"
            semester = "other"
            course = "genel"

            # Check if under EEM-X
            for i, p in enumerate(parts):
                if p.startswith("EEM-") and p[4:].isdigit():
                    department = "EEM"
                    semester = p
                    if i + 1 < len(parts) - 1:
                        course = parts[i + 1]
                    break
                elif p in ALL_STEM_DEPTS and p != "EEM":
                    department = p
                    if i + 1 < len(parts) - 1:
                        course = parts[i + 1]
                    break
                elif p == "STEM_Ortak":
                    department = "COMMON"
                    if i + 1 < len(parts) - 1:
                        course = parts[i + 1]
                    break

            norm_course = course.replace("-", " ").replace("_", " ").lower().strip()
            course_slug = slugify(norm_course)

            # Check if this course is common across departments
            is_common = False
            applicable_depts = [department]

            for common_key, depts in COMMON_COURSES.items():
                if common_key in norm_course or norm_course in common_key:
                    is_common = True
                    applicable_depts = depts
                    break

            try:
                added_at = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc).isoformat()
            except Exception:
                added_at = datetime.now(timezone.utc).isoformat()

            files.append({
                "id": make_id(rel_to_depo),
                "path": rel_to_depo,
                "name": f.stem.replace("-", " ").replace("_", " "),
                "department": department,
                "semester": semester,
                "course": norm_course,
                "course_slug": course_slug,
                "is_common": is_common,
                "applicable_departments": applicable_depts,
                "ext": f.suffix.lstrip(".").lower(),
                "type": derive_type(f.suffix.lower()),
                "size_kb": round(f.stat().st_size / 1024, 1),
                "added_at": added_at,
                "download_url": f"{GITHUB_RAW}/{rel_to_depo}",
            })

    # Stats
    common_count = sum(1 for x in files if x["is_common"])
    dept_stats = {}
    for x in files:
        dept_stats[x["department"]] = dept_stats.get(x["department"], 0) + 1

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "file_count": len(files),
        "common_course_files": common_count,
        "departments_covered": ALL_STEM_DEPTS,
        "department_distribution": dept_stats,
        "files": files
    }

    manifest_output = depo_root / "manifest.json"
    with open(manifest_output, "w", encoding="utf-8") as fp:
        json.dump(manifest, fp, ensure_ascii=False, indent=2)

    print(f"✓ Çoklu STEM manifest.json başarıyla oluşturuldu:")
    print(f"  • Toplam dosya: {len(files)}")
    print(f"  • STEM Ortak havuz dosyası: {common_count}")
    print(f"  • Bölüm dağılımı: {dept_stats}")


if __name__ == "__main__":
    main()
