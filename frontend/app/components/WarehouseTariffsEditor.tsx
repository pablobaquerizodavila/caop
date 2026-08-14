"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import {
  createWarehouseTariff,
  deleteWarehouseTariff,
  updateWarehouseTariff,
} from "@/app/lib/actions";
import { RATE_TYPE_LABELS, type WarehouseTariff } from "@/app/lib/format";

const RATE_TYPES = ["PER_DAY", "PER_KG_DAY", "FLAT"];
const MODES = [
  { v: "", label: "Todos" },
  { v: "OCEAN", label: "Marítimo" },
  { v: "AIR", label: "Aéreo" },
];

function TariffRow({ t }: { t: WarehouseTariff }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [f, setF] = useState({
    warehouse_name: t.warehouse_name,
    transport_mode: t.transport_mode ?? "",
    free_days: String(t.free_days),
    rate_type: t.rate_type,
    daily_rate: String(t.daily_rate),
    currency: t.currency,
    active: t.active,
  });

  const dirty =
    f.warehouse_name !== t.warehouse_name ||
    f.transport_mode !== (t.transport_mode ?? "") ||
    f.free_days !== String(t.free_days) ||
    f.rate_type !== t.rate_type ||
    f.daily_rate !== String(t.daily_rate) ||
    f.currency !== t.currency ||
    f.active !== t.active;

  async function save() {
    setBusy(true);
    try {
      const r = await updateWarehouseTariff(t.id, {
        warehouse_name: f.warehouse_name,
        transport_mode: f.transport_mode || null,
        free_days: Number(f.free_days) || 0,
        rate_type: f.rate_type,
        daily_rate: Number(f.daily_rate) || 0,
        currency: f.currency,
        active: f.active,
      });
      if (!r.ok) alert(r.error ?? "No se pudo guardar");
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    if (!confirm(`¿Eliminar la tarifa de ${t.warehouse_name}?`)) return;
    setBusy(true);
    try {
      await deleteWarehouseTariff(t.id);
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  return (
    <tr>
      <td><input className="rule-in" style={{ minWidth: 150 }} value={f.warehouse_name}
        onChange={(e) => setF((p) => ({ ...p, warehouse_name: e.target.value }))} /></td>
      <td>
        <select value={f.transport_mode} onChange={(e) => setF((p) => ({ ...p, transport_mode: e.target.value }))}>
          {MODES.map((m) => <option key={m.v} value={m.v}>{m.label}</option>)}
        </select>
      </td>
      <td className="num"><input className="rule-in num" style={{ width: 54 }} value={f.free_days}
        onChange={(e) => setF((p) => ({ ...p, free_days: e.target.value }))} /></td>
      <td>
        <select value={f.rate_type} onChange={(e) => setF((p) => ({ ...p, rate_type: e.target.value }))}>
          {RATE_TYPES.map((x) => <option key={x} value={x}>{RATE_TYPE_LABELS[x]}</option>)}
        </select>
      </td>
      <td className="num"><input className="rule-in num" style={{ width: 70 }} value={f.daily_rate}
        onChange={(e) => setF((p) => ({ ...p, daily_rate: e.target.value }))} /></td>
      <td><input className="rule-in mono" style={{ width: 54 }} value={f.currency}
        onChange={(e) => setF((p) => ({ ...p, currency: e.target.value }))} /></td>
      <td style={{ textAlign: "center" }}>
        <input type="checkbox" checked={f.active}
          onChange={(e) => setF((p) => ({ ...p, active: e.target.checked }))} />
      </td>
      <td>
        <div className="actions">
          {dirty ? <button className="btn" disabled={busy} onClick={save}>Guardar</button> : null}
          <button className="btn ghost" disabled={busy} title="Eliminar" onClick={remove}>✕</button>
        </div>
      </td>
    </tr>
  );
}

export function WarehouseTariffsEditor({ tariffs }: { tariffs: WarehouseTariff[] }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [nt, setNt] = useState({
    warehouse_name: "",
    transport_mode: "",
    free_days: "2",
    rate_type: "PER_KG_DAY",
    daily_rate: "0",
    currency: "USD",
  });

  async function add() {
    if (!nt.warehouse_name) return;
    setBusy(true);
    try {
      const r = await createWarehouseTariff({
        warehouse_name: nt.warehouse_name,
        transport_mode: nt.transport_mode || null,
        free_days: Number(nt.free_days) || 0,
        rate_type: nt.rate_type,
        daily_rate: Number(nt.daily_rate) || 0,
        currency: nt.currency,
      });
      if (!r.ok) alert(r.error ?? "No se pudo agregar");
      setNt({ ...nt, warehouse_name: "", daily_rate: "0" });
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <style>{`.rule-in{background:var(--surface-2);border:1px solid var(--border);color:var(--text);border-radius:6px;padding:6px 8px;font-size:12.5px;}.rule-in.num{text-align:right;font-family:var(--mono);}`}</style>

      <div className="card rise section-gap">
        <div className="head"><h2>Agregar tarifa</h2></div>
        <div className="form-row" style={{ flexWrap: "wrap", alignItems: "flex-end" }}>
          <label className="field" style={{ flex: 1, minWidth: 180 }}>
            <span>Depósito temporal</span>
            <input placeholder="Nombre del depósito" value={nt.warehouse_name}
              onChange={(e) => setNt((p) => ({ ...p, warehouse_name: e.target.value }))} />
          </label>
          <label className="field">
            <span>Modo</span>
            <select value={nt.transport_mode} onChange={(e) => setNt((p) => ({ ...p, transport_mode: e.target.value }))}>
              {MODES.map((m) => <option key={m.v} value={m.v}>{m.label}</option>)}
            </select>
          </label>
          <label className="field">
            <span>Free días</span>
            <input value={nt.free_days} onChange={(e) => setNt((p) => ({ ...p, free_days: e.target.value }))} style={{ width: 64 }} />
          </label>
          <label className="field">
            <span>Tipo tarifa</span>
            <select value={nt.rate_type} onChange={(e) => setNt((p) => ({ ...p, rate_type: e.target.value }))}>
              {RATE_TYPES.map((x) => <option key={x} value={x}>{RATE_TYPE_LABELS[x]}</option>)}
            </select>
          </label>
          <label className="field">
            <span>Tarifa</span>
            <input value={nt.daily_rate} onChange={(e) => setNt((p) => ({ ...p, daily_rate: e.target.value }))} style={{ width: 80 }} />
          </label>
          <label className="field">
            <span>Moneda</span>
            <input value={nt.currency} onChange={(e) => setNt((p) => ({ ...p, currency: e.target.value }))} style={{ width: 64 }} />
          </label>
          <button className="btn" disabled={busy || !nt.warehouse_name} onClick={add}>Agregar</button>
        </div>
      </div>

      <div className="card rise">
        <div className="head">
          <h2>Tarifas configuradas</h2>
          <span className="count">{tariffs.length}</span>
        </div>
        {tariffs.length === 0 ? (
          <div className="empty">Sin tarifas. Agrega las de tus depósitos temporales habituales.</div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="tbl">
              <thead>
                <tr>
                  <th>Depósito</th><th>Modo</th><th className="num">Free</th><th>Tipo</th>
                  <th className="num">Tarifa</th><th>Moneda</th>
                  <th style={{ textAlign: "center" }}>Activa</th><th></th>
                </tr>
              </thead>
              <tbody>
                {tariffs.map((t) => <TariffRow key={t.id} t={t} />)}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
