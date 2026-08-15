"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { addConsent, addContact, deleteContact, revokeConsent } from "@/app/lib/actions";
import type { Consent, Contact } from "@/app/lib/format";
import { useCaps } from "@/app/lib/useCaps";

const LEGAL_BASIS = ["consentimiento", "contrato", "obligacion_legal", "interes_legitimo"];

export function CustomerCrmPanels({
  customerId,
  contacts,
  consents,
}: {
  customerId: string;
  contacts: Contact[];
  consents: Consent[];
}) {
  const router = useRouter();
  const { canWrite } = useCaps();
  const [busy, setBusy] = useState(false);
  const [nc, setNc] = useState({ name: "", email: "", phone: "", role: "", is_primary: false });
  const [ncon, setNcon] = useState({ purpose: "", legal_basis: "consentimiento" });

  async function act(fn: () => Promise<{ ok: boolean; error?: string }>) {
    setBusy(true);
    try {
      const r = await fn();
      if (!r.ok) alert(r.error ?? "No se pudo completar");
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  async function saveContact() {
    if (!nc.name) return;
    await act(() => addContact(customerId, {
      name: nc.name, email: nc.email || null, phone: nc.phone || null,
      role: nc.role || null, is_primary: nc.is_primary,
    }));
    setNc({ name: "", email: "", phone: "", role: "", is_primary: false });
  }

  async function saveConsent() {
    if (!ncon.purpose) return;
    await act(() => addConsent(customerId, {
      purpose: ncon.purpose, legal_basis: ncon.legal_basis,
      granted_at: new Date().toISOString(),
    }));
    setNcon({ purpose: "", legal_basis: "consentimiento" });
  }

  return (
    <div className="cols">
      <div className="card rise">
        <div className="head">
          <h2>Contactos</h2>
          <span className="count">{contacts.length}</span>
        </div>
        {contacts.length === 0 ? (
          <div className="empty">Sin contactos.</div>
        ) : (
          contacts.map((c) => (
            <div className="chk" key={c.id}>
              <div className="left">
                {c.is_primary ? <span className="pill ok">principal</span> : <span className="pill">contacto</span>}
                <div>
                  <div className="doc">{c.name}{c.role ? ` · ${c.role}` : ""}</div>
                  <div className="tag mono">{[c.email, c.phone].filter(Boolean).join(" · ") || "—"}</div>
                </div>
              </div>
              {canWrite ? (
                <button className="btn ghost" disabled={busy} onClick={() => act(() => deleteContact(customerId, c.id))}>✕</button>
              ) : null}
            </div>
          ))
        )}
        {canWrite ? (
          <div className="form-row" style={{ flexWrap: "wrap", borderTop: "1px solid var(--border-soft)" }}>
            <input type="text" placeholder="Nombre" value={nc.name} onChange={(e) => setNc((p) => ({ ...p, name: e.target.value }))} style={{ width: 150 }} />
            <input type="text" placeholder="Email" value={nc.email} onChange={(e) => setNc((p) => ({ ...p, email: e.target.value }))} style={{ width: 160 }} />
            <input type="text" placeholder="Teléfono" value={nc.phone} onChange={(e) => setNc((p) => ({ ...p, phone: e.target.value }))} style={{ width: 120 }} />
            <input type="text" placeholder="Cargo" value={nc.role} onChange={(e) => setNc((p) => ({ ...p, role: e.target.value }))} style={{ width: 110 }} />
            <label className="muted" style={{ fontSize: 12 }}>
              <input type="checkbox" checked={nc.is_primary} onChange={(e) => setNc((p) => ({ ...p, is_primary: e.target.checked }))} /> principal
            </label>
            <button className="btn" disabled={busy} onClick={saveContact}>+ Contacto</button>
          </div>
        ) : null}
      </div>

      <div className="card rise">
        <div className="head">
          <h2>Consentimiento (LOPDP)</h2>
          <span className="count">{consents.length}</span>
        </div>
        {consents.length === 0 ? (
          <div className="empty">Sin registros de consentimiento.</div>
        ) : (
          consents.map((c) => (
            <div className="chk" key={c.id}>
              <div className="left">
                <span className={`pill ${c.revoked_at ? "crit" : "ok"}`}>{c.revoked_at ? "revocado" : "vigente"}</span>
                <div>
                  <div className="doc">{c.purpose}</div>
                  <div className="tag mono">
                    {c.legal_basis}
                    {c.granted_at ? ` · otorgado ${new Date(c.granted_at).toLocaleDateString("es-EC")}` : ""}
                    {c.revoked_at ? ` · revocado ${new Date(c.revoked_at).toLocaleDateString("es-EC")}` : ""}
                  </div>
                </div>
              </div>
              {canWrite && !c.revoked_at ? (
                <button className="btn ghost" disabled={busy} onClick={() => act(() => revokeConsent(customerId, c.id))}>Revocar</button>
              ) : null}
            </div>
          ))
        )}
        {canWrite ? (
          <div className="form-row" style={{ flexWrap: "wrap", borderTop: "1px solid var(--border-soft)" }}>
            <input type="text" placeholder="Finalidad (p. ej. comunicaciones)" value={ncon.purpose} onChange={(e) => setNcon((p) => ({ ...p, purpose: e.target.value }))} style={{ flex: 1, minWidth: 180 }} />
            <select value={ncon.legal_basis} onChange={(e) => setNcon((p) => ({ ...p, legal_basis: e.target.value }))}>
              {LEGAL_BASIS.map((b) => <option key={b} value={b}>{b}</option>)}
            </select>
            <button className="btn" disabled={busy} onClick={saveConsent}>+ Consentimiento</button>
          </div>
        ) : null}
      </div>
    </div>
  );
}
