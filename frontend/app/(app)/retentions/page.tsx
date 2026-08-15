import { apiGet, type Retention } from "@/app/lib/api";
import { RetentionsManager } from "@/app/components/RetentionsManager";

export const dynamic = "force-dynamic";

export default async function RetentionsPage() {
  const retentions = (await apiGet<Retention[]>("/retentions")) ?? [];

  return (
    <>
      <div className="topbar">
        <div>
          <div className="eyebrow">Tributario · SRI</div>
          <h1>Comprobantes de retención</h1>
        </div>
      </div>

      <div className="blocker-banner section-gap" style={{ background: "rgba(45,212,191,0.08)", borderColor: "rgba(45,212,191,0.3)", color: "var(--muted)" }}>
        Emisión en <b>modo simulador</b> (clave de acceso y XML oficiales; firma y
        autorización simuladas, sin transmisión real al SRI). Verifica los códigos y
        porcentajes de retención vigentes.
      </div>

      <RetentionsManager retentions={retentions} />
    </>
  );
}
