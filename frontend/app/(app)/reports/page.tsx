import { apiGet, money, stateLabel } from "@/app/lib/api";

export const dynamic = "force-dynamic";

interface Operations {
  stages: { stage: string; avg_hours: number; n: number }[];
  throughput: { month: string; created: number; released: number }[];
  top_customers: { customer: string; cases: number; landed_cost: number }[];
  aforo: Record<string, number>;
  money_at_risk: { demurrage: number; storage: number; total: number };
}

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
  const ops = await apiGet<Operations>("/analytics/operations");

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

      {ops ? (
        <>
          <div className="topbar" style={{ marginTop: 34 }}>
            <div>
              <div className="eyebrow">Operación</div>
              <h1 style={{ fontSize: 19 }}>Reporte operativo</h1>
            </div>
          </div>

          <div className="kpis">
            <Kpi label="Dinero en riesgo" value={money(ops.money_at_risk.total)} cls={ops.money_at_risk.total ? "warn" : "ok"} sub="demurrage + almacenaje" />
            <Kpi label="Demurrage" value={money(ops.money_at_risk.demurrage)} sub="estimado" />
            <Kpi label="Almacenaje" value={money(ops.money_at_risk.storage)} sub="estimado" />
            <Kpi label="Expedientes liberados" value={`${ops.throughput.reduce((s, m) => s + m.released, 0)}`} cls="ok" sub="total histórico" />
          </div>

          <div className="card section-gap rise">
            <div className="head"><h2>Tiempos de ciclo por etapa</h2></div>
            {ops.stages.every((s) => s.n === 0) ? (
              <div className="empty">Aún no hay expedientes con etapas completadas.</div>
            ) : (
              <div className="bars">
                {ops.stages.map((s) => {
                  const max = Math.max(1, ...ops.stages.map((x) => x.avg_hours));
                  return (
                    <div className="bar-row" key={s.stage}>
                      <span className="lbl">{s.stage}</span>
                      <div className="track2">
                        <div className="fill2" style={{ width: `${(s.avg_hours / max) * 100}%`, background: "var(--accent)" }} />
                      </div>
                      <span className="n">{s.avg_hours}h</span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div className="cols">
            <div className="card rise">
              <div className="head"><h2>Throughput mensual</h2></div>
              {ops.throughput.length === 0 ? (
                <div className="empty">Sin datos.</div>
              ) : (
                <table className="tbl">
                  <thead><tr><th>Mes</th><th className="num">Creados</th><th className="num">Liberados</th></tr></thead>
                  <tbody>
                    {ops.throughput.map((m) => (
                      <tr key={m.month}>
                        <td className="mono">{m.month}</td>
                        <td className="num">{m.created}</td>
                        <td className="num">{m.released}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>

            <div className="card rise">
              <div className="head"><h2>Top clientes</h2></div>
              {ops.top_customers.length === 0 ? (
                <div className="empty">Sin datos.</div>
              ) : (
                <table className="tbl">
                  <thead><tr><th>Cliente</th><th className="num">Exp.</th><th className="num">Landed cost</th></tr></thead>
                  <tbody>
                    {ops.top_customers.map((c) => (
                      <tr key={c.customer}>
                        <td>{c.customer}</td>
                        <td className="num">{c.cases}</td>
                        <td className="num">{money(c.landed_cost)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>

          <div className="card section-gap rise">
            <div className="head"><h2>Canal de aforo</h2></div>
            <Bars data={ops.aforo} />
          </div>
        </>
      ) : null}
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
