"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { createCustomer } from "@/app/lib/actions";

export function NewCustomerForm() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [f, setF] = useState({ ruc: "", legal_name: "", email: "", phone: "" });

  const set = (k: string, v: string) => setF((p) => ({ ...p, [k]: v }));

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const payload: Record<string, unknown> = {
      ruc: f.ruc.trim(),
      legal_name: f.legal_name.trim(),
      email: f.email.trim() || null,
    };
    if (f.phone.trim()) {
      payload.contacts = [{ name: f.legal_name.trim(), phone: f.phone.trim(), is_primary: true }];
    }
    const res = await createCustomer(payload);
    setBusy(false);
    if (res.ok) router.push("/customers");
    else setError(res.error ?? "No se pudo crear el cliente");
  }

  return (
    <form onSubmit={submit} className="stack" style={{ maxWidth: 520 }}>
      {error ? <div className="form-error">{error}</div> : null}
      <label className="field">
        <span>RUC</span>
        <input
          type="text"
          value={f.ruc}
          onChange={(e) => set("ruc", e.target.value)}
          placeholder="1712345675001"
          required
        />
      </label>
      <label className="field">
        <span>Razón social</span>
        <input
          type="text"
          value={f.legal_name}
          onChange={(e) => set("legal_name", e.target.value)}
          required
        />
      </label>
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
