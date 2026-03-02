from __future__ import annotations

import hashlib
import json
from typing import Any

def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def canonical_json_bytes(obj: Any) -> bytes:
    # Stable object key ordering; does not reorder arrays.
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
