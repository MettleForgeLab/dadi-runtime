from __future__ import annotations

import json
import os
import zipfile
from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple, List

from .hashing import sha256_hex

MANIFEST_NAME = "fixture_manifest.json"

@dataclass
class Fixture:
    root: str  # directory containing manifest + artifacts/
    manifest: Dict[str, Any]

def load_fixture(path: str, extract_to: Optional[str] = None) -> Fixture:
    if os.path.isdir(path):
        manifest_path = os.path.join(path, MANIFEST_NAME)
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        return Fixture(path, manifest)

    if not zipfile.is_zipfile(path):
        raise ValueError("Fixture must be a directory or zip")

    extract_to = extract_to or (path + ".dir")
    if not os.path.exists(extract_to):
        os.makedirs(extract_to, exist_ok=True)
        with zipfile.ZipFile(path, "r") as z:
            z.extractall(extract_to)

    manifest_path = os.path.join(extract_to, MANIFEST_NAME)
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    return Fixture(extract_to, manifest)

def write_fixture(out_path: str, manifest: Dict[str, Any], artifacts: Dict[str, bytes]) -> str:
    # out_path may be .zip or directory
    if out_path.endswith(".zip"):
        tmp_dir = out_path + ".dir"
        os.makedirs(os.path.join(tmp_dir, "artifacts"), exist_ok=True)
        with open(os.path.join(tmp_dir, MANIFEST_NAME), "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, sort_keys=True)
            f.write("\n")
        for sha, b in artifacts.items():
            with open(os.path.join(tmp_dir, "artifacts", sha), "wb") as f:
                f.write(b)
        with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
            for root, _, files in os.walk(tmp_dir):
                for fn in files:
                    full = os.path.join(root, fn)
                    rel = os.path.relpath(full, tmp_dir)
                    z.write(full, arcname=rel)
        return out_path

    os.makedirs(os.path.join(out_path, "artifacts"), exist_ok=True)
    with open(os.path.join(out_path, MANIFEST_NAME), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
        f.write("\n")
    for sha, b in artifacts.items():
        with open(os.path.join(out_path, "artifacts", sha), "wb") as f:
            f.write(b)
    return out_path
