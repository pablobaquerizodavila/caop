import Link from "next/link";

import { apiGet, type CountryOption, type CustomerSummary } from "@/app/lib/api";
import { NewQuoteForm } from "@/app/components/NewQuoteForm";

export const dynamic = "force-dynamic";

export default async function NewQuotePage({
  searchParams,
}: {
  searchParams?: { customer?: string };
}) {
  const customers = (await apiGet<CustomerSummary[]>("/customers?limit=200")) ?? [];
  const countries = (await apiGet<CountryOption[]>("/tariff/countries")) ?? [];

  // Cliente preseleccionado (viene desde la ficha del cliente).
  const preCustomerId = searchParams?.customer;
  let preCustomer = preCustomerId ? customers.find((c) => c.id === preCustomerId) : undefined;
  if (preCustomerId && !preCustomer) {
    // Puede no estar entre los primeros 200: lo traemos por id y lo añadimos.
    const c = await apiGet<CustomerSummary>(`/customers/${preCustomerId}`);
    if (c) {
      preCustomer = c;
      customers.unshift(c);
    }
  }

  return (
    <>
      <div className="eyebrow" style={{ marginBottom: 10 }}>
        <Link href={preCustomer ? `/customers/${preCustomer.id}` : "/quotes"} style={{ color: "var(--accent)" }}>
          ← {preCustomer ? "Volver al cliente" : "Cotizaciones"}
        </Link>
      </div>
      <div className="topbar">
        <div>
          <div className="eyebrow">Comercial</div>
          <h1>Nueva cotización</h1>
          {preCustomer ? (
            <div className="meta" style={{ color: "var(--muted)", marginTop: 6, fontSize: 13 }}>
              Cliente: <strong>{preCustomer.legal_name}</strong> · <span className="mono">{preCustomer.ruc}</span>
            </div>
          ) : null}
        </div>
      </div>
      <div className="card card-pad rise">
        <NewQuoteForm customers={customers} countries={countries} defaultCustomerId={preCustomer?.id} />
      </div>
    </>
  );
}
