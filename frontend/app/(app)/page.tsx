import Link from "next/link";

import {
  alarmClass,
  apiGet,
  type AtRiskContainer,
  type AtRiskStorage,
  type CaseSummary,
  money,
  readiness,
  type Receivables,
  SLA_RISKY,
  type SlaRisk,
  slaChipClass,
} from "@/app/lib/api";
import { CaseRow } from "@/app/components/ui";
import { SendDigestButton } from "@/app/components/SendDigestButton";

export const dynamic = "force-dynamic";

export default async function ControlTower() {
  const cases = (await apiGet<CaseSummary[]>("/cases?limit=200")) ?? null;
  const slas = (await apiGet<SlaRisk[]>("/sla?limit=500")) ?? [];
  const demurrage = (await apiGet<AtRiskContainer[]>("/ocean/demurrage-at-risk")) ?? [];
  const storage = (await apiGet<AtRiskStorage[]>("/warehouse/at-risk")) ?? [];
  const receivables = await apiGet<Receivables>("/analytics/receivables");
  const overdue = (receivables?.items ?? []).filter((r) => r.days_overdue > 0);

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
        <Kpi
          label="Demurrage en riesgo"
          value={String(demurrage.length)}
          cls={demurrage.length ? "warn" : "ok"}
          delay={180}
        />
      </div>

      {demurrage.length > 0 ? (
        <div className="card exception section-gap rise">
          <div className="head">
            <h2>Demurrage en riesgo</h2>
            <span className="count">{demurrage.length}</span>
          </div>
          <div style={{ overflowX: "auto" }}>
            <table className="tbl">
              <thead>
                <tr>
                  <th>Alarma</th><th>Contenedor</th><th>Expediente</th>
                  <th className="num">Días a last free</th><th className="num">Demurrage est.</th>
                </tr>
              </thead>
              <tbody>
                {demurrage.map((x, i) => (
                  <tr key={i}>
                    <td><span className={`pill ${alarmClass(x.alarm)}`}>{x.alarm}</span></td>
                    <td className="code">{x.container_number}</td>
                    <td><Link href={`/cases/${x.case_id}`} className="code">{x.case_number}</Link></td>
                    <td className="num">{x.days_to_last_free_day ?? "—"}</td>
                    <td className="num">{money(x.estimated_demurrage)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}

      {storage.length > 0 ? (
        <div className="card exception section-gap rise">
          <div className="head">
            <h2>Almacenaje en riesgo</h2>
            <span className="count">{storage.length}</span>
          </div>
          <div style={{ overflowX: "auto" }}>
            <table className="tbl">
              <thead>
                <tr>
                  <th>Alarma</th><th>Referencia</th><th>Bodega</th><th>Expediente</th>
                  <th className="num">Días a last free</th><th className="num">Almacenaje est.</th>
                </tr>
              </thead>
              <tbody>
                {storage.map((x, i) => (
                  <tr key={i}>
                    <td><span className={`pill ${alarmClass(x.alarm)}`}>{x.alarm}</span></td>
                    <td className="code">{x.reference ?? "—"}</td>
                    <td>{x.warehouse_name ?? "—"}</td>
                    <td><Link href={`/cases/${x.case_id}`} className="code">{x.case_number}</Link></td>
                    <td className="num">{x.days_to_last_free_day ?? "—"}</td>
                    <td className="num">{money(x.estimated_storage)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}

      {overdue.length > 0 ? (
        <div className="card exception section-gap rise">
          <div className="head">
            <h2>Cobranza vencida</h2>
            <span className="count">{overdue.length}</span>
          </div>
          <div style={{ overflowX: "auto" }}>
            <table className="tbl">
              <thead>
                <tr>
                  <th>Liquidación</th><th>Cliente</th><th className="num">Saldo</th>
                  <th className="num">Días</th><th>Aging</th>
                </tr>
              </thead>
              <tbody>
                {overdue.map((x) => (
                  <tr key={x.settlement_id}>
                    <td className="code">
                      {x.customs_case_id ? (
                        <Link href={`/cases/${x.customs_case_id}`}>{x.settlement_number}</Link>
                      ) : x.settlement_number}
                    </td>
                    <td>{x.customer}</td>
                    <td className="num">{money(x.balance, x.currency)}</td>
                    <td className="num">{x.days_overdue}</td>
                    <td><span className={`pill ${x.bucket === "60+" ? "crit" : "warn"}`}>{x.bucket}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}

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
      <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
        <SendDigestButton />
        <div className="live">
          <span className="pulse" /> en vivo
        </div>
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
