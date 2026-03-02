from __future__ import annotations

import json
from typing import Dict, Any, List

from .fixture import load_fixture

def diff_fixtures(a_path: str, b_path: str) -> Dict[str, Any]:
    a = load_fixture(a_path)
    b = load_fixture(b_path)

    a_art = a.manifest.get("artifacts", {})
    b_art = b.manifest.get("artifacts", {})

    a_set = set(a_art.keys())
    b_set = set(b_art.keys())

    added = sorted(list(b_set - a_set))
    removed = sorted(list(a_set - b_set))
    common = sorted(list(a_set & b_set))

    # For common artifacts, compare expected hashes (should match key); mainly compare byte_length
    changed_meta = []
    for sha in common:
        if a_art.get(sha) != b_art.get(sha):
            changed_meta.append({"sha": sha, "a": a_art.get(sha), "b": b_art.get(sha)})

    # Boundary drift localization: compare stage_boundaries output hashes per stage index
    def boundary_map(man):
        m = {}
        for sb in man.get("stage_boundaries", []):
            m[int(sb["stage_index"])] = sb.get("output_sha256")
        return m

    am = boundary_map(a.manifest)
    bm = boundary_map(b.manifest)
    all_idx = sorted(set(am.keys()) | set(bm.keys()))
    first_drift = None
    boundary_diffs = []
    for i in all_idx:
        if am.get(i) != bm.get(i):
            boundary_diffs.append({"stage_index": i, "a_output": am.get(i), "b_output": bm.get(i)})
            if first_drift is None:
                first_drift = i

    return {
        "a_pipeline_run_id": a.manifest.get("pipeline_run_id"),
        "b_pipeline_run_id": b.manifest.get("pipeline_run_id"),
        "added_artifacts": added,
        "removed_artifacts": removed,
        "changed_metadata": changed_meta,
        "boundary_diffs": boundary_diffs,
        "first_boundary_drift_stage_index": first_drift
    }
