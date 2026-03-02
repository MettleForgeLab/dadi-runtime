import "./globals.css";
import React from "react";

export const metadata = {
  title: "DADI Artifact Browser",
  description: "Artifact inspection, lineage, plans, and diffs",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div style={{ padding: 16, borderBottom: "1px solid #e5e7eb" }}>
          <div style={{ fontSize: 18, fontWeight: 600 }}>DADI Artifact Browser</div>
          <div style={{ fontSize: 12, opacity: 0.7 }}>Artifacts • Lineage • Plans • Diff</div>
        </div>
        <div style={{ padding: 16 }}>{children}</div>
      </body>
    </html>
  );
}
