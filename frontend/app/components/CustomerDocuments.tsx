"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";

import {
  documentVersionUrl,
  replaceDocumentVersion,
  setDocumentDates,
  uploadCustomerDocument,
} from "@/app/lib/actions";
import type { CustomerDoc } from "@/app/lib/format";

const DOC_LABELS: Record<string, string> = {
  RUC: "RUC (escaneado)",
  CEDULA: "Cédula de identidad",
  APPOINTMENT: "Nombramiento legal",
};

const DOC_ACCEPT = ".pdf,.png,.jpg,.jpeg,application/pdf,image/*";
const CANONICAL = ["RUC", "CEDULA", "APPOINTMENT"];

/** Badge de vigencia según la fecha de vencimiento. */
function ExpiryBadge({ expiry }: { expiry?: string | null }) {
  if (!expiry) return <span style={{ color: "var(--muted-2)", fontSize: 12 }}>— sin fecha —</span>;
  const d = new Date(expiry + "T00:00:00");
  const days = Math.ceil((d.getTime() - Date.now()) / 86400000);
  const fecha = d.toLocaleDateString("es-EC");
  if (days < 0) return <span><span className="pill crit">Vencido</span> <span className="mono" style={{ fontSize: 12 }}>{fecha}</span></span>;
  if (days <= 30) return <span><span className="pill warn">Vence en {days}d</span> <span className="mono" style={{ fontSize: 12 }}>{fecha}</span></span>;
  return <span><span className="pill ok">Vigente</span> <span className="mono" style={{ fontSize: 12 }}>{fecha}</span></span>;
}

export function CustomerDocuments({
  docs,
  customerId,
  canEdit = false,
}: {
  docs: CustomerDoc[];
  customerId: string;
  canEdit?: boolean;
}) {
  const router = useRouter();
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const replaceRefs = useRef<Record<string, HTMLInputElement | null>>({});
  const addRef = useRef<HTMLInputElement | null>(null);
  const [addType, setAddType] = useState("APPOINTMENT");
  const [addExpiry, setAddExpiry] = useState("");

  async function open(docId: string, version: number) {
    setBusy(docId);
    try {
      const url = await documentVersionUrl(docId, version);
      if (url) window.open(url, "_blank", "noopener,noreferrer");
    } finally {
      setBusy(null);
    }
  }

  async function replace(docId: string) {
    const file = replaceRefs.current[docId]?.files?.[0];
    if (!file) return;
    setBusy(docId);
    setMsg(null);
    try {
      const fd = new FormData();
      fd.append("file", file, file.name);
      const r = await replaceDocumentVersion(docId, customerId, fd);
      setMsg(r.ok ? "Documento reemplazado (nueva versión)." : `Error: ${r.error}`);
      if (r.ok && replaceRefs.current[docId]) replaceRefs.current[docId]!.value = "";
      router.refresh();
    } finally {
      setBusy(null);
    }
  }

  async function saveExpiry(docId: string, value: string) {
    setBusy(docId + ":date");
    setMsg(null);
    try {
      const r = await setDocumentDates(docId, customerId, { expiry_date: value || null });
      setMsg(r.ok ? "Fecha de vencimiento actualizada." : `Error: ${r.error}`);
      router.refresh();
    } finally {
      setBusy(null);
    }
  }

  async function add() {
    const file = addRef.current?.files?.[0];
    if (!file) { setMsg("Selecciona un archivo."); return; }
    setBusy("add");
    setMsg(null);
    try {
      const fd = new FormData();
      fd.append("file", file, file.name);
      if (addExpiry) fd.append("expiry_date", addExpiry);
      const r = await uploadCustomerDocument(customerId, addType, fd);
      setMsg(r.ok ? "Documento agregado." : `Error: ${r.error}`);
      if (r.ok && addRef.current) addRef.current.value = "";
      if (r.ok) setAddExpiry("");
      router.refresh();
    } finally {
      setBusy(null);
    }
  }

  const presentTypes = new Set(docs.map((d) => d.doc_type));
  const missing = CANONICAL.filter((t) => !presentTypes.has(t));

  return (
    <div className="stack" style={{ gap: 10 }}>
      {docs.length === 0 ? (
        <div className="empty">Sin documentos legales cargados (RUC, cédula, nombramiento).</div>
      ) : (
        <div style={{ overflowX: "auto" }}>
          <table className="tbl" style={{ width: "100%" }}>
            <thead>
              <tr><th>Documento</th><th>Archivo</th><th>Vencimiento</th><th>Cargado</th><th></th>{canEdit ? <th>Reemplazar</th> : null}</tr>
            </thead>
            <tbody>
              {docs.map((d) => {
                const v = d.versions?.[d.versions.length - 1];
                return (
                  <tr key={d.id}>
                    <td>{DOC_LABELS[d.doc_type] ?? d.doc_type}{d.versions?.length > 1 ? <span style={{ color: "var(--muted-2)", fontSize: 11 }}> · v{v?.version}</span> : null}</td>
                    <td className="mono" style={{ fontSize: 12 }}>{v?.filename ?? "—"}</td>
                    <td>
                      {canEdit ? (
                        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                          <input
                            type="date"
                            defaultValue={v?.expiry_date ?? ""}
                            disabled={busy === d.id + ":date"}
                            onChange={(e) => saveExpiry(d.id, e.target.value)}
                            style={{ fontSize: 12, width: 150 }}
                            title="Fecha de vencimiento (se guarda al cambiar)"
                          />
                          <ExpiryBadge expiry={v?.expiry_date} />
                        </div>
                      ) : (
                        <ExpiryBadge expiry={v?.expiry_date} />
                      )}
                    </td>
                    <td className="mono" style={{ color: "var(--muted)", fontSize: 12 }}>
                      {v?.created_at ? new Date(v.created_at).toLocaleDateString("es-EC") : "—"}
                    </td>
                    <td>
                      {v ? (
                        <button className="btn ghost" disabled={busy === d.id} onClick={() => open(d.id, v.version)}>
                          {busy === d.id ? "…" : "Ver / descargar"}
                        </button>
                      ) : null}
                    </td>
                    {canEdit ? (
                      <td>
                        <input
                          ref={(el) => { replaceRefs.current[d.id] = el; }}
                          type="file"
                          accept={DOC_ACCEPT}
                          disabled={busy === d.id}
                          onChange={() => replace(d.id)}
                          style={{ fontSize: 12 }}
                        />
                      </td>
                    ) : null}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {canEdit && missing.length ? (
        <div className="form-row" style={{ display: "flex", gap: 8, alignItems: "flex-end", flexWrap: "wrap" }}>
          <label className="field"><span>Agregar documento</span>
            <select value={addType} onChange={(e) => setAddType(e.target.value)}>
              {missing.map((t) => <option key={t} value={t}>{DOC_LABELS[t] ?? t}</option>)}
            </select>
          </label>
          <label className="field"><span>Vence (opcional)</span>
            <input type="date" value={addExpiry} onChange={(e) => setAddExpiry(e.target.value)} />
          </label>
          <label className="field" style={{ minWidth: 200 }}><span>Archivo (PDF)</span>
            <input ref={addRef} type="file" accept={DOC_ACCEPT} />
          </label>
          <button className="btn" disabled={busy === "add"} onClick={add}>Agregar</button>
        </div>
      ) : null}

      {msg ? <div style={{ fontSize: 12.5, color: "var(--muted)" }}>{msg}</div> : null}
    </div>
  );
}
