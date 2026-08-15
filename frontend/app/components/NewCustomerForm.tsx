"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { createCustomer, uploadCustomerDocument } from "@/app/lib/actions";
import { EC_PROVINCES, capitalOf, citiesOf } from "@/app/lib/ecuador";

/** Deduce el tipo de contribuyente por el 3.º dígito del RUC ecuatoriano:
 *  0-5 = persona natural, 6 = sector público, 9 = sociedad privada. */
function guessEntityType(ruc: string): "NATURAL" | "COMPANY" {
  const d = ruc.trim()[2];
  return d === "9" || d === "6" ? "COMPANY" : "NATURAL";
}

const DOC_ACCEPT = ".pdf,.png,.jpg,.jpeg,application/pdf,image/*";

export function NewCustomerForm() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [entityTouched, setEntityTouched] = useState(false);
  const [f, setF] = useState({
    ruc: "",
    legal_name: "",
    trade_name: "",
    entity_type: "NATURAL" as "NATURAL" | "COMPANY",
    country: "Ecuador",
    province: "",
    city: "",
    address: "",
    legal_rep_name: "",
    legal_rep_id: "",
    email: "",
    phone: "",
  });
  const rucFileRef = useRef<HTMLInputElement>(null);
  const nombramientoFileRef = useRef<HTMLInputElement>(null);

  const set = (k: string, v: string) => setF((p) => ({ ...p, [k]: v }));

  // Autodetecta natural/empresa desde el RUC mientras no lo cambien a mano.
  function onRucChange(v: string) {
    setF((p) => ({
      ...p,
      ruc: v,
      entity_type: entityTouched ? p.entity_type : guessEntityType(v),
    }));
  }

  const isCompany = f.entity_type === "COMPANY";

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);

    if (isCompany && !f.legal_rep_name.trim()) {
      setError("Una empresa requiere el nombre del representante legal.");
      setBusy(false);
      return;
    }

    const payload: Record<string, unknown> = {
      ruc: f.ruc.trim(),
      legal_name: f.legal_name.trim(),
      trade_name: f.trade_name.trim() || null,
      entity_type: f.entity_type,
      country: f.country.trim() || "Ecuador",
      province: f.province.trim() || null,
      city: f.city.trim() || null,
      address: f.address.trim() || null,
      email: f.email.trim() || null,
    };
    if (isCompany) {
      payload.legal_rep_name = f.legal_rep_name.trim();
      payload.legal_rep_id = f.legal_rep_id.trim() || null;
    }
    if (f.phone.trim()) {
      payload.contacts = [{ name: f.legal_name.trim(), phone: f.phone.trim(), is_primary: true }];
    }

    const res = await createCustomer(payload);
    if (!res.ok || !res.id) {
      setBusy(false);
      setError(res.error ?? "No se pudo crear el cliente");
      return;
    }

    // Adjunta los PDFs escaneados si se seleccionaron (best-effort, con aviso si fallan).
    const warnings: string[] = [];
    const rucFile = rucFileRef.current?.files?.[0];
    if (rucFile) {
      const fd = new FormData();
      fd.append("file", rucFile, rucFile.name);
      const r = await uploadCustomerDocument(res.id, "RUC", fd);
      if (!r.ok) warnings.push("no se pudo subir el RUC escaneado");
    }
    if (isCompany) {
      const nomFile = nombramientoFileRef.current?.files?.[0];
      if (nomFile) {
        const fd = new FormData();
        fd.append("file", nomFile, nomFile.name);
        const r = await uploadCustomerDocument(res.id, "APPOINTMENT", fd);
        if (!r.ok) warnings.push("no se pudo subir el nombramiento");
      }
    }

    setBusy(false);
    if (warnings.length) {
      setError(
        `Cliente creado, pero ${warnings.join(" y ")}. Puedes subir el documento desde la ficha del cliente.`,
      );
      return;
    }
    router.push("/customers");
  }

  return (
    <form onSubmit={submit} className="stack" style={{ maxWidth: 560 }}>
      {error ? <div className="form-error">{error}</div> : null}

      <label className="field">
        <span>RUC</span>
        <input
          type="text"
          value={f.ruc}
          onChange={(e) => onRucChange(e.target.value)}
          placeholder="1712345675001"
          required
        />
      </label>

      <label className="field">
        <span>Tipo de contribuyente</span>
        <select
          value={f.entity_type}
          onChange={(e) => {
            setEntityTouched(true);
            set("entity_type", e.target.value);
          }}
        >
          <option value="NATURAL">Persona natural</option>
          <option value="COMPANY">Empresa / sociedad</option>
        </select>
      </label>

      <label className="field">
        <span>{isCompany ? "Razón social" : "Nombres y apellidos"}</span>
        <input
          type="text"
          value={f.legal_name}
          onChange={(e) => set("legal_name", e.target.value)}
          required
        />
      </label>

      <label className="field">
        <span>Nombre comercial (opcional)</span>
        <input type="text" value={f.trade_name} onChange={(e) => set("trade_name", e.target.value)} />
      </label>

      <fieldset className="stack" style={{ border: "1px solid var(--border)", borderRadius: 8, padding: 12 }}>
        <legend style={{ padding: "0 6px", color: "var(--muted)", fontSize: 12.5 }}>Dirección física</legend>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(160px,1fr))", gap: 10 }}>
          <label className="field">
            <span>País</span>
            <input type="text" value={f.country} onChange={(e) => set("country", e.target.value)} />
          </label>
          <label className="field">
            <span>Provincia</span>
            <select
              value={f.province}
              onChange={(e) => {
                const prov = e.target.value;
                // Al elegir provincia, propone su ciudad capital.
                setF((p) => ({ ...p, province: prov, city: capitalOf(prov) }));
              }}
            >
              <option value="">— Selecciona —</option>
              {EC_PROVINCES.map((p) => (
                <option key={p.province} value={p.province}>{p.province}</option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Ciudad</span>
            <select value={f.city} onChange={(e) => set("city", e.target.value)} disabled={!f.province}>
              {f.province ? (
                citiesOf(f.province).map((ci) => <option key={ci} value={ci}>{ci}</option>)
              ) : (
                <option value="">— Elige provincia primero —</option>
              )}
            </select>
          </label>
        </div>
        <label className="field">
          <span>Calle, número y referencia</span>
          <textarea
            value={f.address}
            onChange={(e) => set("address", e.target.value)}
            rows={2}
            placeholder="Av. Amazonas N34-45 y Pereira, edificio…, oficina…"
          />
        </label>
      </fieldset>

      <label className="field">
        <span>RUC escaneado (PDF)</span>
        <input ref={rucFileRef} type="file" accept={DOC_ACCEPT} />
      </label>

      {isCompany ? (
        <fieldset className="stack" style={{ border: "1px solid var(--border)", borderRadius: 8, padding: 12 }}>
          <legend style={{ padding: "0 6px", color: "var(--muted)", fontSize: 12.5 }}>
            Representante legal
          </legend>
          <label className="field">
            <span>Nombre del representante legal</span>
            <input
              type="text"
              value={f.legal_rep_name}
              onChange={(e) => set("legal_rep_name", e.target.value)}
              required={isCompany}
            />
          </label>
          <label className="field">
            <span>Cédula / RUC del representante (opcional)</span>
            <input type="text" value={f.legal_rep_id} onChange={(e) => set("legal_rep_id", e.target.value)} />
          </label>
          <label className="field">
            <span>Nombramiento legal escaneado (PDF)</span>
            <input ref={nombramientoFileRef} type="file" accept={DOC_ACCEPT} />
          </label>
        </fieldset>
      ) : null}

      <label className="field">
        <span>Email</span>
        <input type="text" value={f.email} onChange={(e) => set("email", e.target.value)} />
      </label>
      <label className="field">
        <span>Teléfono (WhatsApp)</span>
        <input type="text" value={f.phone} onChange={(e) => set("phone", e.target.value)} />
      </label>

      <div>
        <button className="btn" type="submit" disabled={busy}>
          {busy ? "Creando…" : "Crear cliente"}
        </button>
      </div>
    </form>
  );
}
