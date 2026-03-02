import os, json, base64, time, uuid, hmac, hashlib
import psycopg
import requests

API_BASE = os.getenv("API_BASE", "http://localhost:8000")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://dadi:dadi@localhost:5432/dadi")
JWT_SECRET = os.getenv("DADI_JWT_HS256_SECRET", "dev-secret")

def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")

def make_jwt(secret: str, payload: dict) -> str:
    header = {"alg":"HS256","typ":"JWT"}
    h = b64url(json.dumps(header, separators=(",",":"), sort_keys=True).encode("utf-8"))
    p = b64url(json.dumps(payload, separators=(",",":"), sort_keys=True).encode("utf-8"))
    signing_input = f"{h}.{p}".encode("ascii")
    sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    s = b64url(sig)
    return f"{h}.{p}.{s}"

def auth_headers(tenant: str, scopes: str):
    token = get_idp_token(tenant, scopes)
    return {"Authorization": f"Bearer {token}"}

def b64(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")

def canonical_json_bytes(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

def post_artifact(headers, artifact_type, schema_version, obj, media_type="application/json", canonical=True, canonical_format="json_c14n_v1"):
    content = canonical_json_bytes(obj)
    payload = {
        "meta": {
            "artifact_type": artifact_type,
            "media_type": media_type,
            "canonical": canonical,
            "canonical_format": canonical_format,
            "schema_version": schema_version
        },
        "content_b64": b64(content)
    }
    r = requests.post(f"{API_BASE}/artifacts", json=payload, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()["sha256"]


def get_idp_token(tenant: str, scope: str) -> str:
    # Requires idp stub at http://localhost:9000 (host) or http://idp:9000 (docker network).
    import requests
    idp = os.getenv("IDP_URL", "http://localhost:9000").rstrip("/")
    r = requests.post(f"{idp}/token", json={"tenant_id": tenant, "scope": scope, "sub": "seed-demo"})
    r.raise_for_status()
    return r.json()["access_token"]

def wait_gateway()

    # IDP token (tenant_a) for UI/dev use
    try:
        tkn = get_idp_token('tenant_a', 'artifact:read_bytes deliverable:download_bundle')
        print('IDP token (tenant_a):', tkn)
    except Exception as e:
        print('NOTE: failed to fetch IDP token:', str(e))
:
    for _ in range(30):
        try:
            r = requests.get(f"{API_BASE}/health", timeout=2)
            if r.ok:
                return
        except Exception:
            time.sleep(1)


def write_seed_state(state: dict):
    # Write to repo root relative to this script: ../../../.seed_state.json
    import os, json
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    p = os.path.join(root, ".seed_state.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, sort_keys=True)
        f.write("\n")
    print("Wrote seed state:", p)

def main():
    wait_gateway()

    # IDP token (tenant_a) for UI/dev use
    try:
        tkn = get_idp_token('tenant_a', 'artifact:read_bytes deliverable:download_bundle')
        print('IDP token (tenant_a):', tkn)
    except Exception as e:
        print('NOTE: failed to fetch IDP token:', str(e))


    # Seed pipeline rows directly (tenant scoped)
    tenant_a = "tenant_a"
    tenant_b = "tenant_b"

    pipeline_id = str(uuid.uuid4())
    run_a = str(uuid.uuid4())
    run_b = str(uuid.uuid4())

    with psycopg.connect(DATABASE_URL) as c:
        with c.transaction():
            c.execute("INSERT INTO pipelines (pipeline_id, name) VALUES (%s,%s)", (pipeline_id, "demo_pipeline"))
            c.execute("INSERT INTO pipeline_runs (tenant_id, pipeline_run_id, pipeline_id, status) VALUES (%s,%s,%s,'running')", (tenant_a, run_a, pipeline_id))
            c.execute("INSERT INTO pipeline_runs (tenant_id, pipeline_run_id, pipeline_id, status) VALUES (%s,%s,%s,'running')", (tenant_b, run_b, pipeline_id))

    # Tenant A creates an artifact
    headers_a = auth_headers(tenant_a, "artifact:read_bytes")
    headers_b = auth_headers(tenant_b, "artifact:read_bytes")

    docpack = {
        "schema_version": "docpack-v1",
        "raw_sha256": "0"*64,
        "pages": [{"page_num":1,"blocks":[{"block_id":"b1","type":"text","text":"Tenant A demo."}]}]
    }
    doc_sha_a = post_artifact(headers_a, "doc/normalized/docpack-v1", "docpack-v1", docpack)

    # Cross-tenant denial: tenant B should not find tenant A artifact metadata
    r = requests.get(f"{API_BASE}/artifacts/{doc_sha_a}", headers=headers_b, timeout=30)
    assert r.status_code == 404, f"Expected 404 cross-tenant, got {r.status_code}"

    # Create minimal stage_run for tenant A so planner can match
    prompt_sha = post_artifact(headers_a, "prompt/bundle/v1", "prompt_bundle-v1", {"schema_version":"prompt_bundle-v1","v":"demo"})
    toolchain_sha = post_artifact(headers_a, "toolchain/manifest/v1", "toolchain_manifest-v1", {"schema_version":"toolchain_manifest-v1","v":"demo"})
    stage_input = {
        "schema_version":"stage_input-v1",
        "stage":{"index":2,"name":"02_classify","schema_version":"v1"},
        "docpack_sha256": doc_sha_a,
        "prior_outputs": [],
        "prompt_bundle_sha256": prompt_sha,
        "toolchain_manifest_sha256": toolchain_sha,
        "params": {}
    }
    stage_in_sha = post_artifact(headers_a, "pipeline/stage/02/input-v1", "stage_input-v1", stage_input)
    stage02_out = {
        "schema_version":"stage02-output-v1",
        "stage":{"index":2,"name":"02_classify","schema_version":"v1"},
        "results":{
            "doc_profile":{"doc_types":["unknown"],"confidence":0.0},
            "section_map": [],
            "content_index":{"tables":[],"figures":[],"key_blocks":[]},
            "extraction_plan":{"targets":["unknown"],"priority":[{"target":"unknown","importance":"low"}]}
        },
        "citations": [],
        "provenance":{"input_sha256": stage_in_sha, "prompt_bundle_sha256": prompt_sha}
    }
    stage_out_sha = post_artifact(headers_a, "pipeline/stage/02/output-v1", "stage02-output-v1", stage02_out)

    # Insert stage_run row for tenant A
    stage_run_id = str(uuid.uuid4())
    with psycopg.connect(DATABASE_URL) as c:
        with c.transaction():
            c.execute(
                "INSERT INTO stage_runs (tenant_id, stage_run_id, pipeline_run_id, stage_index, stage_name, stage_schema_version, toolchain_manifest_sha256, prompt_bundle_sha256, input_artifact_sha256, output_artifact_sha256, status) "
                "VALUES (%s,%s,%s,2,'02_classify','v1',%s,%s,%s,%s,'success')",
                (tenant_a, stage_run_id, run_a, toolchain_sha, prompt_sha, stage_in_sha, stage_out_sha)
            )
            c.execute("UPDATE pipeline_runs SET status='success', completed_at=now() WHERE tenant_id=%s AND pipeline_run_id=%s", (tenant_a, run_a))

    # Plan regeneration (tenant A)
    plan = requests.post(f"{API_BASE}/plan/regenerate", json={"old_prompt_sha256": prompt_sha, "new_prompt_sha256":"f"*64}, headers=headers_a, timeout=30).json()
    plan_id = plan["plan_id"]
    explain = requests.get(f"{API_BASE}/plan/{plan_id}/explain", headers=headers_a, timeout=30).json()

    
    

    # --- Stage 06 DOCX render demo via orchestrator (tenant A) ---
    try:
        from io import BytesIO
        from docx import Document
    except Exception:
        print("NOTE: python-docx not installed; skipping DOCX render demo.")
    else:
        report_model = {
            "schema_version": "report_model-v1",
            "report": {
                "title": "Demo Analyst Report",
                "summary": [{"type":"bullet","text":"Revenue FY2024 is $10M.","citations":[]}],
                "sections": [
                    {"section_id":"sec1","heading":"Financial Overview","blocks":[{"type":"paragraph","text":"Demo content.","citations":[]}]}
                ]
            }
        }
        report_model_sha = post_artifact(headers_a, "report/model/v1", "report_model-v1", report_model)

        doc = Document()
        doc.add_paragraph("Template Header")
        buf = BytesIO()
        doc.save(buf)
        template_bytes = buf.getvalue()

        payload = {
            "meta": {
                "artifact_type": "report/template/docx-v1",
                "media_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "canonical": False,
                "canonical_format": None,
                "schema_version": None
            },
            "content_b64": b64(template_bytes)
        }
        rtpl = requests.post(f"{API_BASE}/artifacts", json=payload, headers=headers_a, timeout=30)
        rtpl.raise_for_status()
        template_sha = rtpl.json()["sha256"]

        render_input = {
            "schema_version": "render_input-v1",
            "report_model_sha256": report_model_sha,
            "template_sha256": template_sha,
            "render_params": {"format":"docx","style":"analyst_v1"},
            "toolchain_manifest_sha256": "0"*64
        }
        render_input_sha = post_artifact(headers_a, "report/render/input-v1", "render_input-v1", render_input)

        # Run orchestrator Stage 06 (tenant-scoped, RLS)
        import sys
        sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "..", "services", "orchestrator"))
        sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "..", "services", "renderer"))
        os.environ["DADI_TENANT_ID"] = tenant_a  # required by orchestrator DB helpers

        from dadi_orchestrator.orchestrator import Orchestrator, StageSpec
        from dadi_renderer.stage06_handler import stage06_render_docx

        orch = Orchestrator(schemas_path=os.path.join(os.path.dirname(__file__), "..", "..", "..", "schemas"))

        stage06 = StageSpec(
            index=6,
            name="06_render",
            schema_version="v1",
            output_schema_version="render_docx_output-v1",
            handler=stage06_render_docx,
            uses_prompt=False
        )

        # First run (cache miss)
        outs1 = orch.run(
            pipeline_run_id=run_a,
            docpack_sha256=doc_sha_a,
            toolchain_manifest_sha256=toolchain_sha,
            prompt_bundle_sha256=None,
            stages=[stage06],
            params={"render_input_sha256": render_input_sha}
        )

        # Second run (should be cache hit, producing same output hash)
        outs2 = orch.run(
            pipeline_run_id=run_a,
            docpack_sha256=doc_sha_a,
            toolchain_manifest_sha256=toolchain_sha,
            prompt_bundle_sha256=None,
            stages=[stage06],
            params={"render_input_sha256": render_input_sha}
        )

        print("DOCX orchestrated render complete:", {"render_input_sha256": render_input_sha, "stage06_output_sha1": outs1[-1], "stage06_output_sha2": outs2[-1]})


        # --- Create deliverable record (tenant A) ---
        try:
            deliverable = requests.post(
                f"{API_BASE}/deliverables",
                json={"pipeline_run_id": run_a, "status": "draft"},
                headers=headers_a,
                timeout=30,
            ).json()
            print("Deliverable created:", {"deliverable_id": deliverable.get("deliverable_id"), "status": deliverable.get("status"), "docx_sha256": deliverable.get("docx_sha256")})

# --- Finalize deliverable before bundling (policy gate) ---
try:
    did = deliverable.get("deliverable_id")
    if did:
        frest = requests.post(f"{API_BASE}/deliverables/{did}/finalize", headers=headers_a, timeout=30)
        print("Deliverable finalized:", {"deliverable_id": did, "status": "final", "http": frest.status_code})
except Exception as e:
    print("NOTE: deliverable finalize failed:", str(e))

        # --- Create delivery bundle + signed manifest (tenant A) ---
        try:
            bresp = requests.post(
                f"{API_BASE}/deliverables/{deliverable.get('deliverable_id')}/bundle",
                headers=headers_a,
                timeout=30,
            ).json()
            print("Bundle created:", {"bundle_id": bresp.get("bundle_id"), "manifest_sha256": bresp.get("manifest_artifact_sha256"), "bundle_sha256": bresp.get("bundle_artifact_sha256")})

# --- Self-verify bundle (tenant A) ---
try:
    manifest_sha = bresp.get("manifest_artifact_sha256")
    bundle_sha = bresp.get("bundle_artifact_sha256")
    if manifest_sha and bundle_sha:
        vresp = requests.post(
            f"{API_BASE}/deliverables/{deliverable.get('deliverable_id')}/bundle/verify",
            json={"manifest_artifact_sha256": manifest_sha},
            headers=headers_a,
            timeout=30,
        ).json()
        print("Bundle verify (server):", vresp)

        zbytes = requests.get(
            f"{API_BASE}/artifacts/{bundle_sha}/content",
            headers=headers_a,
            timeout=30
        ).content

        import zipfile, io, hashlib

        zf = zipfile.ZipFile(io.BytesIO(zbytes), "r")
        manifest_bytes = zf.read("manifest.json")
        manifest_obj = json.loads(manifest_bytes.decode("utf-8"))

        expected = set()
        for a in manifest_obj.get("artifacts", []) or []:
            if isinstance(a, dict) and isinstance(a.get("sha256"), str):
                expected.add(a["sha256"])

        mismatches = []
        missing_in_manifest = []
        for name in zf.namelist():
            if not name.startswith("artifacts/"):
                continue
            sha = name.split("/", 1)[1]
            data = zf.read(name)
            h = hashlib.sha256(data).hexdigest()
            if h != sha:
                mismatches.append({"entry": name, "computed": h, "expected": sha})
            if sha not in expected:
                missing_in_manifest.append(sha)

        zip_artifacts = {n.split("/",1)[1] for n in zf.namelist() if n.startswith("artifacts/")}
        missing_in_zip = sorted(list(expected - zip_artifacts))

        report = {
            "manifest_sha256": manifest_sha,
            "bundle_sha256": bundle_sha,
            "mismatches": mismatches,
            "missing_in_manifest": sorted(list(set(missing_in_manifest))),
            "missing_in_zip": missing_in_zip,
            "ok": (len(mismatches) == 0 and len(missing_in_manifest) == 0 and len(missing_in_zip) == 0)
        }
        print("Bundle self-verify (client):", json.dumps(report, indent=2))
except Exception as e:
    print("NOTE: bundle self-verification failed:", str(e))
        except Exception as e:
            print("NOTE: bundle creation failed:", str(e))
        except Exception as e:
            print("NOTE: deliverable creation failed:", str(e))

print("Set env for tests: DADI_SEEDED_RUN_ID=", run_a)


# --- Persist seed state for tests ---
try:
    seed_state = {
        "tenant_a": tenant_a,
        "tenant_b": tenant_b,
        "pipeline_id": pipeline_id,
        "pipeline_run_id": run_a,
        "docpack_sha_a": doc_sha_a,
    }
    # Optional fields if they exist
    if "did" in locals():
        seed_state["deliverable_id"] = did
    if "deliverable" in locals() and isinstance(deliverable, dict) and deliverable.get("deliverable_id"):
        seed_state["deliverable_id"] = deliverable.get("deliverable_id")
    if "bresp" in locals() and isinstance(bresp, dict):
        if bresp.get("bundle_id"):
            seed_state["bundle_id"] = bresp.get("bundle_id")
        if bresp.get("manifest_artifact_sha256"):
            seed_state["manifest_artifact_sha256"] = bresp.get("manifest_artifact_sha256")
        if bresp.get("bundle_artifact_sha256"):
            seed_state["bundle_artifact_sha256"] = bresp.get("bundle_artifact_sha256")
    if "plan_id" in locals():
        seed_state["plan_id"] = plan_id
    write_seed_state(seed_state)
except Exception as e:
    print("NOTE: failed to write seed state:", str(e))

print(json.dumps({
        "tenant_a": tenant_a,
        "tenant_b": tenant_b,
        "pipeline_id": pipeline_id,
        "pipeline_run_a": run_a,
        "docpack_sha_a": doc_sha_a,
        "plan_id": plan_id,
        "plan_items": len(plan.get("items", []))
    }, indent=2))

if __name__ == "__main__":
    main()
