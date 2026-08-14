"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { createQuote } from "@/app/lib/actions";
import type { CustomerSummary } from "@/app/lib/format";

interface Item {
  description: string;
  hs_code: string;
  quantity: string;
  unit_price: string;
}
interface Cost {
  category: string;
  description: string;
  estimated_amount: string;
}

const CATEGORIES = ["FEE", "FREIGHT", "INSURANCE", "PORT", "HANDLING", "TRANSPORT", "OTHER"];

export function NewQuoteForm({ customers }: { customers: CustomerSummary[] }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [h, setH] = useState({
    customer_id: "",
    transport_mode: "OCEAN",
    incoterm: "FOB",
    origin_country: "",
    currency: "USD",
    total_freight: "",
    total_insurance: "",
  });
  const [items, setItems] = useState<Item[]>([
    { description: "", hs_code: "", quantity: "1", unit_price: "0" },
  ]);
  const [costs, setCosts] = useState<Cost[]>([
    { category: "FEE", description: "Honorarios de despacho", estimated_amount: "0" },
  ]);

  const setHeader = (k: string, v: string) => setH((p) => ({ ...p, [k]: v }));
  const setItem = (i: number, k: string, v: string) =>
    setItems((p) => p.map((it, idx) => (idx === i ? { ...it, [k]: v } : it)));
  const setCost = (i: number, k: string, v: string) =>
    setCosts((p) => p.map((c, idx) => (idx === i ? { ...c, [k]: v } : c)));

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const payload = {
      customer_id: h.customer_id || null,
      transport_mode: h.transport_mode,
      incoterm: h.incoterm || null,
      origin_country: h.origin_country || null,
      currency: h.currency,
      total_freight: h.total_freight || null,
      total_insurance: h.total_insurance || null,
      items: items.map((it) => ({
        description: it.description || null,
        hs_code: it.hs_code || null,
        quantity: it.quantity || "1",
        unit_price: it.unit_price || "0",
      })),
      cost_lines: costs.map((c) => ({
        category: c.category,
        description: c.description || null,
        estimated_amount: c.estimated_amount || "0",
      })),
    };
    const res = await createQuote(payload);
    setBusy(false);
    if (res.ok) router.push("/quotes");
    else setError(res.error ?? "No se pudo crear la cotización");
  }

  return (
    <form onSubmit={submit} className="stack">
      {error ? <div className="form-error">{error}</div> : null}

      <div className="grid-2">
        <label className="field">
          <span>Cliente</span>
          <select value={h.customer_id} onChange={(e) => setHeader("customer_id", e.target.value)}>
            <option value="">(sin cliente)</option>
            {customers.map((c) => (
              <option key={c.id} value={c.id}>
                {c.legal_name} — {c.ruc}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>Modalidad</span>
          <select value={h.transport_mode} onChange={(e) => setHeader("transport_mode", e.target.value)}>
            <option value="OCEAN">Marítimo</option>
            <option value="AIR">Aéreo</option>
          </select>
        </label>
        <label className="field">
          <span>Incoterm</span>
          <input type="text" value={h.incoterm} onChange={(e) => setHeader("incoterm", e.target.value)} />
        </label>
        <label className="field">
          <span>Origen (ISO-2)</span>
          <input type="text" value={h.origin_country} onChange={(e) => setHeader("origin_country", e.target.value)} placeholder="CN" />
        </label>
        <label className="field">
          <span>Flete internacional</span>
          <input type="text" value={h.total_freight} onChange={(e) => setHeader("total_freight", e.target.value)} placeholder="0" />
        </label>
        <label className="field">
          <span>Seguro</span>
          <input type="text" value={h.total_insurance} onChange={(e) => setHeader("total_insurance", e.target.value)} placeholder="0" />
        </label>
      </div>

      <div className="subhead">
        <h3>Ítems</h3>
        <button type="button" className="btn ghost" onClick={() => setItems((p) => [...p, { description: "", hs_code: "", quantity: "1", unit_price: "0" }])}>
          + Ítem
        </button>
      </div>
      {items.map((it, i) => (
        <div className="grid-items" key={i}>
          <input type="text" placeholder="Descripción" value={it.description} onChange={(e) => setItem(i, "description", e.target.value)} />
          <input type="text" placeholder="Subpartida (HS)" value={it.hs_code} onChange={(e) => setItem(i, "hs_code", e.target.value)} />
          <input type="text" placeholder="Cant." value={it.quantity} onChange={(e) => setItem(i, "quantity", e.target.value)} />
          <input type="text" placeholder="P. unit." value={it.unit_price} onChange={(e) => setItem(i, "unit_price", e.target.value)} />
          <button type="button" className="btn ghost" disabled={items.length === 1} onClick={() => setItems((p) => p.filter((_, idx) => idx !== i))}>
            ✕
          </button>
        </div>
      ))}

      <div className="subhead">
        <h3>Rubros de costo</h3>
        <button type="button" className="btn ghost" onClick={() => setCosts((p) => [...p, { category: "OTHER", description: "", estimated_amount: "0" }])}>
          + Rubro
        </button>
      </div>
      {costs.map((c, i) => (
        <div className="grid-costs" key={i}>
          <select value={c.category} onChange={(e) => setCost(i, "category", e.target.value)}>
            {CATEGORIES.map((cat) => (
              <option key={cat} value={cat}>
                {cat}
              </option>
            ))}
          </select>
          <input type="text" placeholder="Descripción" value={c.description} onChange={(e) => setCost(i, "description", e.target.value)} />
          <input type="text" placeholder="Monto" value={c.estimated_amount} onChange={(e) => setCost(i, "estimated_amount", e.target.value)} />
          <button type="button" className="btn ghost" disabled={costs.length === 1} onClick={() => setCosts((p) => p.filter((_, idx) => idx !== i))}>
            ✕
          </button>
        </div>
      ))}

      <div style={{ marginTop: 8 }}>
        <button className="btn" type="submit" disabled={busy}>
          {busy ? "Calculando…" : "Crear cotización"}
        </button>
      </div>
    </form>
  );
}
