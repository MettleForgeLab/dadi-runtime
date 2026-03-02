import React from "react";

export type TabKey = "artifact" | "plan" | "diff" | "run";

export function Tabs({
  value,
  onChange,
}: {
  value: TabKey;
  onChange: (v: TabKey) => void;
}) {
  const tabs: Array<{ key: TabKey; label: string }> = [
    { key: "artifact", label: "Artifact" },
    { key: "run", label: "Run" },
    { key: "plan", label: "Plan" },
    { key: "diff", label: "Diff" },
  ];

  return (
    <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
      {tabs.map((t) => (
        <button
          key={t.key}
          onClick={() => onChange(t.key)}
          style={{
            padding: "8px 12px",
            borderRadius: 10,
            border: "1px solid #e5e7eb",
            background: value === t.key ? "#111827" : "white",
            color: value === t.key ? "white" : "#111827",
            cursor: "pointer",
          }}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}
