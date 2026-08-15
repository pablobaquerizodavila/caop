import Link from "next/link";

import { apiGet, type CountryOption, type CustomerSummary } from "@/app/lib/api";
import { NewQuoteForm } from "@/app/components/NewQuoteForm";

export const dynamic = "force-dynamic";

export default async function NewQuotePage() {
  const customers = (await apiGet<CustomerSummary[]>("/customers?limit=200")) ?? [];
  const countries = (await apiGet<CountryOption[]>("/tariff/countries")) ?? [];

  return (
    <>
      <div className="eyebrow" style={{ marginBottom: 10 }}>
        <Link href="/quotes" style={{ color: "var(--accent)" }}>
          ← Cotizaciones
        </Link>
      </div>
      <div className="topbar">
        <div>
          <div className="eyebrow">Comercial</div>
          <h1>Nueva cotización</h1>
        </div>
      </div>
      <div className="card card-pad rise">
        <NewQuoteForm customers={customers} countries={countries} />
      </div>
    </>
  );
}
