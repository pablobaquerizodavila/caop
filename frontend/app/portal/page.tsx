import Link from "next/link";

import { apiGet, type PortalCaseSummary, type PortalProfile } from "@/app/lib/api";

export const dynamic = "force-dynamic";

export default async function PortalHome() {
  const profile = await apiGet<PortalProfile>("/portal/me");

  if (!profile || !profile.linked) {
    return (
      <section className="trk-card">
        <h2>Bienvenido</h2>
        <p style={{ fontSize: 14, color: "var(--muted)", lineHeight: 1.6 }}>
          Tu cuenta aún no está vinculada a un cliente en nuestra plataforma. Contacta a tu
          ejecutivo de comercio exterior para habilitar el acceso a tus importaciones.
        </p>
      </section>
    );
  }

  const cases = (await apiGet<PortalCaseSummary[]>("/portal/cases")) ?? [];
  const c = profile.customer!;

  return (
    <>
      <section className="trk-card trk-hero">
        <div className="ref">{c.ruc}</div>
        <div className="cust">{c.trade_name || c.legal_name}</div>
      </section>

      <div className="trk-stats">
        <div className="trk-stat"><div className="n">{profile.cases}</div><div className="l">Importaciones</div></div>
        <div className="trk-stat"><div className="n">{profile.quotes}</div><div className="l">Cotizaciones</div></div>
        <div className="trk-stat"><div className="n">{cases.filter((x) => x.status_sem === "ok").length}</div><div className="l">Al día</div></div>
      </div>

      <section className="trk-card">
        <h2>Mis importaciones</h2>
        {cases.length === 0 ? (
          <div style={{ padding: 12, color: "var(--muted)" }}>Aún no tienes expedientes.</div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="trk-table">
              <thead>
                <tr><th>Expediente</th><th>Estado</th><th>Origen</th><th>Modo</th></tr>
              </thead>
              <tbody>
                {cases.map((x) => (
                  <tr key={x.id}>
                    <td><Link href={`/portal/cases/${x.id}`}>{x.case_number}</Link></td>
                    <td>
                      <span className="trk-badge">
                        <span className={`lamp ${x.status_sem}`} /> {x.status_label}
                      </span>
                    </td>
                    <td>{x.origin_country ?? "—"}</td>
                    <td>{x.transport_mode === "AIR" ? "Aéreo" : x.transport_mode === "OCEAN" ? "Marítimo" : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}
