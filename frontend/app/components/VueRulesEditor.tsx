"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import {
  createVueRule,
  deleteVueRule,
  seedVueRules,
  updateVueRule,
} from "@/app/lib/actions";
import type { VueRule } from "@/app/lib/format";

const ENTITIES = ["INEN", "ARCSA", "AGROCALIDAD", "MPCEIP", "MSP", "OTHER"];

function RuleRow({ rule }: { rule: VueRule }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [f, setF] = useState({
    hs_prefix: rule.hs_prefix,
    entity: rule.entity,
    document_code: rule.document_code,
    description: rule.description ?? "",
    blocking: rule.blocking,
    status: rule.status,
  });

  const dirty =
    f.hs_prefix !== rule.hs_prefix ||
    f.entity !== rule.entity ||
    f.document_code !== rule.document_code ||
    (f.description ?? "") !== (rule.description ?? "") ||
    f.blocking !== rule.blocking ||
    f.status !== rule.status;

  async function save() {
    setBusy(true);
    try {
      const r = await updateVueRule(rule.id, { ...f, description: f.description || null });
      if (!r.ok) alert(r.error ?? "No se pudo guardar");
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    if (!confirm(`¿Eliminar la regla ${rule.hs_prefix} → ${rule.entity}/${rule.document_code}?`)) return;
    setBusy(true);
    try {
      await deleteVueRule(rule.id);
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  return (
    <tr>
      <td>
        <input className="rule-in mono" style={{ width: 80 }} value={f.hs_prefix}
          onChange={(e) => setF((p) => ({ ...p, hs_prefix: e.target.value }))} />
      </td>
      <td>
        <select value={f.entity} onChange={(e) => setF((p) => ({ ...p, entity: e.target.value }))}>
          {ENTITIES.map((x) => <option key={x} value={x}>{x}</option>)}
        </select>
      </td>
      <td>
        <input className="rule-in mono" style={{ width: 150 }} value={f.document_code}
          onChange={(e) => setF((p) => ({ ...p, document_code: e.target.value }))} />
      </td>
      <td>
        <input className="rule-in" style={{ width: "100%", minWidth: 180 }} value={f.description}
          onChange={(e) => setF((p) => ({ ...p, description: e.target.value }))} />
      </td>
      <td style={{ textAlign: "center" }}>
        <input type="checkbox" checked={f.blocking}
          onChange={(e) => setF((p) => ({ ...p, blocking: e.target.checked }))} />
      </td>
      <td>
        <select value={f.status} onChange={(e) => setF((p) => ({ ...p, status: e.target.value }))}>
          <option value="ACTIVE">Activa</option>
          <option value="INACTIVE">Inactiva</option>
        </select>
      </td>
      <td>
        <div className="actions">
          {dirty ? (
            <button className="btn" disabled={busy} onClick={save}>Guardar</button>
          ) : null}
          <button className="btn ghost" disabled={busy} title="Eliminar" onClick={remove}>✕</button>
        </div>
      </td>
    </tr>
  );
}

export function VueRulesEditor({ rules }: { rules: VueRule[] }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [nr, setNr] = useState({
    hs_prefix: "",
    entity: "INEN",
    document_code: "",
    description: "",
    blocking: true,
  });

  async function add() {
    if (!nr.hs_prefix || !nr.document_code) return;
    setBusy(true);
    try {
      const r = await createVueRule({ ...nr, description: nr.description || null });
      if (!r.ok) alert(r.error ?? "No se pudo agregar");
      setNr({ hs_prefix: "", entity: "INEN", document_code: "", description: "", blocking: true });
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  async function seed() {
    setBusy(true);
    try {
      const r = await seedVueRules();
      if (!r.ok) alert(r.error ?? "No se pudo sembrar");
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <style>{`.rule-in{background:var(--surface-2);border:1px solid var(--border);color:var(--text);border-radius:6px;padding:6px 8px;font-size:12.5px;}`}</style>

      <div className="card rise section-gap">
        <div className="head">
          <h2>Agregar regla</h2>
          <button className="btn ghost" disabled={busy} onClick={seed}>Sembrar reglas base</button>
        </div>
        <div className="form-row" style={{ flexWrap: "wrap", alignItems: "flex-end" }}>
          <label className="field">
            <span>Prefijo HS</span>
            <input className="mono" placeholder="3304" value={nr.hs_prefix}
              onChange={(e) => setNr((p) => ({ ...p, hs_prefix: e.target.value }))} style={{ width: 90 }} />
          </label>
          <label className="field">
            <span>Entidad</span>
            <select value={nr.entity} onChange={(e) => setNr((p) => ({ ...p, entity: e.target.value }))}>
              {ENTITIES.map((x) => <option key={x} value={x}>{x}</option>)}
            </select>
          </label>
          <label className="field">
            <span>Documento</span>
            <input className="mono" placeholder="REGISTRO_SANITARIO" value={nr.document_code}
              onChange={(e) => setNr((p) => ({ ...p, document_code: e.target.value }))} style={{ width: 180 }} />
          </label>
          <label className="field" style={{ flex: 1, minWidth: 180 }}>
            <span>Descripción</span>
            <input placeholder="Descripción del control previo" value={nr.description}
              onChange={(e) => setNr((p) => ({ ...p, description: e.target.value }))} />
          </label>
          <label className="field" style={{ alignItems: "center" }}>
            <span>Bloqueante</span>
            <input type="checkbox" checked={nr.blocking}
              onChange={(e) => setNr((p) => ({ ...p, blocking: e.target.checked }))} />
          </label>
          <button className="btn" disabled={busy || !nr.hs_prefix || !nr.document_code} onClick={add}>
            Agregar
          </button>
        </div>
      </div>

      <div className="card rise">
        <div className="head">
          <h2>Reglas configuradas</h2>
          <span className="count">{rules.length}</span>
        </div>
        {rules.length === 0 ? (
          <div className="empty">
            Sin reglas. Usa &quot;Sembrar reglas base&quot; para cargar el catálogo de referencia.
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="tbl">
              <thead>
                <tr>
                  <th>Prefijo HS</th><th>Entidad</th><th>Documento</th><th>Descripción</th>
                  <th style={{ textAlign: "center" }}>Bloq.</th><th>Estado</th><th></th>
                </tr>
              </thead>
              <tbody>
                {rules.map((r) => <RuleRow key={r.id} rule={r} />)}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
