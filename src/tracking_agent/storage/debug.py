from __future__ import annotations
from pathlib import Path


def save_debug_html(base_dir: str, name: str, html: str) -> str:
    """Persist a fetched page for offline inspection (ТЗ §11 debug mode)."""
    safe = "".join(c if (c.isalnum() or c in "._-") else "_" for c in name)
    d = Path(base_dir)
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{safe}.html"
    path.write_text(html, encoding="utf-8")
    return str(path)
