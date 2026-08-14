"use client";

import { useState } from "react";

import { documentVersionUrl } from "@/app/lib/actions";
import { type CaseDocument, docLabel, humanSize } from "@/app/lib/format";

export function CaseDocumentsPanel({ documents }: { documents: CaseDocument[] }) {
  const [busy, setBusy] = useState<string | null>(null);

  async function open(documentId: string, version: number) {
    const key = `${documentId}-${version}`;
    setBusy(key);
    try {
      const url = await documentVersionUrl(documentId, version);
      if (url) window.open(url, "_blank");
      else alert("No se pudo obtener el archivo");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="card section-gap rise">
      <div className="head">
        <h2>Documentos del expediente</h2>
        <span className="count">{documents.length}</span>
      </div>
      {documents.length === 0 ? (
        <div className="empty">Aún no se han cargado documentos.</div>
      ) : (
        <div style={{ overflowX: "auto" }}>
          <table className="tbl">
            <thead>
              <tr>
                <th>Tipo</th><th>Archivo</th><th className="num">Ver.</th>
                <th className="num">Tamaño</th><th>Cargado</th><th></th>
              </tr>
            </thead>
            <tbody>
              {documents.flatMap((d) =>
                d.versions.map((v) => (
                  <tr key={v.id}>
                    <td>{docLabel(d.doc_type)}</td>
                    <td className="mono" style={{ fontSize: 12 }}>{v.filename}</td>
                    <td className="num">v{v.version}</td>
                    <td className="num">{humanSize(v.size)}</td>
                    <td className="mono" style={{ fontSize: 11, color: "var(--muted)" }}>
                      {new Date(v.created_at).toLocaleDateString("es-EC")}
                    </td>
                    <td>
                      <button
                        className="btn ghost"
                        disabled={busy === `${d.id}-${v.version}`}
                        onClick={() => open(d.id, v.version)}
                      >
                        Descargar
                      </button>
                    </td>
                  </tr>
                )),
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
