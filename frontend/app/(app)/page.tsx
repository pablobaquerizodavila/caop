import Link from "next/link";

import {
  apiGet,
  type CaseSummary,
  readiness,
  SLA_RISKY,
  type SlaRisk,
  slaChipClass,
} from "@/app/lib/api";
import { CaseRow } from "@/app/components/ui";

export const dynamic = "force-dynamic";

export default async function ControlTower() {
  const cases = (await apiGet<CaseSummary[]>("/cases?limit=200")) ?? null;
  const slas = (await apiGet<SlaRisk[]>("/sla?limit=500")) ?? [];

  if (cases === null) {
    return (
      <>
        <Topbar />
        <div className="card">
          <div className="empty">
            No se pudo conectar con el backend en <span className="mono">/api/v1/cases</span>.
          </div>
        </div>
      </>
    );
  }

  const awaiting = cases.filter((c) => c.current_state === "AWAITING_DOCUMENTS");
  const ready = cases.filter((c) => c.current_state === "READY_FOR_CUSTOMS");
  const exceptions = cases
    .filter((c) => c.blocker || c.current_state === "AWAITING_DOCUMENTS")
    .sort((a, b) => readiness(a.customs_readiness_score) - readiness(b.customs_readiness_score));
  const avg =
    cases.length === 0
      ? 0
      : Math.round(cases.reduce((s, c) => s + readiness(c.customs_readiness_score), 0) / cases.length);

  const caseNumber = new Map(cases.map((c) => [c.id, c.case_number]));
  const riskySla = slas
    .filter((s) => SLA_RISKY.includes(s.status))
    .sort((a, b) => b.escalation_level - a.escalation_level);

  return (
    <>
      <Topbar />

      <div className="kpis">
        <Kpi label="Expedientes activos" value={String(cases.length)} cls="accent" delay={0} />
        <Kpi label="Esperando documentos" value={String(awaiting.length)} cls="warn" delay={60} />
        <Kpi
          label="SLA en riesgo"
          value={String(riskySla.length)}
          cls={riskySla.length ? "warn" : "ok"}
          delay={120}
        />
        <Kpi label="Readiness promedio" value={`${avg}`} unit="%" delay={180} />
      </div>

      {riskySla.length > 0 ? (
        <div className="card exception section-gap rise">
          <div className="head">
            <h2>SLA en riesgo</h2>
            <span className="count">{riskySla.length}</span>
          </div>
          <div style={{ overflowX: "auto" }}>
            <table className="tbl">
              <thead>
                <tr>
                  <th>Estado</th>
                  <th>Hito</th>
                  <th>Expediente</th>
                  <th>Nivel escal.</th>
                  <th>Vence</th>
                </tr>
              </thead>
              <tbody>
                {riskySla.map((s) => (
                  <tr key={s.id}>
                    <td>
                      <span className={`pill ${slaChipClass(s.status)}`}>{s.status}</span>
                    </td>
                    <td className="mono" style={{ fontSize: 12.5 }}>
                      {s.milestone}
                    </td>
                    <td>
                      {caseNumber.get(s.entity_id) ? (
                        <Link href={`/cases/${s.entity_id}`} className="code">
                          {caseNumber.get(s.entity_id)}
                        </Link>
                      ) : (
                        <span className="mono" style={{ color: "var(--muted-2)" }}>
                          —
                        </span>
                      )}
                    </td>
                    <td className="mono">{s.escalation_level}</td>
                    <td className="mono" style={{ color: "var(--muted)", fontSize: 12 }}>
                      {s.deadline ? new Date(s.deadline).toLocaleString("es-EC") : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}

      <div className="card exception section-gap rise">
        <div className="head">
          <h2>Requiere atención</h2>
          <span className="count">{exceptions.length}</span>
        </div>
        {exceptions.length === 0 ? (
          <div className="empty">Sin excepciones. La plataforma está al día. 🟢</div>
        ) : (
          <Table rows={exceptions} />
        )}
      </div>

      <div className="card section-gap rise">
        <div className="head">
          <h2>Listos para aduana</h2>
          <span className="count">{ready.length}</span>
        </div>
        {ready.length === 0 ? (
          <div className="empty">Ningún expediente listo para transmisión todavía.</div>
        ) : (
          <Table rows={ready} />
        )}
      </div>

      <div className="card rise">
        <div className="head">
          <h2>Todos los expedientes</h2>
          <span className="count">{cases.length}</span>
        </div>
        {cases.length === 0 ? (
          <div className="empty">Aún no hay expedientes. Se crean al aceptar una cotización.</div>
        ) : (
          <Table rows={cases} />
        )}
      </div>
    </>
  );
}

function Topbar() {
  return (
    <div className="topbar">
      <div>
        <div className="eyebrow">Operaciones · SENAE / ECUAPASS</div>
        <h1>Torre de Control</h1>
      </div>
      <div className="live">
        <span className="pulse" /> en vivo
      </div>
    </div>
  );
}

function Kpi({
  label,
  value,
  unit,
  cls,
  delay = 0,
}: {
  label: string;
  value: string;
  unit?: string;
  cls?: string;
  delay?: number;
}) {
  return (
    <div className={`kpi ${cls ?? ""}`} style={{ animationDelay: `${delay}ms` }}>
      <div className="label">{label}</div>
      <div className="value">
        {value}
        {unit ? <small>{unit}</small> : null}
      </div>
    </div>
  );
}

function Table({ rows }: { rows: CaseSummary[] }) {
  return (
    <div style={{ overflowX: "auto" }}>
      <table className="tbl">
        <thead>
          <tr>
            <th style={{ width: 40 }} />
            <th>Expediente</th>
            <th>Estado</th>
            <th>Readiness</th>
            <th>Bloqueo</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((c) => (
            <CaseRow key={c.id} c={c} />
          ))}
        </tbody>
      </table>
    </div>
  );
}
