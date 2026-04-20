from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Tuple

import pandas as pd


REAL_CACHE_ROOT = Path("data") / "real_cache"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_county_fips(county_fips: str) -> str:
    s = str(county_fips).strip()
    if not s.isdigit():
        raise ValueError(f"county_fips must be digits, got: {county_fips!r}")
    if len(s) != 5:
        raise ValueError(f"county_fips must be 5 digits (state+county), got: {county_fips!r}")
    return s


def split_county_fips(county_fips: str) -> Tuple[str, str]:
    c = normalize_county_fips(county_fips)
    return c[:2], c[2:]


@dataclass(frozen=True)
class DatasetRef:
    county_fips: str
    source_id: str
    quantity_id: str
    filename: str = "data.csv"

    @property
    def dir(self) -> Path:
        c = normalize_county_fips(self.county_fips)
        return REAL_CACHE_ROOT / "counties" / c / self.source_id / self.quantity_id

    @property
    def data_path(self) -> Path:
        return self.dir / self.filename

    @property
    def response_path(self) -> Path:
        return self.dir / "response.json"

    @property
    def manifest_path(self) -> Path:
        return self.dir / "manifest.json"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, obj: Any) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def write_dataset(
    ref: DatasetRef,
    df: pd.DataFrame,
    *,
    response_json: Optional[Any] = None,
    request: Optional[dict[str, Any]] = None,
    schema: Optional[dict[str, Any]] = None,
    notes: Optional[str] = None,
    overwrite: bool = True,
) -> Path:
    """
    Write a cached dataset with neighboring manifest.json and optional response.json.
    Returns the written data.csv path.
    """
    ensure_dir(ref.dir)

    if (not overwrite) and ref.data_path.exists() and ref.manifest_path.exists():
        return ref.data_path

    df.to_csv(ref.data_path, index=False)

    if response_json is not None:
        write_json(ref.response_path, response_json)

    manifest = {
        "version": 1,
        "county_fips": normalize_county_fips(ref.county_fips),
        "source_id": ref.source_id,
        "quantity_id": ref.quantity_id,
        "retrieved_at_utc": utc_now_iso(),
        "files": {
            "data": str(ref.data_path.as_posix()),
            "response": str(ref.response_path.as_posix()) if response_json is not None else None,
        },
        "request": request or None,
        "schema": schema
        or {
            "columns": list(df.columns),
        },
        "row_count": int(len(df)),
        "sha256": {
            "data": sha256_file(ref.data_path),
        },
        "notes": notes,
    }
    write_json(ref.manifest_path, manifest)
    return ref.data_path

