import { apiGet, type CaseSummary } from "@/app/lib/api";
import { CaseRow } from "@/app/components/ui";

export const dynamic = "force-dynamic";

export default async function CasesPage() {
  const cases = await apiGet<CaseSummary[]>("/cases?limit=200");

  return (
    <>
      <div className="topbar">
        <div>
          <div className="eyebrow">Importaciones</div>
          <h1>Expedientes</h1>
        </div>
      </div>

      <div className="card rise">
        <div className="head">
          <h2>Todos los expedientes</h2>
          <span className="count">{cases?.length ?? 0}</span>
        </div>
        {!cases || cases.length === 0 ? (
          <div className="empty">
            {cases === null
              ? "No se pudo conectar con el backend."
              : "Aún no hay expedientes. Se crean al aceptar una cotización."}
          </div>
        ) : (
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
                {cases.map((c) => (
                  <CaseRow key={c.id} c={c} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
