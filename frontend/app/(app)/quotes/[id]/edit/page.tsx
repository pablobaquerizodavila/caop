import Link from "next/link";

import { apiGet, type CustomerSummary } from "@/app/lib/api";
import { NewQuoteForm, type QuoteInitial } from "@/app/components/NewQuoteForm";

export const dynamic = "force-dynamic";

interface ItemRead {
  description?: string | null;
  hs_code?: string | null;
  quantity: number | string;
  unit_price: number | string;
  freight_alloc?: number | string | null;
  insurance_alloc?: number | string | null;
}
interface CostRead {
  category: string;
  description?: string | null;
  estimated_amount: number | string;
}
interface QuoteRead {
  id: string;
  quote_number: string;
  status: string;
  customer_id?: string | null;
  transport_mode?: string | null;
  incoterm?: string | null;
  origin_country?: string | null;
  currency: string;
  items: ItemRead[];
  cost_lines: CostRead[];
}

const num = (v: number | string | null | undefined) => (v == null ? 0 : Number(v));

export default async function EditQuotePage({ params }: { params: { id: string } }) {
  const quote = await apiGet<QuoteRead>(`/quotes/${params.id}`);
  const customers = (await apiGet<CustomerSummary[]>("/customers?limit=200")) ?? [];

  if (!quote) {
    return (
      <div className="topbar"><div><h1>Cotización no encontrada</h1>
        <Link href="/quotes" className="btn ghost">← Cotizaciones</Link></div></div>
    );
  }
  if (quote.status !== "DRAFT") {
    return (
      <>
        <div className="topbar"><div>
          <div className="eyebrow">Cotización · {quote.status}</div>
          <h1>{quote.quote_number}</h1>
        </div></div>
        <div className="card"><div className="blocker-banner">
          Solo se pueden editar cotizaciones en estado DRAFT. Esta está en {quote.status}.
        </div>
        <Link href={`/quotes/${quote.id}`} className="btn ghost" style={{ marginTop: 10 }}>← Volver</Link></div>
      </>
    );
  }

  const totalFreight = quote.items.reduce((s, it) => s + num(it.freight_alloc), 0);
  const totalInsurance = quote.items.reduce((s, it) => s + num(it.insurance_alloc), 0);

  const initial: QuoteInitial = {
    header: {
      customer_id: quote.customer_id ?? "",
      transport_mode: quote.transport_mode ?? "OCEAN",
      incoterm: quote.incoterm ?? "",
      origin_country: quote.origin_country ?? "",
      currency: quote.currency ?? "USD",
      total_freight: totalFreight ? String(totalFreight) : "",
      total_insurance: totalInsurance ? String(totalInsurance) : "",
    },
    items: quote.items.length
      ? quote.items.map((it) => ({
          description: it.description ?? "",
          hs_code: it.hs_code ?? "",
          quantity: String(num(it.quantity)),
          unit_price: String(num(it.unit_price)),
        }))
      : [{ description: "", hs_code: "", quantity: "1", unit_price: "0" }],
    costs: quote.cost_lines.length
      ? quote.cost_lines.map((c) => ({
          category: c.category,
          description: c.description ?? "",
          estimated_amount: String(num(c.estimated_amount)),
        }))
      : [{ category: "FEE", description: "Honorarios de despacho", estimated_amount: "0" }],
  };

  return (
    <>
      <div className="topbar">
        <div>
          <div className="eyebrow">Editar cotización · {quote.status}</div>
          <h1>{quote.quote_number}</h1>
        </div>
        <Link href={`/quotes/${quote.id}`} className="btn ghost">← Volver</Link>
      </div>
      <div className="card rise">
        <NewQuoteForm customers={customers} initial={initial} quoteId={quote.id} />
      </div>
    </>
  );
}
