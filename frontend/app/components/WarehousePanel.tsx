"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { addWarehouse, deleteWarehouse, updateWarehouse } from "@/app/lib/actions";
import {
  alarmClass,
  money,
  RATE_TYPE_LABELS,
  type WarehouseSummary,
} from "@/app/lib/format";

const RATE_TYPES = ["PER_DAY", "PER_KG_DAY", "FLAT"];

export function WarehousePanel({
  caseId,
  summary,
}: {
  caseId: string;
  summary: WarehouseSummary | null;
}) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [ns, setNs] = useState({
    warehouse_name: "",
    reference: "",
    entry_date: "",
    free_days: "2",
    rate_type: "PER_KG_DAY",
    daily_rate: "0",
    chargeable_weight_kg: "",
  });

  const items = summary?.items ?? [];

  async function save() {
    if (!ns.entry_date && !ns.reference) return;
    setBusy(true);
    try {
      await addWarehouse(caseId, {
        warehouse_name: ns.warehouse_name || null,
        reference: ns.reference || null,
        entry_date: ns.entry_date || null,
        free_days: ns.free_days ? Number(ns.free_days) : null,
        rate_type: ns.rate_type,
        daily_rate: ns.daily_rate ? Number(ns.daily_rate) : 0,
        chargeable_weight_kg: ns.chargeable_weight_kg ? Number(ns.chargeable_weight_kg) : null,
        status: "IN_WAREHOUSE",
      });
      setNs({ ...ns, reference: "", entry_date: "", chargeable_weight_kg: "" });
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  async function withdraw(id: string) {
    setBusy(true);
    try {
      await updateWarehouse(caseId, id, {
        status: "WITHDRAWN",
        withdrawal_date: new Date().toISOString().slice(0, 10),
      });
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: string) {
    setBusy(true);
    try {
      await deleteWarehouse(caseId, id);
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card section-gap rise">
      <div className="head">
        <h2>Almacenaje / bodega</h2>
        <span className="count">{items.length}</span>
      </div>

      {summary && summary.money_at_risk > 0 ? (
        <div className="blocker-banner" style={{ margin: "0 18px 12px" }}>
          <span className={`pill ${alarmClass(summary.max_alarm)}`}>{summary.max_alarm}</span>
          Money at risk (almacenaje): <b>{money(summary.money_at_risk)}</b>
        </div>
      ) : null}

      {items.length > 0 ? (
        <div style={{ overflowX: "auto" }}>
          <table className="tbl">
            <thead>
              <tr>
                <th>Referencia</th><th>Bodega</th><th>Ingreso</th><th>Free</th>
                <th>Last free day</th><th className="num">Días venc.</th>
                <th className="num">Almacenaje est.</th><th>Alarma</th><th></th>
              </tr>
            </thead>
            <tbody>
              {items.map((s) => (
                <tr key={s.id}>
                  <td className="code">{s.reference ?? "—"}</td>
                  <td>{s.warehouse_name ?? "—"}</td>
                  <td className="mono">{s.entry_date ?? "—"}</td>
                  <td className="num">{s.free_days ?? "—"}</td>
                  <td className="mono">{s.last_free_day ?? "—"}</td>
                  <td className="num">{s.days_overdue}</td>
                  <td className="num">{money(s.estimated_storage)}</td>
                  <td><span className={`pill ${alarmClass(s.alarm)}`}>{s.alarm}</span></td>
                  <td>
                    {s.status !== "WITHDRAWN" ? (
                      <div className="actions">
                        <button className="btn ghost" disabled={busy} onClick={() => withdraw(s.id)}>
                          Retirar
                        </button>
                        <button className="btn ghost" disabled={busy} title="Eliminar" onClick={() => remove(s.id)}>
                          ✕
                        </button>
                      </div>
                    ) : (
                      <span className="pill ok">Retirado</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="empty">Sin registros de almacenaje.</div>
      )}

      <div className="form-row" style={{ borderTop: "1px solid var(--border-soft)", flexWrap: "wrap" }}>
        <input type="text" placeholder="Referencia (HAWB/lote)" value={ns.reference} onChange={(e) => setNs((p) => ({ ...p, reference: e.target.value }))} style={{ width: 150 }} />
        <input type="text" placeholder="Bodega" value={ns.warehouse_name} onChange={(e) => setNs((p) => ({ ...p, warehouse_name: e.target.value }))} style={{ width: 130 }} />
        <label className="muted" style={{ fontSize: 12 }}>Ingreso <input type="date" value={ns.entry_date} onChange={(e) => setNs((p) => ({ ...p, entry_date: e.target.value }))} /></label>
        <label className="muted" style={{ fontSize: 12 }}>Free días <input type="text" value={ns.free_days} onChange={(e) => setNs((p) => ({ ...p, free_days: e.target.value }))} style={{ width: 44 }} /></label>
        <select value={ns.rate_type} onChange={(e) => setNs((p) => ({ ...p, rate_type: e.target.value }))}>
          {RATE_TYPES.map((t) => (
            <option key={t} value={t}>{RATE_TYPE_LABELS[t]}</option>
          ))}
        </select>
        <label className="muted" style={{ fontSize: 12 }}>Tarifa <input type="text" value={ns.daily_rate} onChange={(e) => setNs((p) => ({ ...p, daily_rate: e.target.value }))} style={{ width: 64 }} /></label>
        {ns.rate_type === "PER_KG_DAY" ? (
          <label className="muted" style={{ fontSize: 12 }}>Peso kg <input type="text" value={ns.chargeable_weight_kg} onChange={(e) => setNs((p) => ({ ...p, chargeable_weight_kg: e.target.value }))} style={{ width: 64 }} /></label>
        ) : null}
        <button className="btn" disabled={busy} onClick={save}>+ Almacenaje</button>
      </div>
    </div>
  );
}
