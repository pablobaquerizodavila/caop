"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { authorizeInvoice, createInvoice, getInvoiceXml } from "@/app/lib/actions";
import { type Einvoice, einvoiceStatusClass, money } from "@/app/lib/format";
import { useCaps } from "@/app/lib/useCaps";

export function EinvoicePanel({
  caseId,
  settlementId,
  settlementIssued,
  invoice,
}: {
  caseId: string;
  settlementId: string | null;
  settlementIssued: boolean;
  invoice: Einvoice | null;
}) {
  const router = useRouter();
  const { canWrite } = useCaps();
  const [busy, setBusy] = useState(false);
  const [scenario, setScenario] = useState("AUTHORIZE");

  async function act(fn: () => Promise<{ ok: boolean; error?: string }>) {
    setBusy(true);
    try {
      const r = await fn();
      if (!r.ok) alert(r.error ?? "No se pudo completar");
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  async function downloadXml() {
    if (!invoice) return;
    setBusy(true);
    try {
      const xml = await getInvoiceXml(invoice.id);
      if (!xml) {
        alert("No se pudo obtener el XML");
        return;
      }
      const blob = new Blob([xml], { type: "application/xml" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${invoice.access_key}.xml`;
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card section-gap rise">
      <div className="head">
        <h2>Facturación electrónica (SRI)</h2>
        {invoice ? (
          <span className={`pill ${einvoiceStatusClass(invoice.status)}`}>{invoice.status}</span>
        ) : null}
      </div>
      <div className="card-pad">
        {!invoice ? (
          !settlementId ? (
            <div className="muted">Genera y emite la liquidación para poder facturar.</div>
          ) : !settlementIssued ? (
            <div className="muted">Emite la liquidación (botón &quot;Emitir&quot;) para poder facturar.</div>
          ) : canWrite ? (
            <button className="btn" disabled={busy} onClick={() => act(() => createInvoice(caseId, settlementId))}>
              Generar factura electrónica
            </button>
          ) : (
            <div className="muted">Sin permiso para facturar.</div>
          )
        ) : (
          <div className="stack">
            <div className="mono" style={{ fontSize: 11.5, color: "var(--muted)", wordBreak: "break-all" }}>
              Clave de acceso: {invoice.access_key}
            </div>
            <div className="mono" style={{ fontSize: 12.5, color: "var(--muted)" }}>
              {invoice.estab}-{invoice.pto_emi}-{invoice.secuencial} · ambiente {invoice.ambiente === "2" ? "producción" : "pruebas"}
              {invoice.is_simulated ? " · SIMULADO (sin transmisión real)" : ""}
            </div>
            <div className="mono" style={{ fontSize: 12.5 }}>Total facturado: {money(invoice.total)}</div>
            {invoice.authorization_number ? (
              <div className="mono" style={{ fontSize: 11.5, color: "var(--ok)", wordBreak: "break-all" }}>
                Autorización: {invoice.authorization_number}
              </div>
            ) : null}
            {invoice.error ? <div className="form-error">{invoice.error}</div> : null}

            <div className="actions">
              {invoice.status !== "AUTHORIZED" && canWrite ? (
                <>
                  <select value={scenario} onChange={(e) => setScenario(e.target.value)}>
                    <option value="AUTHORIZE">Escenario: autorizar</option>
                    <option value="REJECT">Escenario: rechazar</option>
                    <option value="UNAVAILABLE">Escenario: SRI no disponible</option>
                  </select>
                  <button className="btn" disabled={busy} onClick={() => act(() => authorizeInvoice(caseId, invoice.id, scenario))}>
                    Firmar y autorizar
                  </button>
                </>
              ) : null}
              <button className="btn ghost" disabled={busy} onClick={downloadXml}>
                Descargar XML
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
