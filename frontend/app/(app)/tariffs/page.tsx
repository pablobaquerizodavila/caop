import { apiGet, type WarehouseTariff } from "@/app/lib/api";
import { WarehouseTariffsEditor } from "@/app/components/WarehouseTariffsEditor";

export const dynamic = "force-dynamic";

export default async function TariffsPage() {
  const tariffs = (await apiGet<WarehouseTariff[]>("/warehouse/tariffs")) ?? [];

  return (
    <>
      <div className="topbar">
        <div>
          <div className="eyebrow">Configuración · Logística</div>
          <h1>Tarifarios de bodega</h1>
        </div>
      </div>

      <div className="blocker-banner section-gap" style={{ background: "rgba(45,212,191,0.08)", borderColor: "rgba(45,212,191,0.3)", color: "var(--muted)" }}>
        Tarifas de almacenaje por depósito temporal. Se usan para <b>autocompletar</b> el
        registro de almacenaje de un embarque (días libres, tipo de tarifa y valor).
      </div>

      <WarehouseTariffsEditor tariffs={tariffs} />
    </>
  );
}
