"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import {
  addCaseCertificate,
  addCertificate,
  deleteCaseCertificate,
  deleteCertificate,
  validateCaseCertificate,
  validateCertificate,
} from "@/app/lib/actions";

interface Cert {
  id: string; cert_type: string; number?: string | null; issuing_country?: string | null;
  organism?: string | null; issue_date?: string | null; valid_until?: string | null;
  validation_status: string;
}

export function CertificatesPanel({
  quoteId, certificates, scope = "quote",
}: {
  quoteId: string; certificates: Cert[]; scope?: "quote" | "case";
}) {
  const router = useRouter();
  const doAdd = scope === "case" ? addCaseCertificate : addCertificate;
  const doValidate = scope === "case" ? validateCaseCertificate : validateCertificate;
  const doDelete = scope === "case" ? deleteCaseCertificate : deleteCertificate;
  const [busy, setBusy] = useState(false);
  const [nc, setNc] = useState({
    cert_type: "ORIGEN", number: "", issuing_country: "", organism: "", valid_until: "",
  });

  async function add() {
    if (!nc.issuing_country.trim()) { alert("Indica el país emisor (ISO2)."); return; }
    setBusy(true);
    try {
      const r = await doAdd(quoteId, {
        cert_type: nc.cert_type, number: nc.number || null,
        issuing_country: nc.issuing_country.trim().toUpperCase(),
        organism: nc.organism || null, valid_until: nc.valid_until || null,
      });
      if (!r.ok) alert(r.error ?? "No se pudo registrar");
      else setNc({ cert_type: "ORIGEN", number: "", issuing_country: "", organism: "", valid_until: "" });
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  async function setStatus(id: string, st: string) {
    setBusy(true);
    try { await doValidate(quoteId, id, st); router.refresh(); }
    finally { setBusy(false); }
  }

  async function remove(id: string) {
    if (!confirm("¿Eliminar el certificado?")) return;
    setBusy(true);
    try { await doDelete(quoteId, id); router.refresh(); }
    finally { setBusy(false); }
  }

  return (
    <div className="card rise section-gap">
      <div className="head"><h2>Certificados de origen</h2><span className="count">{certificates.length}</span></div>
      <p style={{ color: "var(--muted)", fontSize: 12.5 }}>
        Un certificado <b>validado</b> y vigente habilita la preferencia como <b>aplicable</b>
        (en vez de solo potencial) para las mercancías de ese país de origen.
      </p>

      <div className="form-row" style={{ flexWrap: "wrap", alignItems: "flex-end", gap: 10 }}>
        <label className="field"><span>Tipo</span>
          <input value={nc.cert_type} onChange={(e) => setNc((p) => ({ ...p, cert_type: e.target.value }))} style={{ width: 110 }} />
        </label>
        <label className="field"><span>Número</span>
          <input value={nc.number} onChange={(e) => setNc((p) => ({ ...p, number: e.target.value }))} style={{ width: 130 }} />
        </label>
        <label className="field"><span>País emisor (ISO2)</span>
          <input value={nc.issuing_country} maxLength={2}
            onChange={(e) => setNc((p) => ({ ...p, issuing_country: e.target.value }))} style={{ width: 90 }} />
        </label>
        <label className="field"><span>Organismo</span>
          <input value={nc.organism} onChange={(e) => setNc((p) => ({ ...p, organism: e.target.value }))} style={{ width: 150 }} />
        </label>
        <label className="field"><span>Válido hasta</span>
          <input type="date" value={nc.valid_until} onChange={(e) => setNc((p) => ({ ...p, valid_until: e.target.value }))} />
        </label>
        <button className="btn" disabled={busy} onClick={add}>Registrar</button>
      </div>

      {certificates.length ? (
        <div style={{ marginTop: 14, overflowX: "auto" }}>
          <table className="tbl" style={{ width: "100%" }}>
            <thead>
              <tr><th>Tipo</th><th>Número</th><th>Origen</th><th>Vigencia</th><th>Estado</th><th></th></tr>
            </thead>
            <tbody>
              {certificates.map((c) => (
                <tr key={c.id}>
                  <td className="mono">{c.cert_type}</td>
                  <td>{c.number || "—"}</td>
                  <td>{c.issuing_country || "—"}</td>
                  <td style={{ fontSize: 12 }}>{c.valid_until || "sin fecha"}</td>
                  <td>
                    <span className={`pill ${c.validation_status === "VALID" ? "ok" : c.validation_status === "REJECTED" ? "crit" : "warn"}`}>
                      {c.validation_status}
                    </span>
                  </td>
                  <td>
                    <div className="actions">
                      {c.validation_status !== "VALID" ? (
                        <button className="btn ghost" disabled={busy} onClick={() => setStatus(c.id, "VALID")}>Validar</button>
                      ) : null}
                      {c.validation_status !== "REJECTED" ? (
                        <button className="btn ghost" disabled={busy} onClick={() => setStatus(c.id, "REJECTED")}>Rechazar</button>
                      ) : null}
                      <button className="btn ghost" disabled={busy} onClick={() => remove(c.id)}>✕</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}
