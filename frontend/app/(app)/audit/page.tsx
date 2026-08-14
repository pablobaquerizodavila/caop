import Link from "next/link";

import { apiGet, type AuditEvent } from "@/app/lib/api";

export const dynamic = "force-dynamic";

const ACTION_CLS: Record<string, string> = { CREATE: "ok", UPDATE: "warn", DELETE: "crit" };
const FILTERS = ["", "customs_case", "quote", "document", "vue_permit", "settlement", "customer"];

export default async function AuditPage({
  searchParams,
}: {
  searchParams: { entity?: string };
}) {
  const entity = searchParams.entity ?? "";
  const qs = entity ? `?entity=${encodeURIComponent(entity)}&limit=300` : "?limit=300";
  const events = await apiGet<AuditEvent[]>(`/audit${qs}`);

  return (
    <>
      <div className="topbar">
        <div>
          <div className="eyebrow">Cumplimiento · Trazabilidad</div>
          <h1>Auditoría</h1>
        </div>
      </div>

      <div className="form-row" style={{ gap: 6, flexWrap: "wrap", paddingLeft: 0 }}>
        {FILTERS.map((f) => (
          <Link
            key={f || "all"}
            href={f ? `/audit?entity=${f}` : "/audit"}
            className={`pill ${entity === f ? "accent" : ""}`}
          >
            {f || "todos"}
          </Link>
        ))}
      </div>

      <div className="card rise">
        <div className="head">
          <h2>Eventos de auditoría</h2>
          <span className="count">{events?.length ?? 0}</span>
        </div>
        {events === null ? (
          <div className="empty">No tienes acceso a la auditoría (requiere rol de administración o auditor).</div>
        ) : events.length === 0 ? (
          <div className="empty">Sin eventos.</div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="tbl">
              <thead>
                <tr>
                  <th>Fecha</th><th>Acción</th><th>Entidad</th><th>ID</th><th>Rol</th>
                </tr>
              </thead>
              <tbody>
                {events.map((e) => (
                  <tr key={e.id}>
                    <td className="mono" style={{ fontSize: 11.5, color: "var(--muted)" }}>
                      {new Date(e.timestamp).toLocaleString("es-EC")}
                    </td>
                    <td><span className={`pill ${ACTION_CLS[e.action] ?? ""}`}>{e.action}</span></td>
                    <td className="mono" style={{ fontSize: 12 }}>{e.entity}</td>
                    <td className="mono" style={{ fontSize: 10.5, color: "var(--muted-2)" }}>
                      {e.entity_id ? e.entity_id.slice(0, 8) : "—"}
                    </td>
                    <td className="mono" style={{ fontSize: 11 }}>{e.role ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
