import { cookies } from "next/headers";

import { apiGet } from "@/app/lib/api";
import { capsFromRoles, parseRolesCookie } from "@/app/lib/rbac";
import { PriceBandAdmin } from "@/app/components/PriceBandAdmin";
import { TariffAdmin } from "@/app/components/TariffAdmin";
import { TariffTierAdmin } from "@/app/components/TariffTierAdmin";
import { TradeRemedyAdmin } from "@/app/components/TradeRemedyAdmin";
import { TariffLookup } from "@/app/components/TariffLookup";

export const dynamic = "force-dynamic";

interface Version {
  id: string; number: string; status: string;
  codes_count: number; rules_count: number; published_at?: string | null; created_at: string;
}

interface SyncStatus {
  active_version: { number: string; status: string; codes_count: number; rules_count: number } | null;
  total_codes: number;
  total_active_rules: number;
  last_import_status: string | null;
}

export default async function TariffPage() {
  const caps = capsFromRoles(parseRolesCookie(cookies().get("caop_roles")?.value));
  const status = await apiGet<SyncStatus>("/tariff/sync-status");
  const ver = status?.active_version ?? null;
  const versions = caps.canAdmin ? (await apiGet<Version[]>("/tariff/versions")) ?? [] : [];
  const agreements = caps.canAdmin ? (await apiGet<unknown[]>("/tariff/agreements")) ?? [] : [];
  const preferences = caps.canAdmin ? (await apiGet<unknown[]>("/tariff/preferences")) ?? [] : [];
  const iceMeasures = caps.canAdmin ? (await apiGet<unknown[]>("/tariff/ice-measures")) ?? [] : [];
  const priceBands = caps.canAdmin ? (await apiGet<unknown[]>("/tariff/price-bands")) ?? [] : [];
  const remedies = caps.canAdmin ? (await apiGet<unknown[]>("/tariff/trade-remedies")) ?? [] : [];
  const tiers = caps.canAdmin ? (await apiGet<unknown[]>("/tariff/tiers")) ?? [] : [];

  return (
    <>
      <div className="topbar">
        <div>
          <div className="eyebrow">Arancel del Ecuador</div>
          <h1>Consulta arancelaria</h1>
        </div>
      </div>

      <div className="cards-row section-gap" style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
        <div className="card" style={{ flex: 1, minWidth: 180 }}>
          <div className="eyebrow">Versión vigente</div>
          <div style={{ fontSize: 20, fontWeight: 700 }}>{ver ? ver.number : "— sin cargar —"}</div>
          <div style={{ color: "var(--muted-2)", fontSize: 12 }}>{ver ? ver.status : "importa el arancel"}</div>
        </div>
        <div className="card" style={{ flex: 1, minWidth: 140 }}>
          <div className="eyebrow">Subpartidas</div>
          <div style={{ fontSize: 20, fontWeight: 700 }}>{status?.total_codes ?? 0}</div>
        </div>
        <div className="card" style={{ flex: 1, minWidth: 140 }}>
          <div className="eyebrow">Reglas Ad-Valorem</div>
          <div style={{ fontSize: 20, fontWeight: 700 }}>{status?.total_active_rules ?? 0}</div>
        </div>
      </div>

      {!ver ? (
        <div className="blocker-banner section-gap" style={{ borderColor: "rgba(45,212,191,0.3)", color: "var(--muted)" }}>
          Aún no hay una versión arancelaria activa. Un administrador debe importar el
          Arancel del Ecuador (PDF oficial) vía <code>POST /api/v1/tariff/import</code> y publicarla.
        </div>
      ) : null}

      {caps.canAdmin ? (
        <TariffAdmin
          versions={versions}
          agreements={agreements as never[]}
          preferences={preferences as never[]}
          iceMeasures={iceMeasures as never[]}
        />
      ) : null}

      {caps.canAdmin ? <PriceBandAdmin measures={priceBands as never[]} /> : null}

      {caps.canAdmin ? <TradeRemedyAdmin remedies={remedies as never[]} /> : null}

      {caps.canAdmin ? <TariffTierAdmin tiers={tiers as never[]} /> : null}

      <TariffLookup />
    </>
  );
}
