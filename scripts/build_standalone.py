#!/usr/bin/env python3
"""Build standalone offline HTML converter."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CXQ_PATH = ROOT / "app" / "data" / "cxq_mapping.json"
TEMPLATE_PATH = Path(__file__).resolve().parent / "standalone_template.html"
OUT_PATH = ROOT / "dist" / "Mindbox-to-SFMC-Converter-v3-Sanofi.html"
LEGACY_PATH = ROOT / "dist" / "Mindbox-to-SFMC-Converter.html"


def main() -> None:
    cxq = json.loads(CXQ_PATH.read_text(encoding="utf-8"))
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    html = template.replace("__CXQ_JSON__", json.dumps(cxq, ensure_ascii=False))
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(html, encoding="utf-8")
    LEGACY_PATH.write_text(html, encoding="utf-8")
    size_kb = OUT_PATH.stat().st_size // 1024
    print(f"Built {OUT_PATH} ({size_kb} KB)")
    print(f"Also updated {LEGACY_PATH}")


if __name__ == "__main__":
    main()
