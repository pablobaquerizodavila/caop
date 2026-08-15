"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { runTariffSync } from "@/app/lib/actions";

interface SyncLog {
  id: string; source_code?: string | null; status: string; found: number; new_count: number;
  detected?: string[] | null; error?: string | null; created_at: string;
}

export function SyncAdmin({ logs = [] }: { logs?: SyncLog[] }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  async function run() {
    setBusy(true);
    setMsg("Consultando fuentes oficiales…");
    try {
      const r = await runTariffSync();
      if (!r.ok) setMsg(`Error: ${r.error}`);
      else if (r.status === "NO_SOURCE") setMsg("No hay fuentes con URL configurada. Configura una fuente oficial (COMEX/Registro Oficial) con su URL.");
      else setMsg(`Sincronización OK: ${r.sources} fuente(s), ${r.new} resolución(es) nueva(s) detectada(s).`);
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card rise section-gap">
      <div className="head" style={{ justifyContent: "space-between" }}>
        <h2>Vigilante de fuentes oficiales</h2>
        <button className="btn" disabled={busy} onClick={run}>Sincronizar ahora</button>
      </div>
      <p style={{ color: "var(--muted)", fontSize: 12.5 }}>
        Detecta resoluciones nuevas en las fuentes configuradas (COMEX / Registro Oficial) y avisa.
        No modifica el arancel: la carga y aprobación siguen siendo manuales.
      </p>
      {msg ? <div style={{ fontSize: 12.5, color: "var(--muted)", marginBottom: 8 }}>{msg}</div> : null}
      {logs.length ? (
        <div style={{ overflowX: "auto" }}>
          <table className="tbl" style={{ width: "100%" }}>
            <thead><tr><th>Fecha</th><th>Fuente</th><th>Estado</th><th className="num">Halladas</th>
              <th className="num">Nuevas</th><th>Detectadas</th></tr></thead>
            <tbody>
              {logs.map((l) => (
                <tr key={l.id}>
                  <td style={{ fontSize: 12 }}>{new Date(l.created_at).toLocaleString()}</td>
                  <td className="mono">{l.source_code || "—"}</td>
                  <td><span className={`pill ${l.status === "OK" ? "ok" : l.status === "FAILED" ? "crit" : "warn"}`}>{l.status}</span></td>
                  <td className="num">{l.found}</td>
                  <td className="num">{l.new_count}</td>
                  <td style={{ fontSize: 11.5 }}>{(l.detected || []).join(", ") || (l.error ? l.error.slice(0, 40) : "—")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}
