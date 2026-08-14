"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import {
  addSettlementLine,
  deleteSettlementLine,
  generateSettlement,
  issueSettlement,
  settlementPdf,
  updateSettlement,
  updateSettlementLine,
} from "@/app/lib/actions";
import { money, type Settlement, type SettlementLine, settleCatLabel } from "@/app/lib/format";
import { useCaps } from "@/app/lib/useCaps";

const CATEGORIES = [
  "HONORARIO", "TRIBUTO", "FLETE", "SEGURO", "ALMACENAJE",
  "DEMURRAGE", "PORTUARIO", "TRANSPORTE", "OTRO",
];

function LineRow({
  caseId,
  line,
  cur,
  locked,
}: {
  caseId: string;
  line: SettlementLine;
  cur: string;
  locked: boolean;
}) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [amount, setAmount] = useState(String(line.amount));
  const dirty = amount !== String(line.amount);

  async function save() {
    setBusy(true);
    try {
      await updateSettlementLine(caseId, line.id, { amount: Number(amount) || 0 });
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    setBusy(true);
    try {
      await deleteSettlementLine(caseId, line.id);
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  return (
    <tr>
      <td>{line.description || settleCatLabel(line.category)}</td>
      <td className="mono" style={{ fontSize: 11 }}>
        {settleCatLabel(line.category)}
        {line.taxable ? " · IVA" : ""}
      </td>
      <td className="num" style={{ width: 120 }}>
        {locked ? (
          money(line.amount, cur)
        ) : (
          <input
            className="num"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && dirty) save(); }}
            style={{ width: 90, textAlign: "right", fontFamily: "var(--mono)" }}
          />
        )}
      </td>
      <td style={{ width: 90 }}>
        {!locked ? (
          <div className="actions">
            {dirty ? <button className="btn" disabled={busy} onClick={save}>✓</button> : null}
            <button className="btn ghost" disabled={busy} title="Eliminar" onClick={remove}>✕</button>
          </div>
        ) : null}
      </td>
    </tr>
  );
}

export function SettlementPanel({ caseId, settlement }: { caseId: string; settlement: Settlement | null }) {
  const router = useRouter();
  const { canWrite } = useCaps();
  const [busy, setBusy] = useState(false);
  const [nl, setNl] = useState({ kind: "DISBURSEMENT", category: "OTRO", description: "", amount: "0", taxable: false });

  async function generate() {
    setBusy(true);
    try {
      await generateSettlement(caseId);
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  if (!settlement) {
    return (
      <div className="card section-gap rise">
        <div className="head"><h2>Liquidación al cliente</h2></div>
        <div className="card-pad">
          <div className="empty" style={{ padding: 16 }}>
            Aún no hay liquidación. Se arma con los rubros de la cotización, tributos, almacenaje y demurrage.
          </div>
          {canWrite ? (
            <button className="btn" disabled={busy} onClick={generate}>Generar liquidación</button>
          ) : (
            <span className="muted">Sin permiso para generar la liquidación.</span>
          )}
        </div>
      </div>
    );
  }

  const s = settlement;
  const cur = s.currency;
  const locked = s.status === "ISSUED" || !canWrite;  // viewers ven en solo lectura

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

  async function addLine() {
    if (!nl.description && nl.amount === "0") return;
    await act(() => addSettlementLine(caseId, s.id, {
      kind: nl.kind, category: nl.category, description: nl.description || null,
      amount: Number(nl.amount) || 0, taxable: nl.taxable,
    }));
    setNl({ ...nl, description: "", amount: "0" });
  }

  async function pdf() {
    setBusy(true);
    try {
      const url = await settlementPdf(s.id);
      if (url) window.open(url, "_blank");
      else alert("No se pudo generar el PDF");
    } finally {
      setBusy(false);
    }
  }

  const fees = s.lines.filter((l) => l.kind === "FEE");
  const disb = s.lines.filter((l) => l.kind === "DISBURSEMENT");

  return (
    <div className="card section-gap rise">
      <div className="head">
        <h2>Liquidación · <span className="mono">{s.settlement_number}</span></h2>
        <span className={`pill ${s.status === "ISSUED" ? "ok" : "accent"}`}>
          {s.status === "ISSUED" ? "EMITIDA" : "BORRADOR"}
        </span>
      </div>

      <div style={{ overflowX: "auto" }}>
        <table className="tbl">
          <thead>
            <tr><th>Honorarios</th><th>Cat.</th><th className="num">Monto</th><th></th></tr>
          </thead>
          <tbody>
            {fees.length === 0 ? (
              <tr><td colSpan={4} className="empty" style={{ padding: 12 }}>Sin honorarios.</td></tr>
            ) : fees.map((l) => <LineRow key={l.id} caseId={caseId} line={l} cur={cur} locked={locked} />)}
          </tbody>
          <thead>
            <tr><th>Desembolsos</th><th>Cat.</th><th className="num">Monto</th><th></th></tr>
          </thead>
          <tbody>
            {disb.length === 0 ? (
              <tr><td colSpan={4} className="empty" style={{ padding: 12 }}>Sin desembolsos.</td></tr>
            ) : disb.map((l) => <LineRow key={l.id} caseId={caseId} line={l} cur={cur} locked={locked} />)}
          </tbody>
        </table>
      </div>

      {!locked ? (
        <div className="form-row" style={{ borderTop: "1px solid var(--border-soft)", flexWrap: "wrap" }}>
          <select value={nl.kind} onChange={(e) => setNl((p) => ({ ...p, kind: e.target.value, taxable: e.target.value === "FEE" }))}>
            <option value="DISBURSEMENT">Desembolso</option>
            <option value="FEE">Honorario</option>
          </select>
          <select value={nl.category} onChange={(e) => setNl((p) => ({ ...p, category: e.target.value }))}>
            {CATEGORIES.map((c) => <option key={c} value={c}>{settleCatLabel(c)}</option>)}
          </select>
          <input type="text" placeholder="Descripción" value={nl.description}
            onChange={(e) => setNl((p) => ({ ...p, description: e.target.value }))} style={{ flex: 1, minWidth: 140 }} />
          <input type="text" placeholder="Monto" value={nl.amount}
            onChange={(e) => setNl((p) => ({ ...p, amount: e.target.value }))} style={{ width: 90 }} />
          <label className="muted" style={{ fontSize: 12 }}>
            IVA <input type="checkbox" checked={nl.taxable} onChange={(e) => setNl((p) => ({ ...p, taxable: e.target.checked }))} />
          </label>
          <button className="btn" disabled={busy} onClick={addLine}>+ Rubro</button>
        </div>
      ) : null}

      <div className="card-pad" style={{ borderTop: "1px solid var(--border-soft)" }}>
        <table className="tbl" style={{ maxWidth: 380, marginLeft: "auto" }}>
          <tbody>
            <tr><td>Subtotal honorarios</td><td className="num">{money(s.subtotal_fees, cur)}</td></tr>
            <tr>
              <td>
                IVA{" "}
                {locked ? `${s.iva_rate}%` : (
                  <input value={String(s.iva_rate)} onChange={(e) => act(() => updateSettlement(caseId, s.id, { iva_rate: Number(e.target.value) || 0 }))}
                    style={{ width: 48, textAlign: "right", fontFamily: "var(--mono)" }} />
                )}{" "}sobre honorarios
              </td>
              <td className="num">{money(s.tax_amount, cur)}</td>
            </tr>
            <tr><td>Desembolsos reembolsables</td><td className="num">{money(s.subtotal_disbursements, cur)}</td></tr>
            <tr style={{ fontWeight: 600 }}>
              <td style={{ color: "var(--accent)" }}>TOTAL A PAGAR</td>
              <td className="num" style={{ color: "var(--accent)" }}>{money(s.total, cur)}</td>
            </tr>
          </tbody>
        </table>
        <div className="actions" style={{ marginTop: 12, justifyContent: "flex-end" }}>
          <button className="btn ghost" disabled={busy} onClick={pdf}>PDF</button>
          {!locked ? (
            <button className="btn" disabled={busy} onClick={() => act(() => issueSettlement(caseId, s.id))}>
              Emitir
            </button>
          ) : null}
        </div>
      </div>
    </div>
  );
}
