"""
Workspace isolation
=====================
Har user (ya guest) ka apna folder: WORKSPACE_ROOT/{owner_id}/...
`owner_id` authenticated users ke liye unka `username` hai, demo/guest ke
liye server-generated `guest_<uuid>` id.

Security invariant: koi bhi function jo ek "relative path" leta hai
(zip ke andar ka entry name ho, ya LLM ka diya hua folder_name), use
hamesha `safe_join()` se resolve karo. Ye function guarantee karta hai
ki resolved absolute path `WORKSPACE_ROOT/{owner_id}/` ke andar hi rahe —
`..`, absolute paths, ya symlink tricks se bahar nikalna (zip-slip /
path traversal) possible nahi hoga.
"""

from __future__ import annotations

import shutil
import time
import zipfile
from pathlib import Path
from typing import Optional

ROOT_DIR = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = ROOT_DIR / "workspace"
WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)

MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB, confirmed with user


class WorkspaceSecurityError(Exception):
    pass


def owner_dir(owner_id: str) -> Path:
    """Ensures and returns WORKSPACE_ROOT/{owner_id} (creates it if missing)."""
    if not owner_id or "/" in owner_id or ".." in owner_id or "\\" in owner_id:
        raise WorkspaceSecurityError("Invalid owner id")
    d = WORKSPACE_ROOT / owner_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def safe_join(owner_id: str, relative_path: str) -> Path:
    """
    Resolve `relative_path` inside the owner's workspace, raising
    WorkspaceSecurityError if the result would escape that directory.
    """
    base = owner_dir(owner_id).resolve()
    # Strip leading slashes so "/etc/passwd" is treated as relative, not absolute.
    cleaned = str(relative_path).lstrip("/\\")
    target = (base / cleaned).resolve()
    if target != base and base not in target.parents:
        raise WorkspaceSecurityError(f"Path traversal blocked for '{relative_path}'")
    return target


def extract_zip_safely(zip_bytes: bytes, owner_id: str, project_name: str) -> tuple[Path, list[str]]:
    """
    Extracts an in-memory zip into WORKSPACE_ROOT/{owner_id}/{project_name}/.
    Every entry is validated with safe_join before being written — this is
    what stops "zip-slip" (a zip crafted with entries like '../../etc/x').
    Malicious/escaping entries are skipped individually (not fatal for the
    whole upload); returns (extracted_dir, list_of_skipped_entry_names).
    """
    import io

    if len(zip_bytes) > MAX_UPLOAD_BYTES:
        raise ValueError(f"Zip file too large (max {MAX_UPLOAD_BYTES // (1024*1024)}MB)")

    dest_root = safe_join(owner_id, project_name)
    dest_root.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        total_uncompressed = sum(zi.file_size for zi in zf.infolist())
        if total_uncompressed > MAX_UPLOAD_BYTES * 4:
            # Basic zip-bomb guard: extracted size wildly larger than the archive itself.
            raise ValueError("Zip contents too large after extraction")

        skipped = []
        for zi in zf.infolist():
            if zi.is_dir():
                continue
            try:
                # project_name is already the root; entries inside are relative to it.
                entry_path = safe_join(owner_id, f"{project_name}/{zi.filename}")
            except WorkspaceSecurityError:
                skipped.append(zi.filename)
                continue
            entry_path.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(zi) as src, open(entry_path, "wb") as dst:
                shutil.copyfileobj(src, dst)

    return dest_root, skipped


def zip_folder_for_download(owner_id: str, project_name: str) -> Path:
    """Zips WORKSPACE_ROOT/{owner_id}/{project_name} and returns the path to the .zip file."""
    src_dir = safe_join(owner_id, project_name)
    if not src_dir.exists() or not src_dir.is_dir():
        raise FileNotFoundError(f"Project '{project_name}' not found")

    out_path = owner_dir(owner_id) / f"_download_{project_name}.zip"
    if out_path.exists():
        out_path.unlink()

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in src_dir.rglob("*"):
            if file_path.is_file():
                zf.write(file_path, arcname=str(file_path.relative_to(src_dir)))

    return out_path


def list_projects(owner_id: str) -> list[str]:
    base = owner_dir(owner_id)
    return sorted(p.name for p in base.iterdir() if p.is_dir())


def delete_project(owner_id: str, project_name: str) -> None:
    target = safe_join(owner_id, project_name)
    if target.exists():
        shutil.rmtree(target)


def cleanup_stale_guest_workspaces(max_age_seconds: int = 24 * 60 * 60) -> list[str]:
    """
    Deletes guest_* workspace folders older than max_age_seconds.
    Call this periodically (e.g. from a FastAPI background task / scheduler).
    """
    removed = []
    now = time.time()
    for entry in WORKSPACE_ROOT.iterdir():
        if not entry.is_dir() or not entry.name.startswith("guest_"):
            continue
        try:
            age = now - entry.stat().st_mtime
        except FileNotFoundError:
            continue
        if age > max_age_seconds:
            shutil.rmtree(entry, ignore_errors=True)
            removed.append(entry.name)
    return removed