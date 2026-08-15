import Link from "next/link";

import { apiGet, money, type Receivables, stateLabel } from "@/app/lib/api";
import { ExportCsvButton } from "@/app/components/ExportCsvButton";
import { Donut, LineChart } from "@/app/components/charts";

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

export default async function ReportsPage() {
  const d = await apiGet<Overview>("/analytics/overview");
  const ops = await apiGet<Operations>("/analytics/operations");
  const rec = await apiGet<Receivables>("/analytics/receivables");

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

      <div className="cols">
        <div className="card rise">
          <div className="head"><h2>Expedientes por estado</h2></div>
          <Donut data={Object.entries(d.cases.by_state).map(([k, v]) => ({ label: stateLabel(k), value: v }))} />
        </div>
        <div className="card rise">
          <div className="head">
            <h2>Cotizaciones por estado</h2>
            <span className="count">{d.commercial.total_quotes}</span>
          </div>
          <Donut data={Object.entries(d.commercial.by_status).map(([k, v]) => ({ label: k, value: v }))} />
        </div>
      </div>
      <div className="section-gap" />

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

          <div className="card section-gap rise">
            <div className="head"><h2>Throughput mensual</h2></div>
            {ops.throughput.length === 0 ? (
              <div className="empty">Sin datos.</div>
            ) : (
              <LineChart
                labels={ops.throughput.map((m) => m.month)}
                series={[
                  { label: "Creados", color: "var(--accent)", points: ops.throughput.map((m) => m.created) },
                  { label: "Liberados", color: "var(--ok)", points: ops.throughput.map((m) => m.released) },
                ]}
              />
            )}
          </div>

          <div className="cols">
            <div className="card rise">
              <div className="head"><h2>Canal de aforo</h2></div>
              <Donut data={Object.entries(ops.aforo).map(([k, v]) => ({ label: k, value: v }))} />
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
          <div className="section-gap" />
        </>
      ) : null}

      {rec ? (
        <>
          <div className="kpis">
            <Kpi label="Por cobrar (total)" value={money(rec.total_balance)} cls={rec.total_balance ? "warn" : "ok"} sub="saldo pendiente" />
            <Kpi label="Corriente" value={money(rec.aging["corriente"] ?? 0)} />
            <Kpi label="31-60 días" value={money(rec.aging["31-60"] ?? 0)} cls={(rec.aging["31-60"] ?? 0) ? "warn" : ""} />
            <Kpi label="60+ días" value={money(rec.aging["60+"] ?? 0)} cls={(rec.aging["60+"] ?? 0) ? "warn" : "ok"} />
          </div>

          <div className="card rise">
            <div className="head">
              <h2>Cuentas por cobrar</h2>
              <div className="actions">
                <ExportCsvButton path="receivables.csv" filename="cuentas_por_cobrar.csv" />
                <span className="count">{rec.items.length}</span>
              </div>
            </div>
            {rec.items.length === 0 ? (
              <div className="empty">Sin saldos pendientes. 🟢</div>
            ) : (
              <div style={{ overflowX: "auto" }}>
                <table className="tbl">
                  <thead>
                    <tr>
                      <th>Liquidación</th><th>Cliente</th><th className="num">Total</th>
                      <th className="num">Saldo</th><th>Vence</th><th className="num">Días</th><th>Aging</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rec.items.map((x) => (
                      <tr key={x.settlement_id}>
                        <td className="mono" style={{ fontSize: 12 }}>
                          {x.customs_case_id ? (
                            <Link href={`/cases/${x.customs_case_id}`} style={{ color: "var(--accent)" }}>
                              {x.settlement_number}
                            </Link>
                          ) : x.settlement_number}
                        </td>
                        <td>{x.customer}</td>
                        <td className="num">{money(x.total, x.currency)}</td>
                        <td className="num">{money(x.balance, x.currency)}</td>
                        <td className="mono" style={{ fontSize: 12 }}>{x.due_date ?? "—"}</td>
                        <td className="num">{x.days_overdue}</td>
                        <td><span className={`pill ${x.bucket === "corriente" ? "" : x.bucket === "60+" ? "crit" : "warn"}`}>{x.bucket}</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
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

