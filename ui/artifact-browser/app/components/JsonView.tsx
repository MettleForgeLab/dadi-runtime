import React from "react";

export function JsonView({ value }: { value: any }) {
  return (
    <pre
      style={{
        margin: 0,
        padding: 12,
        borderRadius: 12,
        border: "1px solid #e5e7eb",
        background: "#f9fafb",
        overflow: "auto",
        maxHeight: 420,
        fontSize: 12,
        lineHeight: 1.4,
      }}
    >
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}
