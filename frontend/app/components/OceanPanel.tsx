"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { addContainer, updateContainer, updateTransport } from "@/app/lib/actions";
import { alarmClass, type DemurrageSummary, money, type Transport } from "@/app/lib/format";

const T_FIELDS: [keyof Transport, string][] = [
  ["carrier", "Naviera / Aerolínea"],
  ["load_type", "Tipo (FCL/LCL/AIR)"],
  ["vessel", "Buque"],
  ["voyage", "Viaje"],
  ["flight_number", "Vuelo"],
  ["mbl_number", "MBL"],
  ["hbl_number", "HBL"],
  ["mawb_number", "MAWB"],
  ["hawb_number", "HAWB"],
  ["pol", "Origen (POL)"],
  ["pod", "Destino (POD)"],
  ["etd", "ETD"],
  ["eta", "ETA"],
  ["ata", "ATA"],
];
const DATE_FIELDS = new Set(["etd", "eta", "ata"]);

export function OceanPanel({
  caseId,
  transport,
  summary,
}: {
  caseId: string;
  transport: Transport | null;
  summary: DemurrageSummary | null;
}) {
  const router = useRouter();
  const [editing, setEditing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState<Record<string, string>>(() => {
    const f: Record<string, string> = {};
    T_FIELDS.forEach(([k]) => {
      f[k] = (transport?.[k] as string) ?? "";
    });
    return f;
  });
  const [nc, setNc] = useState({ container_number: "", iso_type: "40HC", arrival_date: "", free_days: "5", daily_rate: "0" });

  async function saveTransport() {
    setBusy(true);
    try {
      const payload: Record<string, unknown> = {};
      for (const [k] of T_FIELDS) payload[k] = form[k] || null;
      await updateTransport(caseId, payload);
      setEditing(false);
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  async function saveContainer() {
    if (!nc.container_number) return;
    setBusy(true);
    try {
      await addContainer(caseId, {
        container_number: nc.container_number,
        iso_type: nc.iso_type || null,
        arrival_date: nc.arrival_date || null,
        free_days: nc.free_days ? Number(nc.free_days) : null,
        daily_rate: nc.daily_rate ? Number(nc.daily_rate) : 0,
        status: "AT_PORT",
      });
      setNc({ container_number: "", iso_type: "40HC", arrival_date: "", free_days: "5", daily_rate: "0" });
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  async function returnContainer(id: string) {
    setBusy(true);
    try {
      await updateContainer(caseId, id, {
        status: "EMPTY_RETURNED",
        empty_return_date: new Date().toISOString().slice(0, 10),
      });
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  const containers = summary?.containers ?? [];

  return (
    <div className="card section-gap rise">
      <div className="head">
        <h2>Transporte y contenedores</h2>
        <button className="btn ghost" onClick={() => setEditing((e) => !e)}>
          {editing ? "Cerrar" : "Editar transporte"}
        </button>
      </div>

      {editing ? (
        <div className="card-pad">
          <div className="grid-2">
            {T_FIELDS.map(([k, label]) => (
              <label className="field" key={k}>
                <span>{label}</span>
                <input
                  type={DATE_FIELDS.has(k) ? "date" : "text"}
                  value={form[k]}
                  onChange={(e) => setForm((p) => ({ ...p, [k]: e.target.value }))}
                />
              </label>
            ))}
          </div>
          <div style={{ marginTop: 12 }}>
            <button className="btn" disabled={busy} onClick={saveTransport}>
              Guardar transporte
            </button>
          </div>
        </div>
      ) : (
        <div className="card-pad" style={{ display: "flex", gap: 22, flexWrap: "wrap", fontSize: 13 }}>
          {transport?.carrier ? <span><b>{transport.carrier}</b></span> : <span className="muted">Sin datos de transporte.</span>}
          {transport?.vessel ? <span className="mono">{transport.vessel} {transport.voyage ?? ""}</span> : null}
          {transport?.flight_number ? <span className="mono">Vuelo {transport.flight_number}</span> : null}
          {transport?.mbl_number ? <span className="mono">MBL {transport.mbl_number}</span> : null}
          {transport?.hbl_number ? <span className="mono">HBL {transport.hbl_number}</span> : null}
          {transport?.mawb_number ? <span className="mono">MAWB {transport.mawb_number}</span> : null}
          {transport?.pol || transport?.pod ? <span className="mono">{transport?.pol ?? "?"} → {transport?.pod ?? "?"}</span> : null}
          {transport?.eta ? <span>ETA {transport.eta}</span> : null}
        </div>
      )}

      {summary && summary.money_at_risk > 0 ? (
        <div className="blocker-banner" style={{ margin: "0 18px 12px" }}>
          <span className={`pill ${alarmClass(summary.max_alarm)}`}>{summary.max_alarm}</span>
          Money at risk (demurrage): <b>{money(summary.money_at_risk)}</b>
        </div>
      ) : null}

      {containers.length > 0 ? (
        <div style={{ overflowX: "auto" }}>
          <table className="tbl">
            <thead>
              <tr>
                <th>Contenedor</th><th>Tipo</th><th>Arribo</th><th>Free</th>
                <th>Last free day</th><th className="num">Días venc.</th>
                <th className="num">Demurrage est.</th><th>Alarma</th><th></th>
              </tr>
            </thead>
            <tbody>
              {containers.map((c) => (
                <tr key={c.id}>
                  <td className="code">{c.container_number}</td>
                  <td className="mono">{c.iso_type ?? "—"}</td>
                  <td className="mono">{c.arrival_date ?? "—"}</td>
                  <td className="num">{c.free_days ?? "—"}</td>
                  <td className="mono">{c.last_free_day ?? "—"}</td>
                  <td className="num">{c.days_overdue}</td>
                  <td className="num">{money(c.estimated_demurrage)}</td>
                  <td><span className={`pill ${alarmClass(c.alarm)}`}>{c.alarm}</span></td>
                  <td>
                    {c.status !== "EMPTY_RETURNED" ? (
                      <button className="btn ghost" disabled={busy} onClick={() => returnContainer(c.id)}>
                        Devolver
                      </button>
                    ) : (
                      <span className="pill ok">Devuelto</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="empty">Sin contenedores registrados.</div>
      )}

      <div className="form-row" style={{ borderTop: "1px solid var(--border-soft)" }}>
        <input type="text" placeholder="Nº contenedor" value={nc.container_number} onChange={(e) => setNc((p) => ({ ...p, container_number: e.target.value }))} style={{ width: 150 }} />
        <input type="text" placeholder="Tipo" value={nc.iso_type} onChange={(e) => setNc((p) => ({ ...p, iso_type: e.target.value }))} style={{ width: 80 }} />
        <label className="muted" style={{ fontSize: 12 }}>Arribo <input type="date" value={nc.arrival_date} onChange={(e) => setNc((p) => ({ ...p, arrival_date: e.target.value }))} /></label>
        <label className="muted" style={{ fontSize: 12 }}>Free días <input type="text" value={nc.free_days} onChange={(e) => setNc((p) => ({ ...p, free_days: e.target.value }))} style={{ width: 50 }} /></label>
        <label className="muted" style={{ fontSize: 12 }}>Tarifa/día <input type="text" value={nc.daily_rate} onChange={(e) => setNc((p) => ({ ...p, daily_rate: e.target.value }))} style={{ width: 70 }} /></label>
        <button className="btn" disabled={busy} onClick={saveContainer}>+ Contenedor</button>
      </div>
    </div>
  );
}
