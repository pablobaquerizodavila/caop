"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { createSupplier, deleteSupplier, updateSupplier } from "@/app/lib/actions";
import type { Supplier } from "@/app/lib/format";
import { useCaps } from "@/app/lib/useCaps";

function SupplierRow({ s, canWrite }: { s: Supplier; canWrite: boolean }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [f, setF] = useState({ name: s.name, country: s.country ?? "" });
  const dirty = f.name !== s.name || f.country !== (s.country ?? "");

  async function save() {
    setBusy(true);
    try {
      await updateSupplier(s.id, { name: f.name, country: f.country || null });
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    if (!confirm(`¿Eliminar el proveedor ${s.name}?`)) return;
    setBusy(true);
    try {
      await deleteSupplier(s.id);
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  return (
    <tr>
      <td>
        {canWrite ? (
          <input className="rule-in" style={{ minWidth: 200 }} value={f.name}
            onChange={(e) => setF((p) => ({ ...p, name: e.target.value }))} />
        ) : s.name}
      </td>
      <td>
        {canWrite ? (
          <input className="rule-in mono" style={{ width: 70 }} value={f.country}
            onChange={(e) => setF((p) => ({ ...p, country: e.target.value }))} placeholder="CN" />
        ) : (s.country ?? "—")}
      </td>
      <td>
        {canWrite ? (
          <div className="actions">
            {dirty ? <button className="btn" disabled={busy} onClick={save}>Guardar</button> : null}
            <button className="btn ghost" disabled={busy} title="Eliminar" onClick={remove}>✕</button>
          </div>
        ) : null}
      </td>
    </tr>
  );
}

export function SuppliersManager({ suppliers }: { suppliers: Supplier[] }) {
  const router = useRouter();
  const { canWrite } = useCaps();
  const [busy, setBusy] = useState(false);
  const [ns, setNs] = useState({ name: "", country: "" });

  async function add() {
    if (!ns.name) return;
    setBusy(true);
    try {
      const r = await createSupplier({ name: ns.name, country: ns.country || null });
      if (!r.ok) alert(r.error ?? "No se pudo agregar");
      setNs({ name: "", country: "" });
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <style>{`.rule-in{background:var(--surface-2);border:1px solid var(--border);color:var(--text);border-radius:6px;padding:6px 8px;font-size:12.5px;}`}</style>

      {canWrite ? (
        <div className="card rise section-gap">
          <div className="head"><h2>Agregar proveedor</h2></div>
          <div className="form-row" style={{ flexWrap: "wrap", alignItems: "flex-end" }}>
            <label className="field" style={{ flex: 1, minWidth: 200 }}>
              <span>Nombre (exportador)</span>
              <input value={ns.name} onChange={(e) => setNs((p) => ({ ...p, name: e.target.value }))} />
            </label>
            <label className="field">
              <span>País (ISO-2)</span>
              <input className="mono" value={ns.country} placeholder="CN"
                onChange={(e) => setNs((p) => ({ ...p, country: e.target.value }))} style={{ width: 80 }} />
            </label>
            <button className="btn" disabled={busy || !ns.name} onClick={add}>Agregar</button>
          </div>
        </div>
      ) : null}

      <div className="card rise">
        <div className="head">
          <h2>Proveedores</h2>
          <span className="count">{suppliers.length}</span>
        </div>
        {suppliers.length === 0 ? (
          <div className="empty">Sin proveedores registrados.</div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="tbl">
              <thead><tr><th>Nombre</th><th>País</th><th></th></tr></thead>
              <tbody>
                {suppliers.map((s) => <SupplierRow key={s.id} s={s} canWrite={canWrite} />)}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
