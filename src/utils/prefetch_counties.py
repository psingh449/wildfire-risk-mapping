"""
Counties that are marked as UI prefetch targets (bold in dropdown) live in
`data/county_manifest.json` under `prefetched_county_ids`.

Use these IDs for the first full `data/real_cache/` import pass so packaged demo
counties have caches before running the pipeline per county.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_prefetch_county_fips(
    manifest_path: Path | None = None,
) -> List[str]:
    """
    Return normalized 5-digit county FIPS strings from county_manifest.json.
    """
    path = manifest_path or (_repo_root() / "data" / "county_manifest.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    raw = data.get("prefetched_county_ids") or []
    out: List[str] = []
    for x in raw:
        s = str(x).strip()
        if len(s) == 4:
            s = s.zfill(5)
        elif len(s) > 5:
            s = s[-5:]
        out.append(s)
    return out
