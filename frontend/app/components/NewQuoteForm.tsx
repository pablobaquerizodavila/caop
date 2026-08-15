"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { createQuote, extractPreview, updateQuote, type PreviewField } from "@/app/lib/actions";
import type { PreviewLineItem } from "@/app/lib/actions";
import { SubpartidaInput } from "@/app/components/SubpartidaInput";
import type { CustomerSummary } from "@/app/lib/format";

interface Item {
  description: string;
  model: string;
  hs_code: string;
  quantity: string;
  unit_price: string;
}
interface Cost {
  category: string;
  description: string;
  estimated_amount: string;
}

export interface QuoteInitial {
  header: {
    customer_id: string;
    transport_mode: string;
    incoterm: string;
    origin_country: string;
    currency: string;
    total_freight: string;
    total_insurance: string;
  };
  items: Item[];
  costs: Cost[];
}

const CATEGORIES = ["FEE", "FREIGHT", "INSURANCE", "PORT", "HANDLING", "TRANSPORT", "OTHER"];

export function NewQuoteForm({
  customers,
  initial,
  quoteId,
}: {
  customers: CustomerSummary[];
  initial?: QuoteInitial;
  quoteId?: string;
}) {
  const router = useRouter();
  const isEdit = Boolean(quoteId);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ocrBusy, setOcrBusy] = useState(false);
  const [ocrMsg, setOcrMsg] = useState<string | null>(null);

  const [h, setH] = useState(
    initial?.header ?? {
      customer_id: "",
      transport_mode: "OCEAN",
      incoterm: "FOB",
      origin_country: "",
      currency: "USD",
      total_freight: "",
      total_insurance: "",
    },
  );
  const [items, setItems] = useState<Item[]>(
    initial?.items?.length ? initial.items : [{ description: "", model: "", hs_code: "", quantity: "1", unit_price: "0" }],
  );
  const [costs, setCosts] = useState<Cost[]>(
    initial?.costs?.length ? initial.costs : [{ category: "FEE", description: "Honorarios de despacho", estimated_amount: "0" }],
  );

  const setHeader = (k: string, v: string) => setH((p) => ({ ...p, [k]: v }));

  async function importFromProforma(file: File) {
    setOcrBusy(true);
    setOcrMsg(null);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const r = await extractPreview(fd);
      if (!r.ok || !r.fields) {
        setOcrMsg("No se pudo leer la proforma. Ingresa los datos manualmente.");
        return;
      }
      const map: Record<string, PreviewField> = Object.fromEntries(
        r.fields.map((f) => [f.field_name, f]),
      );
      const applied: string[] = [];
      const inco = map.incoterm?.value;
      if (inco) {
        setHeader("incoterm", inco);
        applied.push(`incoterm ${inco}`);
      }
      const cur = map.currency?.value;
      if (cur) {
        setHeader("currency", cur);
        applied.push(`moneda ${cur}`);
      }

      // Ítems leídos línea por línea (lo mejor: reemplazan la lista para revisión).
      const li: PreviewLineItem[] = (r.line_items ?? []).filter(
        (x) => x.description || x.model || x.quantity || x.unit_price,
      );
      if (li.length) {
        setItems(
          li.map((x) => ({
            description: x.description ?? "",
            model: x.model ?? "",
            hs_code: x.hs_code ?? "",
            quantity: x.quantity ?? "1",
            unit_price: x.unit_price ?? "0",
          })),
        );
        const low = li.filter((x) => x.confidence < 0.5).length;
        applied.push(
          `${li.length} ítem(s)` + (low ? ` (${low} de baja confianza)` : ""),
        );
      } else {
        // Sin ítems reconocidos: al menos usa el total en el ítem 1.
        const total = map.total_amount?.value;
        if (total) {
          setItems((p) =>
            p.map((it, idx) =>
              idx === 0 && (!it.unit_price || it.unit_price === "0")
                ? { ...it, unit_price: total }
                : it,
            ),
          );
          applied.push(`monto → ítem 1 (${total})`);
        }
      }

      setOcrMsg(
        applied.length
          ? `Prellenado desde proforma: ${applied.join(", ")}. Revisa antes de crear.`
          : "No se reconocieron campos con confianza. Ingresa los datos manualmente.",
      );
    } finally {
      setOcrBusy(false);
    }
  }

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
        model: it.model || null,
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
    const res = isEdit ? await updateQuote(quoteId!, payload) : await createQuote(payload);
    setBusy(false);
    if (res.ok) {
      router.push(isEdit ? `/quotes/${quoteId}` : "/quotes");
      router.refresh();
    } else {
      setError(res.error ?? (isEdit ? "No se pudo guardar la cotización" : "No se pudo crear la cotización"));
    }
  }

  return (
    <form onSubmit={submit} className="stack">
      {error ? <div className="form-error">{error}</div> : null}

      <div className="field">
        <span>Importar desde proforma / factura (OCR)</span>
        <div className="actions">
          <input
            type="file"
            accept=".pdf,.png,.jpg,.jpeg,.tif,.tiff,.txt,image/*,application/pdf"
            disabled={ocrBusy}
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) importFromProforma(f);
            }}
          />
          {ocrBusy ? <span className="tag">Leyendo documento…</span> : null}
        </div>
        {ocrMsg ? (
          <div className="tag" style={{ color: "var(--muted)", marginTop: 4 }}>
            {ocrMsg}
          </div>
        ) : null}
      </div>

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
          <span>Moneda</span>
          <input type="text" value={h.currency} onChange={(e) => setHeader("currency", e.target.value)} placeholder="USD" />
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
        <button type="button" className="btn ghost" onClick={() => setItems((p) => [...p, { description: "", model: "", hs_code: "", quantity: "1", unit_price: "0" }])}>
          + Ítem
        </button>
      </div>
      <div className="grid-items items-head" style={{ fontSize: 12, color: "var(--muted)", fontWeight: 600 }} aria-hidden>
        <span>Modelo</span>
        <span>Descripción</span>
        <span>Subpartida</span>
        <span>Cantidad</span>
        <span>Precio unitario</span>
        <span></span>
      </div>
      {items.map((it, i) => (
        <div className="grid-items" key={i}>
          <input type="text" placeholder="Modelo" value={it.model} onChange={(e) => setItem(i, "model", e.target.value)} />
          <input type="text" placeholder="Descripción" value={it.description} onChange={(e) => setItem(i, "description", e.target.value)} />
          <SubpartidaInput
            value={it.hs_code}
            onChange={(v) => setItem(i, "hs_code", v)}
            onPick={(s) => {
              setItems((p) =>
                p.map((row, idx) =>
                  idx === i
                    ? { ...row, hs_code: s.code, description: row.description || s.description }
                    : row,
                ),
              );
            }}
          />
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
          {busy ? "Calculando…" : isEdit ? "Guardar cambios" : "Crear cotización"}
        </button>
      </div>
    </form>
  );
}
