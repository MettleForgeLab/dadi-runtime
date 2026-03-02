"use client";

import React, { useState } from "react";
import { Tabs, TabKey } from "./components/Tabs";
import { JsonView } from "./components/JsonView";
import { diffJson } from "./components/diffUtil";
import {
  getBytes,
  getJson,
  postJson,
  tryParseJson,
  bytesToUtf8,
  ArtifactMeta,
  Edge,
  Plan,
} from "./lib_api";

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <div style={{ fontSize: 12, opacity: 0.7 }}>{label}</div>
      <div>{children}</div>
    </div>
  );
}

function Card({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        border: "1px solid #e5e7eb",
        borderRadius: 16,
        padding: 16,
        background: "white",
        boxShadow: "0 1px 2px rgba(0,0,0,0.04)",
      }}
    >
      {children}
    </div>
  );
}

export default function Page() {
  const [tab, setTab] = useState<TabKey>("artifact");

  // Artifact
  const [sha, setSha] = useState("");
  const [meta, setMeta] = useState<ArtifactMeta | null>(null);
  const [contentText, setContentText] = useState<string | null>(null);
  const [contentJson, setContentJson] = useState<any | null>(null);
  const [upstream, setUpstream] = useState<Edge[] | null>(null);
  const [downstream, setDownstream] = useState<Edge[] | null>(null);
  const [artifactError, setArtifactError] = useState<string | null>(null);

  // Plan
  const [planId, setPlanId] = useState("");
  const [plan, setPlan] = useState<Plan | null>(null);
  const [planExplain, setPlanExplain] = useState<any | null>(null);
  const [planError, setPlanError] = useState<string | null>(null);

  // Run
  const [runId, setRunId] = useState("");
  const [runData, setRunData] = useState<any | null>(null);
  const [runArtifacts, setRunArtifacts] = useState<any | null>(null);
  const [runDeliverables, setRunDeliverables] = useState<any | null>(null);
  const [runError, setRunError] = useState<string | null>(null);

  // Deliverables & Bundles
  const [deliverableId, setDeliverableId] = useState<string>("");
  const [deliverableObj, setDeliverableObj] = useState<any | null>(null);
  const [bundleList, setBundleList] = useState<any | null>(null);
  const [bundleCreateResult, setBundleCreateResult] = useState<any | null>(null);
  const [bundleVerifyResult, setBundleVerifyResult] = useState<any | null>(null);
  const [bundleError, setBundleError] = useState<string | null>(null);

  const deliverableStatus = (deliverableObj?.status || deliverableObj?.deliverable_status || "").toString();
  const deliverableIsFinal = deliverableStatus === "final" || deliverableStatus === "sent";

  // Drift (Run Diff) — panel lives under Run tab
  const [diffRunA, setDiffRunA] = useState("");
  const [diffRunB, setDiffRunB] = useState("");
  const [runDiff, setRunDiff] = useState<any | null>(null);
  const [runDiffError, setRunDiffError] = useState<string | null>(null);

  // Diff (Artifact JSON diff)
  const [aSha, setASha] = useState("");
  const [bSha, setBSha] = useState("");
  const [diffA, setDiffA] = useState<any | null>(null);
  const [diffB, setDiffB] = useState<any | null>(null);
  const [diffItems, setDiffItems] = useState<any[] | null>(null);
  const [diffError, setDiffError] = useState<string | null>(null);

  async function loadArtifact() {
    setArtifactError(null);
    setMeta(null);
    setContentText(null);
    setContentJson(null);
    setUpstream(null);
    setDownstream(null);

    const trimmed = sha.trim();
    if (!trimmed) return;

    try {
      const m = await getJson<ArtifactMeta>(`/artifacts/${trimmed}`);
      setMeta(m);

      const bytes = await getBytes(`/artifacts/${trimmed}/content`);
      const text = bytesToUtf8(bytes);
      setContentText(text);

      const obj = tryParseJson(text);
      setContentJson(obj);

      const up = await getJson<{ edges: Edge[] }>(`/lineage/${trimmed}/upstream`);
      const down = await getJson<{ edges: Edge[] }>(`/lineage/${trimmed}/downstream`);
      setUpstream(up.edges || []);
      setDownstream(down.edges || []);
    } catch (e: any) {
      setArtifactError(e?.message || String(e));
    }
  }

  async function loadPlan() {
    setPlanError(null);
    setPlan(null);
    setPlanExplain(null);

    const trimmed = planId.trim();
    if (!trimmed) return;

    try {
      const p = await getJson<Plan>(`/plan/${trimmed}`);
      setPlan(p);

      const ex = await getJson<any>(`/plan/${trimmed}/explain`);
      setPlanExplain(ex);
    } catch (e: any) {
      setPlanError(e?.message || String(e));
    }
  }

  async function loadRun() {
    setRunError(null);
    setRunData(null);
    setRunArtifacts(null);
    setRunDeliverables(null);

    const trimmed = runId.trim();
    if (!trimmed) return;

    try {
      const r = await getJson<any>(`/runs/${trimmed}`);
      setRunData(r);

      const ra = await getJson<any>(`/runs/${trimmed}/artifacts`);
      setRunArtifacts(ra);

      const rd = await getJson<any>(`/runs/${trimmed}/deliverables`);
      setRunDeliverables(rd);
    } catch (e: any) {
      setRunError(e?.message || String(e));
    }
  }

  async function loadRunDiff() {
    setRunDiffError(null);
    setRunDiff(null);

    const A = diffRunA.trim();
    const B = diffRunB.trim();
    if (!A || !B) return;

    try {
      const r = await getJson<any>(
        `/runs/diff?run_a=${encodeURIComponent(A)}&run_b=${encodeURIComponent(B)}`
      );
      setRunDiff(r);
    } catch (e: any) {
      setRunDiffError(e?.message || String(e));
    }
  }

  function jumpToArtifact(sha256: string) {
    setSha(sha256);
    setTab("artifact");
    setTimeout(() => {
      loadArtifact();
    }, 0);
  }

async function createDeliverableDraft() {
  setBundleError(null);
  setDeliverableObj(null);
  setBundleList(null);
  setBundleCreateResult(null);
  setBundleVerifyResult(null);

  const rid = runId.trim();
  if (!rid) {
    setBundleError("Set Pipeline Run ID first.");
    return;
  }

  try {
    const d = await postJson<any>("/deliverables", { pipeline_run_id: rid, status: "draft" });
    setDeliverableObj(d);
    setDeliverableId(d.deliverable_id || "");
  } catch (e: any) {
    setBundleError(e?.message || String(e));
  }
}

async function finalizeDeliverable() {
  setBundleError(null);
  const did = deliverableId.trim();
  if (!did) {
    setBundleError("Set deliverable_id first.");
    return;
  }
  try {
    const r = await postJson<any>(`/deliverables/${did}/finalize`, {});
    setBundleVerifyResult(r);
  } catch (e: any) {
    setBundleError(e?.message || String(e));
  }
}

async function createBundle() {
  setBundleError(null);
  setBundleCreateResult(null);
  const did = deliverableId.trim();
  if (!did) {
    setBundleError("Set deliverable_id first.");
    return;
  }
  try {
    const r = await postJson<any>(`/deliverables/${did}/bundle`, {});
    setBundleCreateResult(r);
  } catch (e: any) {
    setBundleError(e?.message || String(e));
  }
}

async function listBundles() {
  setBundleError(null);
  setBundleList(null);
  const did = deliverableId.trim();
  if (!did) {
    setBundleError("Set deliverable_id first.");
    return;
  }
  try {
    const r = await getJson<any>(`/deliverables/${did}/bundles`);
    setBundleList(r);
  } catch (e: any) {
    setBundleError(e?.message || String(e));
  }
}

async function verifyBundleManifest() {
  setBundleError(null);
  setBundleVerifyResult(null);
  const did = deliverableId.trim();
  const manifestSha =
    bundleCreateResult?.manifest_artifact_sha256 ||
    bundleList?.bundles?.[0]?.manifest_artifact_sha256;

  if (!did) {
    setBundleError("Set deliverable_id first.");
    return;
  }
  if (!manifestSha) {
    setBundleError("No manifest_artifact_sha256 available (create or list bundles first).");
    return;
  }

  try {
    const r = await postJson<any>(`/deliverables/${did}/bundle/verify`, {
      manifest_artifact_sha256: manifestSha,
    });
    setBundleVerifyResult(r);
  } catch (e: any) {
    setBundleError(e?.message || String(e));
  }
}


  function extractFirstDiffOutputs(diffObj: any): { aOut?: string; bOut?: string } {
    const idx = diffObj?.first_diff_stage_index;
    const comps = diffObj?.comparisons;
    if (idx == null || !Array.isArray(comps)) return {};
    const row = comps.find((c: any) => c?.stage_index === idx);
    const aOut = row?.a?.output_artifact_sha256;
    const bOut = row?.b?.output_artifact_sha256;
    return { aOut, bOut };
  }

  async function loadDiff() {
    setDiffError(null);
    setDiffItems(null);
    setDiffA(null);
    setDiffB(null);

    const A = aSha.trim();
    const B = bSha.trim();
    if (!A || !B) return;

    try {
      const aBytes = await getBytes(`/artifacts/${A}/content`);
      const bBytes = await getBytes(`/artifacts/${B}/content`);
      const aText = bytesToUtf8(aBytes);
      const bText = bytesToUtf8(bBytes);
      const aObj = tryParseJson(aText);
      const bObj = tryParseJson(bText);

      if (!aObj || !bObj) {
        throw new Error("Diff requires both artifacts to be valid JSON.");
      }

      setDiffA(aObj);
      setDiffB(bObj);

      const items = diffJson(aObj, bObj);
      setDiffItems(items);
    } catch (e: any) {
      setDiffError(e?.message || String(e));
    }
  }

  const firstDiffOutputs = runDiff ? extractFirstDiffOutputs(runDiff) : {};

  return (
    <div
      style={{
        maxWidth: 1100,
        margin: "0 auto",
        display: "flex",
        flexDirection: "column",
        gap: 16,
      }}
    >
      <Tabs value={tab} onChange={setTab} />

      {tab === "artifact" && (
        <Card>
          <div style={{ display: "flex", gap: 12, alignItems: "flex-end" }}>
            <Field label="Artifact SHA256">
              <input
                value={sha}
                onChange={(e) => setSha(e.target.value)}
                placeholder="64-hex SHA256"
                style={{
                  width: 520,
                  padding: "10px 12px",
                  borderRadius: 10,
                  border: "1px solid #e5e7eb",
                }}
              />
            </Field>
            <button
              onClick={loadArtifact}
              style={{
                padding: "10px 14px",
                borderRadius: 10,
                border: "1px solid #e5e7eb",
                background: "#111827",
                color: "white",
                cursor: "pointer",
              }}
            >
              Load
            </button>
          </div>

          {artifactError && (
            <div style={{ marginTop: 12, color: "#b91c1c" }}>{artifactError}</div>
          )}

          {meta && (
            <div
              style={{
                marginTop: 16,
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: 12,
              }}
            >
              <Field label="artifact_type">
                <code>{meta.artifact_type}</code>
              </Field>
              <Field label="schema_version">
                <code>{meta.schema_version || "(none)"}</code>
              </Field>
              <Field label="media_type">
                <code>{meta.media_type}</code>
              </Field>
              <Field label="byte_length">
                <code>{meta.byte_length}</code>
              </Field>
              <Field label="canonical">
                <code>{String(meta.canonical)}</code>
              </Field>
              <Field label="canonical_format">
                <code>{meta.canonical_format || "(none)"}</code>
              </Field>
              <Field label="storage_backend">
                <code>{meta.storage_backend}</code>
              </Field>
              <Field label="storage_ref">
                <code>{meta.storage_ref || "(none)"}</code>
              </Field>
            </div>
          )}

          {contentJson ? (
            <div style={{ marginTop: 16 }}>
              <div style={{ fontSize: 12, opacity: 0.7, marginBottom: 6 }}>
                Content (JSON)
              </div>
              <JsonView value={contentJson} />
            </div>
          ) : contentText ? (
            <div style={{ marginTop: 16 }}>
              <div style={{ fontSize: 12, opacity: 0.7, marginBottom: 6 }}>
                Content (text preview)
              </div>
              <pre
                style={{
                  margin: 0,
                  padding: 12,
                  borderRadius: 12,
                  border: "1px solid #e5e7eb",
                  background: "#f9fafb",
                  overflow: "auto",
                  maxHeight: 280,
                  fontSize: 12,
                  lineHeight: 1.4,
                }}
              >
                {contentText.slice(0, 20000)}
              </pre>
            </div>
          ) : null}

          {(upstream || downstream) && (
            <div
              style={{
                marginTop: 16,
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: 12,
              }}
            >
              <div>
                <div style={{ fontSize: 12, opacity: 0.7, marginBottom: 6 }}>
                  Upstream edges
                </div>
                <JsonView value={upstream || []} />
              </div>
              <div>
                <div style={{ fontSize: 12, opacity: 0.7, marginBottom: 6 }}>
                  Downstream edges
                </div>
                <JsonView value={downstream || []} />
              </div>
            </div>
          )}
        </Card>
      )}

      {tab === "run" && (
        <>
          <Card>
            <div style={{ display: "flex", gap: 12, alignItems: "flex-end" }}>
              <Field label="Pipeline Run ID">
                <input
                  value={runId}
                  onChange={(e) => setRunId(e.target.value)}
                  placeholder="UUID"
                  style={{
                    width: 520,
                    padding: "10px 12px",
                    borderRadius: 10,
                    border: "1px solid #e5e7eb",
                  }}
                />
              </Field>
              <button
                onClick={loadRun}
                style={{
                  padding: "10px 14px",
                  borderRadius: 10,
                  border: "1px solid #e5e7eb",
                  background: "#111827",
                  color: "white",
                  cursor: "pointer",
                }}
              >
                Load
              </button>
            </div>

            {runError && (
              <div style={{ marginTop: 12, color: "#b91c1c" }}>{runError}</div>
            )}

            {runData && (
              <div style={{ marginTop: 16 }}>
                <div style={{ fontSize: 12, opacity: 0.7, marginBottom: 6 }}>
                  Run
                </div>
                <JsonView value={runData} />
              </div>
            )}

            {runArtifacts && (
              <div style={{ marginTop: 16 }}>
                <div style={{ fontSize: 12, opacity: 0.7, marginBottom: 6 }}>
                  Referenced artifacts
                </div>
                <JsonView value={runArtifacts} />
              </div>
            )}

            {runDeliverables && (
              <div style={{ marginTop: 16 }}>
                <div style={{ fontSize: 12, opacity: 0.7, marginBottom: 6 }}>
                  Deliverables (Stage 06)
                </div>
                <JsonView value={runDeliverables} />
              </div>
            )}
          </Card>

          <Card>
            <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>
              Drift (Run Diff)
            </div>

            <div style={{ display: "flex", gap: 12, alignItems: "flex-end", flexWrap: "wrap" }}>
              <Field label="Run A">
                <input
                  value={diffRunA}
                  onChange={(e) => setDiffRunA(e.target.value)}
                  placeholder="UUID"
                  style={{
                    width: 420,
                    padding: "10px 12px",
                    borderRadius: 10,
                    border: "1px solid #e5e7eb",
                  }}
                />
              </Field>
              <Field label="Run B">
                <input
                  value={diffRunB}
                  onChange={(e) => setDiffRunB(e.target.value)}
                  placeholder="UUID"
                  style={{
                    width: 420,
                    padding: "10px 12px",
                    borderRadius: 10,
                    border: "1px solid #e5e7eb",
                  }}
                />
              </Field>
              <button
                onClick={loadRunDiff}
                style={{
                  padding: "10px 14px",
                  borderRadius: 10,
                  border: "1px solid #e5e7eb",
                  background: "#111827",
                  color: "white",
                  cursor: "pointer",
                }}
              >
                Compare
              </button>
            </div>

            {runDiffError && (
              <div style={{ marginTop: 12, color: "#b91c1c" }}>{runDiffError}</div>
            )}

            {runDiff && (
              <div style={{ marginTop: 16 }}>
                <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap", marginBottom: 10 }}>
                  <div style={{ fontSize: 12, opacity: 0.7 }}>
                    first_diff_stage_index:{" "}
                    <code>{String(runDiff.first_diff_stage_index ?? "(none)")}</code>
                  </div>
                  <div style={{ fontSize: 12, opacity: 0.7 }}>
                    classification: <code>{String(runDiff.classification ?? "(none)")}</code>
                  </div>

                  {firstDiffOutputs.aOut && (
                    <button
                      onClick={() => jumpToArtifact(firstDiffOutputs.aOut!)}
                      style={{
                        padding: "8px 10px",
                        borderRadius: 10,
                        border: "1px solid #e5e7eb",
                        background: "white",
                        cursor: "pointer",
                      }}
                    >
                      Open A stage output
                    </button>
                  )}
                  {firstDiffOutputs.bOut && (
                    <button
                      onClick={() => jumpToArtifact(firstDiffOutputs.bOut!)}
                      style={{
                        padding: "8px 10px",
                        borderRadius: 10,
                        border: "1px solid #e5e7eb",
                        background: "white",
                        cursor: "pointer",
                      }}
                    >
                      Open B stage output
                    </button>
                  )}
                </div>

                <div style={{ fontSize: 12, opacity: 0.7, marginBottom: 6 }}>
                  Run diff
                </div>
                <JsonView value={runDiff} />
              </div>
            )}
          </Card>
        </>
      )}

      {tab === "plan" && (
        <Card>
          <div style={{ display: "flex", gap: 12, alignItems: "flex-end" }}>
            <Field label="Plan ID">
              <input
                value={planId}
                onChange={(e) => setPlanId(e.target.value)}
                placeholder="UUID"
                style={{
                  width: 520,
                  padding: "10px 12px",
                  borderRadius: 10,
                  border: "1px solid #e5e7eb",
                }}
              />
            </Field>
            <button
              onClick={loadPlan}
              style={{
                padding: "10px 14px",
                borderRadius: 10,
                border: "1px solid #e5e7eb",
                background: "#111827",
                color: "white",
                cursor: "pointer",
              }}
            >
              Load
            </button>
          </div>

          {planError && (
            <div style={{ marginTop: 12, color: "#b91c1c" }}>{planError}</div>
          )}

          {plan && (
            <div style={{ marginTop: 16 }}>
              <div style={{ fontSize: 12, opacity: 0.7, marginBottom: 6 }}>Plan</div>
              <JsonView value={plan} />
            </div>
          )}

          {planExplain && (
            <div style={{ marginTop: 16 }}>
              <div style={{ fontSize: 12, opacity: 0.7, marginBottom: 6 }}>
                Explain
              </div>
              <JsonView value={planExplain} />
            </div>
          )}
        </Card>
      )}

      {tab === "diff" && (
        <Card>
          <div style={{ display: "flex", gap: 12, alignItems: "flex-end", flexWrap: "wrap" }}>
            <Field label="Artifact A SHA256">
              <input
                value={aSha}
                onChange={(e) => setASha(e.target.value)}
                placeholder="64-hex SHA256"
                style={{
                  width: 460,
                  padding: "10px 12px",
                  borderRadius: 10,
                  border: "1px solid #e5e7eb",
                }}
              />
            </Field>
            <Field label="Artifact B SHA256">
              <input
                value={bSha}
                onChange={(e) => setBSha(e.target.value)}
                placeholder="64-hex SHA256"
                style={{
                  width: 460,
                  padding: "10px 12px",
                  borderRadius: 10,
                  border: "1px solid #e5e7eb",
                }}
              />
            </Field>
            <button
              onClick={loadDiff}
              style={{
                padding: "10px 14px",
                borderRadius: 10,
                border: "1px solid #e5e7eb",
                background: "#111827",
                color: "white",
                cursor: "pointer",
              }}
            >
              Diff
            </button>
          </div>

          {diffError && (
            <div style={{ marginTop: 12, color: "#b91c1c" }}>{diffError}</div>
          )}

          {diffItems && (
            <div style={{ marginTop: 16 }}>
              <div style={{ fontSize: 12, opacity: 0.7, marginBottom: 6 }}>Diff items</div>
              <JsonView value={diffItems.slice(0, 2000)} />
              <div style={{ fontSize: 12, opacity: 0.7, marginTop: 8 }}>
                Showing up to 2000 diff items.
              </div>
            </div>
          )}

          {(diffA || diffB) && (
            <div style={{ marginTop: 16, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              <div>
                <div style={{ fontSize: 12, opacity: 0.7, marginBottom: 6 }}>A (JSON)</div>
                <JsonView value={diffA} />
              </div>
              <div>
                <div style={{ fontSize: 12, opacity: 0.7, marginBottom: 6 }}>B (JSON)</div>
                <JsonView value={diffB} />
              </div>
            </div>
          )}
        </Card>
      )}

      <div style={{ fontSize: 12, opacity: 0.7 }}>
        API base: <code>{process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000"}</code>
      </div>
    </div>
  );
}
