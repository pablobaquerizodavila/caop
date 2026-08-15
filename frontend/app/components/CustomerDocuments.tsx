"use client";

import { useState } from "react";

import { documentVersionUrl } from "@/app/lib/actions";
import type { CustomerDoc } from "@/app/lib/format";

const DOC_LABELS: Record<string, string> = {
  RUC: "RUC (escaneado)",
  APPOINTMENT: "Nombramiento legal",
};

export function CustomerDocuments({ docs }: { docs: CustomerDoc[] }) {
  const [busy, setBusy] = useState<string | null>(null);

  async function open(docId: string, version: number) {
    setBusy(docId);
    try {
      const url = await documentVersionUrl(docId, version);
      if (url) window.open(url, "_blank", "noopener,noreferrer");
    } finally {
      setBusy(null);
    }
  }

  if (!docs.length) {
    return <div className="empty">Sin documentos legales cargados (RUC, nombramiento).</div>;
  }

  return (
    <div style={{ overflowX: "auto" }}>
      <table className="tbl" style={{ width: "100%" }}>
        <thead>
          <tr><th>Documento</th><th>Archivo</th><th>Cargado</th><th></th></tr>
        </thead>
        <tbody>
          {docs.map((d) => {
            const v = d.versions?.[d.versions.length - 1];
            return (
              <tr key={d.id}>
                <td>{DOC_LABELS[d.doc_type] ?? d.doc_type}</td>
                <td className="mono" style={{ fontSize: 12 }}>{v?.filename ?? "—"}</td>
                <td className="mono" style={{ color: "var(--muted)", fontSize: 12 }}>
                  {v?.created_at ? new Date(v.created_at).toLocaleDateString("es-EC") : "—"}
                </td>
                <td>
                  {v ? (
                    <button className="btn ghost" disabled={busy === d.id} onClick={() => open(d.id, v.version)}>
                      {busy === d.id ? "Abriendo…" : "Ver / descargar"}
                    </button>
                  ) : null}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
