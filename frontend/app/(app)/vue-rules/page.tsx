import { apiGet, type VueRule } from "@/app/lib/api";
import { VueRulesEditor } from "@/app/components/VueRulesEditor";

export const dynamic = "force-dynamic";

export default async function VueRulesPage() {
  const rules = (await apiGet<VueRule[]>("/vue/rules")) ?? [];

  return (
    <>
      <div className="topbar">
        <div>
          <div className="eyebrow">Configuración · Control previo</div>
          <h1>Reglas HS → VUE</h1>
        </div>
      </div>

      <div className="blocker-banner section-gap" style={{ background: "rgba(45,212,191,0.08)", borderColor: "rgba(45,212,191,0.3)", color: "var(--muted)" }}>
        Catálogo <b>configurable de referencia</b>: al crear un expediente se autosugieren
        los controles previos cuya subpartida coincide con estos prefijos. Verifica las
        reglas contra la normativa vigente (INEN, ARCSA, Agrocalidad, MPCEIP, MSP).
      </div>

      <VueRulesEditor rules={rules} />
    </>
  );
}
