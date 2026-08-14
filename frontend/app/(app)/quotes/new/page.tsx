import Link from "next/link";

import { apiGet, type CustomerSummary } from "@/app/lib/api";
import { NewQuoteForm } from "@/app/components/NewQuoteForm";

export const dynamic = "force-dynamic";

export default async function NewQuotePage() {
  const customers = (await apiGet<CustomerSummary[]>("/customers?limit=200")) ?? [];

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
        <NewQuoteForm customers={customers} />
      </div>
    </>
  );
}
