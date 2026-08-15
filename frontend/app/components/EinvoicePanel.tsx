"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import {
  authorizeCreditNote,
  authorizeDebitNote,
  authorizeInvoice,
  createCreditNote,
  createDebitNote,
  createInvoice,
  getCreditNoteXml,
  getDebitNoteXml,
  getInvoiceRide,
  getInvoiceXml,
} from "@/app/lib/actions";
import {
  type CreditNote,
  type DebitNote,
  type Einvoice,
  einvoiceStatusClass,
  money,
} from "@/app/lib/format";
import { useCaps } from "@/app/lib/useCaps";

export function EinvoicePanel({
  caseId,
  settlementId,
  settlementIssued,
  invoice,
  creditNotes = [],
  debitNotes = [],
}: {
  caseId: string;
  settlementId: string | null;
  settlementIssued: boolean;
  invoice: Einvoice | null;
  creditNotes?: CreditNote[];
  debitNotes?: DebitNote[];
}) {
  const router = useRouter();
  const { canWrite } = useCaps();
  const [busy, setBusy] = useState(false);
  const [scenario, setScenario] = useState("AUTHORIZE");
  const [cnMotivo, setCnMotivo] = useState("");
  const [cnAmount, setCnAmount] = useState("");
  const [dnMotivo, setDnMotivo] = useState("");
  const [dnAmount, setDnAmount] = useState("");

  async function addDebitNote() {
    if (!dnMotivo || !dnAmount) return alert("Indica monto y motivo de la nota de débito");
    await act(() => createDebitNote(caseId, invoice!.id, {
      motivo: dnMotivo, amount: Number(dnAmount),
    }));
    setDnMotivo("");
    setDnAmount("");
  }

  async function downloadDnXml(dn: DebitNote) {
    setBusy(true);
    try {
      const xml = await getDebitNoteXml(dn.id);
      if (!xml) return alert("No se pudo obtener el XML");
      saveBlob(new Blob([xml], { type: "application/xml" }), `${dn.access_key}.xml`);
    } finally {
      setBusy(false);
    }
  }

  async function addCreditNote() {
    if (!cnMotivo) return alert("Indica el motivo de la nota de crédito");
    await act(() => createCreditNote(caseId, invoice!.id, {
      motivo: cnMotivo, amount: cnAmount ? Number(cnAmount) : null,
    }));
    setCnMotivo("");
    setCnAmount("");
  }

  async function downloadCnXml(cn: CreditNote) {
    setBusy(true);
    try {
      const xml = await getCreditNoteXml(cn.id);
      if (!xml) return alert("No se pudo obtener el XML");
      saveBlob(new Blob([xml], { type: "application/xml" }), `${cn.access_key}.xml`);
    } finally {
      setBusy(false);
    }
  }

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

  function saveBlob(blob: Blob, filename: string) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  async function downloadXml() {
    if (!invoice) return;
    setBusy(true);
    try {
      const xml = await getInvoiceXml(invoice.id);
      if (!xml) return alert("No se pudo obtener el XML");
      saveBlob(new Blob([xml], { type: "application/xml" }), `${invoice.access_key}.xml`);
    } finally {
      setBusy(false);
    }
  }

  async function downloadRide() {
    if (!invoice) return;
    setBusy(true);
    try {
      const b64 = await getInvoiceRide(invoice.id);
      if (!b64) return alert("No se pudo generar el RIDE");
      const bin = atob(b64);
      const arr = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
      saveBlob(new Blob([arr], { type: "application/pdf" }), `RIDE-${invoice.access_key}.pdf`);
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
              {invoice.status === "AUTHORIZED" ? (
                <button className="btn ghost" disabled={busy} onClick={downloadRide}>
                  Descargar RIDE (PDF)
                </button>
              ) : null}
              <button className="btn ghost" disabled={busy} onClick={downloadXml}>
                Descargar XML
              </button>
            </div>

            {invoice.status === "AUTHORIZED" ? (
              <div style={{ borderTop: "1px solid var(--border-soft)", paddingTop: 10 }}>
                <div className="subhead"><h3>Notas de crédito</h3></div>
                {creditNotes.length === 0 ? (
                  <div className="tag" style={{ color: "var(--muted)" }}>Sin notas de crédito.</div>
                ) : (
                  creditNotes.map((cn) => (
                    <div className="chk" key={cn.id}>
                      <div className="left">
                        <span className={`pill ${einvoiceStatusClass(cn.status)}`}>{cn.status}</span>
                        <div>
                          <div className="doc mono" style={{ fontSize: 12 }}>
                            {cn.estab}-{cn.pto_emi}-{cn.secuencial} · {money(cn.total)}
                          </div>
                          <div className="tag">{cn.motivo}</div>
                        </div>
                      </div>
                      <div className="actions">
                        {cn.status !== "AUTHORIZED" && canWrite ? (
                          <button className="btn" disabled={busy}
                            onClick={() => act(() => authorizeCreditNote(caseId, cn.id, "AUTHORIZE"))}>
                            Autorizar
                          </button>
                        ) : null}
                        <button className="btn ghost" disabled={busy} onClick={() => downloadCnXml(cn)}>XML</button>
                      </div>
                    </div>
                  ))
                )}
                {canWrite ? (
                  <div className="form-row" style={{ flexWrap: "wrap", paddingLeft: 0 }}>
                    <input type="text" placeholder="Motivo" value={cnMotivo}
                      onChange={(e) => setCnMotivo(e.target.value)} style={{ flex: 1, minWidth: 160 }} />
                    <input type="text" placeholder="Monto (vacío = total)" value={cnAmount}
                      onChange={(e) => setCnAmount(e.target.value)} style={{ width: 150 }} />
                    <button className="btn" disabled={busy} onClick={addCreditNote}>+ Nota de crédito</button>
                  </div>
                ) : null}

                <div className="subhead" style={{ marginTop: 12 }}><h3>Notas de débito</h3></div>
                {debitNotes.length === 0 ? (
                  <div className="tag" style={{ color: "var(--muted)" }}>Sin notas de débito.</div>
                ) : (
                  debitNotes.map((dn) => (
                    <div className="chk" key={dn.id}>
                      <div className="left">
                        <span className={`pill ${einvoiceStatusClass(dn.status)}`}>{dn.status}</span>
                        <div>
                          <div className="doc mono" style={{ fontSize: 12 }}>
                            {dn.estab}-{dn.pto_emi}-{dn.secuencial} · {money(dn.total)}
                          </div>
                          <div className="tag">{dn.motivo}</div>
                        </div>
                      </div>
                      <div className="actions">
                        {dn.status !== "AUTHORIZED" && canWrite ? (
                          <button className="btn" disabled={busy}
                            onClick={() => act(() => authorizeDebitNote(caseId, dn.id, "AUTHORIZE"))}>
                            Autorizar
                          </button>
                        ) : null}
                        <button className="btn ghost" disabled={busy} onClick={() => downloadDnXml(dn)}>XML</button>
                      </div>
                    </div>
                  ))
                )}
                {canWrite ? (
                  <div className="form-row" style={{ flexWrap: "wrap", paddingLeft: 0 }}>
                    <input type="text" placeholder="Motivo (ej. interés por mora)" value={dnMotivo}
                      onChange={(e) => setDnMotivo(e.target.value)} style={{ flex: 1, minWidth: 160 }} />
                    <input type="text" placeholder="Monto" value={dnAmount}
                      onChange={(e) => setDnAmount(e.target.value)} style={{ width: 150 }} />
                    <button className="btn" disabled={busy} onClick={addDebitNote}>+ Nota de débito</button>
                  </div>
                ) : null}
              </div>
            ) : null}
          </div>
        )}
      </div>
    </div>
  );
}
