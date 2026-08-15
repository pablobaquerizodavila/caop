import { apiGet, type Waybill } from "@/app/lib/api";
import { WaybillsManager } from "@/app/components/WaybillsManager";

export const dynamic = "force-dynamic";

export default async function WaybillsPage() {
  const waybills = (await apiGet<Waybill[]>("/waybills")) ?? [];

  return (
    <>
      <div className="topbar">
        <div>
          <div className="eyebrow">Tributario · SRI</div>
          <h1>Guías de remisión</h1>
        </div>
      </div>

      <div className="blocker-banner section-gap" style={{ background: "rgba(45,212,191,0.08)", borderColor: "rgba(45,212,191,0.3)", color: "var(--muted)" }}>
        Emisión en <b>modo simulador</b> (clave de acceso y XML oficiales; firma y
        autorización simuladas, sin transmisión real al SRI).
      </div>

      <WaybillsManager waybills={waybills} />
    </>
  );
}
