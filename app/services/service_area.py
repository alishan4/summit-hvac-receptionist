from __future__ import annotations

import re

from app.company import CompanyConfig

_ZIP_RE = re.compile(r"\b(\d{5})(?:-\d{4})?\b")


def normalize_zip(raw: str) -> str | None:
    """Accepts '80202', '80202-1234', ' 80202 ', '8 0 2 0 2' (spoken digits). None if invalid."""
    compact = re.sub(r"[\s.\-]", "", raw) if re.fullmatch(r"[\d\s.\-]+", raw.strip()) else raw
    if re.fullmatch(r"\d{5}(\d{4})?", compact):
        return compact[:5]
    m = _ZIP_RE.search(raw)
    return m.group(1) if m else None


def in_service_area(cfg: CompanyConfig, raw_zip: str) -> tuple[bool, str | None]:
    z = normalize_zip(raw_zip)
    if z is None:
        return False, None
    return z in set(cfg.service_area.zips), z
