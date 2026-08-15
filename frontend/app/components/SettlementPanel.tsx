"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import {
  addPayment,
  addSettlementLine,
  deletePayment,
  deleteSettlementLine,
  generateSettlement,
  issueSettlement,
  sendPaymentReminder,
  settlementPdf,
  updateSettlement,
  updateSettlementLine,
} from "@/app/lib/actions";
import {
  money,
  payStatusClass,
  payStatusLabel,
  type PaymentsView,
  type Settlement,
  type SettlementLine,
  settleCatLabel,
} from "@/app/lib/format";
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

const PAY_METHODS = ["TRANSFER", "CASH", "CHECK", "CARD", "OTHER"];

export function SettlementPanel({
  caseId,
  settlement,
  payments,
}: {
  caseId: string;
  settlement: Settlement | null;
  payments?: PaymentsView | null;
}) {
  const router = useRouter();
  const { canWrite } = useCaps();
  const [busy, setBusy] = useState(false);
  const [nl, setNl] = useState({ kind: "DISBURSEMENT", category: "OTRO", description: "", amount: "0", taxable: false });
  const [np, setNp] = useState({ amount: "", paid_at: new Date().toISOString().slice(0, 10), method: "TRANSFER", reference: "" });

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

  async function addPay() {
    if (!np.amount) return;
    await act(() => addPayment(caseId, s.id, {
      amount: Number(np.amount) || 0, paid_at: np.paid_at,
      method: np.method, reference: np.reference || null,
    }));
    setNp({ ...np, amount: "", reference: "" });
  }

  async function remind() {
    setBusy(true);
    try {
      const r = await sendPaymentReminder(caseId, s.id);
      if (!r.ok) alert(r.error ?? "No se pudo enviar");
      else if (r.status === "SKIPPED") alert(`Recordatorio omitido: ${r.reason}`);
      else alert(`Recordatorio enviado a ${r.to}`);
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  const fees = s.lines.filter((l) => l.kind === "FEE");
  const disb = s.lines.filter((l) => l.kind === "DISBURSEMENT");
  const showCobranza = s.status === "ISSUED" && payments;

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

      {showCobranza ? (
        <>
          <div className="head" style={{ borderTop: "1px solid var(--border-soft)" }}>
            <h2>Cobranza</h2>
            <span className={`pill ${payStatusClass(payments!.status)}`}>
              {payStatusLabel(payments!.status)}
            </span>
          </div>
          <div className="card-pad">
            <table className="tbl" style={{ maxWidth: 380, marginLeft: "auto" }}>
              <tbody>
                <tr><td>Total</td><td className="num">{money(payments!.total, cur)}</td></tr>
                <tr><td>Pagado</td><td className="num">{money(payments!.paid, cur)}</td></tr>
                <tr style={{ fontWeight: 600 }}>
                  <td style={{ color: payments!.balance > 0 ? "var(--warn)" : "var(--ok)" }}>Saldo</td>
                  <td className="num" style={{ color: payments!.balance > 0 ? "var(--warn)" : "var(--ok)" }}>
                    {money(payments!.balance, cur)}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          {payments!.payments.length > 0 ? (
            <table className="tbl">
              <thead>
                <tr><th>Fecha</th><th>Método</th><th>Ref.</th><th className="num">Monto</th><th></th></tr>
              </thead>
              <tbody>
                {payments!.payments.map((p) => (
                  <tr key={p.id}>
                    <td className="mono" style={{ fontSize: 12 }}>{p.paid_at}</td>
                    <td>{p.method}</td>
                    <td className="mono" style={{ fontSize: 12 }}>{p.reference ?? "—"}</td>
                    <td className="num">{money(p.amount, cur)}</td>
                    <td>
                      {canWrite ? (
                        <button className="btn ghost" disabled={busy}
                          onClick={() => act(() => deletePayment(caseId, p.id))}>✕</button>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : null}
          {payments!.balance > 0 ? (
            <div className="form-row" style={{ paddingTop: 0 }}>
              {canWrite ? (
                <button className="btn ghost" disabled={busy} onClick={remind}>
                  Recordar al cliente
                </button>
              ) : null}
              {s.last_reminder_at ? (
                <span className="tag" style={{ color: "var(--muted)" }}>
                  Último recordatorio: {new Date(s.last_reminder_at).toLocaleDateString("es-EC")}
                </span>
              ) : null}
            </div>
          ) : null}

          {canWrite && payments!.balance > 0 ? (
            <div className="form-row" style={{ borderTop: "1px solid var(--border-soft)", flexWrap: "wrap" }}>
              <input type="text" placeholder="Monto" value={np.amount}
                onChange={(e) => setNp((p) => ({ ...p, amount: e.target.value }))} style={{ width: 100 }} />
              <input type="date" value={np.paid_at}
                onChange={(e) => setNp((p) => ({ ...p, paid_at: e.target.value }))} />
              <select value={np.method} onChange={(e) => setNp((p) => ({ ...p, method: e.target.value }))}>
                {PAY_METHODS.map((m) => <option key={m} value={m}>{m}</option>)}
              </select>
              <input type="text" placeholder="Referencia" value={np.reference}
                onChange={(e) => setNp((p) => ({ ...p, reference: e.target.value }))} style={{ width: 130 }} />
              <button className="btn" disabled={busy} onClick={addPay}>+ Pago</button>
            </div>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
