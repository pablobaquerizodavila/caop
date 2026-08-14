import { apiGet, stateLabel } from "@/app/lib/api";

export const dynamic = "force-dynamic";

interface Overview {
  cases: {
    total: number;
    ready_for_customs: number;
    avg_readiness: number;
    by_state: Record<string, number>;
    avg_prep_hours: number;
  };
  automation: {
    human_touches_per_shipment: number;
    straight_through_rate: number;
    automation_rate: number;
    system_events: number;
    user_events: number;
  };
  commercial: {
    total_quotes: number;
    accepted: number;
    conversion_rate: number;
    by_status: Record<string, number>;
  };
  notifications: { total: number; by_status: Record<string, number> };
  sla: { open: number; at_risk: number; breached: number };
}

const STATE_COLOR: Record<string, string> = {
  READY_FOR_CUSTOMS: "var(--ok)",
  AWAITING_DOCUMENTS: "var(--warn)",
  CASE_CREATED: "var(--accent)",
};

export default async function ReportsPage() {
  const d = await apiGet<Overview>("/analytics/overview");

  if (!d) {
    return (
      <>
        <Topbar />
        <div className="card">
          <div className="empty">No se pudo cargar analytics.</div>
        </div>
      </>
    );
  }

  return (
    <>
      <Topbar />

      <div className="kpis">
        <Kpi label="Automation rate" value={`${d.automation.automation_rate}`} unit="%" cls="ok" sub="eventos del sistema vs. totales" />
        <Kpi label="Straight-through" value={`${d.automation.straight_through_rate}`} unit="%" cls="accent" sub="expedientes sin intervención" />
        <Kpi label="Human touches / exp." value={`${d.automation.human_touches_per_shipment}`} cls="warn" sub="objetivo: reducir" />
        <Kpi label="Conversión cotizaciones" value={`${d.commercial.conversion_rate}`} unit="%" sub={`${d.commercial.accepted}/${d.commercial.total_quotes} aceptadas`} />
      </div>

      <div className="kpis">
        <Kpi label="Expedientes" value={`${d.cases.total}`} cls="accent" />
        <Kpi label="Listos para aduana" value={`${d.cases.ready_for_customs}`} cls="ok" />
        <Kpi label="Readiness promedio" value={`${d.cases.avg_readiness}`} unit="%" />
        <Kpi label="Prep. promedio" value={`${d.cases.avg_prep_hours}`} unit="h" sub="creado → listo" />
      </div>

      <div className="card section-gap rise">
        <div className="head">
          <h2>Expedientes por estado</h2>
        </div>
        <Bars data={d.cases.by_state} labelFn={stateLabel} colorFn={(k) => STATE_COLOR[k] ?? "var(--accent)"} />
      </div>

      <div className="card section-gap rise">
        <div className="head">
          <h2>Cotizaciones por estado</h2>
          <span className="count">{d.commercial.total_quotes}</span>
        </div>
        <Bars data={d.commercial.by_status} />
      </div>

      <div className="kpis">
        <Kpi label="SLA abiertos" value={`${d.sla.open}`} />
        <Kpi label="SLA en riesgo" value={`${d.sla.at_risk}`} cls={d.sla.at_risk ? "warn" : "ok"} />
        <Kpi label="SLA incumplidos" value={`${d.sla.breached}`} cls={d.sla.breached ? "warn" : "ok"} />
        <Kpi label="Notificaciones" value={`${d.notifications.total}`} sub="enviadas" />
      </div>
    </>
  );
}

function Topbar() {
  return (
    <div className="topbar">
      <div>
        <div className="eyebrow">Dirección · KPIs</div>
        <h1>Reportes</h1>
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
  sub,
}: {
  label: string;
  value: string;
  unit?: string;
  cls?: string;
  sub?: string;
}) {
  return (
    <div className={`kpi ${cls ?? ""}`}>
      <div className="label">{label}</div>
      <div className="value">
        {value}
        {unit ? <small>{unit}</small> : null}
      </div>
      {sub ? <div className="sub2">{sub}</div> : null}
    </div>
  );
}

function Bars({
  data,
  labelFn,
  colorFn,
}: {
  data: Record<string, number>;
  labelFn?: (k: string) => string;
  colorFn?: (k: string) => string;
}) {
  const entries = Object.entries(data).sort((a, b) => b[1] - a[1]);
  const max = Math.max(1, ...entries.map(([, v]) => v));
  if (entries.length === 0) {
    return <div className="empty">Sin datos.</div>;
  }
  return (
    <div className="bars">
      {entries.map(([k, v]) => (
        <div className="bar-row" key={k}>
          <span className="lbl">{labelFn ? labelFn(k) : k}</span>
          <div className="track2">
            <div
              className="fill2"
              style={{
                width: `${(v / max) * 100}%`,
                background: colorFn ? colorFn(k) : "var(--accent)",
              }}
            />
          </div>
          <span className="n">{v}</span>
        </div>
      ))}
    </div>
  );
}
