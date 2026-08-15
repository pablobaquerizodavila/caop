"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import {
  createRolePrivilege,
  deleteRolePrivilege,
  seedRolePrivileges,
  updateRolePrivilege,
} from "@/app/lib/actions";
import type { RolePrivilege } from "@/app/lib/format";

const CAPS: { key: keyof RolePrivilege; label: string; hint: string }[] = [
  { key: "is_staff", label: "Personal", hint: "Accede a la torre interna (API operativa)" },
  { key: "can_write", label: "Escritura", hint: "Crear/editar/eliminar registros" },
  { key: "can_admin", label: "Config.", hint: "Reglas VUE, tarifarios y configuración global" },
  { key: "can_sign", label: "Firmar DAI", hint: "Firmar la declaración (agente afianzado)" },
  { key: "can_audit", label: "Auditoría", hint: "Ver la bitácora de auditoría" },
];

function MatrixRow({ r }: { r: RolePrivilege }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const locked = r.role_name === "SUPER_ADMIN";
  const [f, setF] = useState({
    description: r.description ?? "",
    is_staff: r.is_staff,
    can_write: r.can_write,
    can_admin: r.can_admin,
    can_sign: r.can_sign,
    can_audit: r.can_audit,
  });

  const dirty =
    f.description !== (r.description ?? "") ||
    CAPS.some((c) => f[c.key as "is_staff"] !== (r[c.key] as boolean));

  async function save() {
    setBusy(true);
    try {
      const res = await updateRolePrivilege(r.id, f);
      if (!res.ok) alert(res.error ?? "No se pudo guardar");
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    if (!confirm(`¿Eliminar los privilegios del rol ${r.role_name}?`)) return;
    setBusy(true);
    try {
      const res = await deleteRolePrivilege(r.id);
      if (!res.ok) alert(res.error ?? "No se pudo eliminar");
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  return (
    <tr>
      <td>
        <span className="mono" style={{ color: "var(--text)" }}>{r.role_name}</span>
        {locked ? <span className="pill accent" style={{ marginLeft: 6 }}>poder total</span> : null}
      </td>
      <td>
        <input
          className="rule-in"
          style={{ minWidth: 200 }}
          value={f.description}
          disabled={locked}
          onChange={(e) => setF((p) => ({ ...p, description: e.target.value }))}
        />
      </td>
      {CAPS.map((c) => (
        <td key={c.key as string} style={{ textAlign: "center" }} title={c.hint}>
          <input
            type="checkbox"
            checked={locked ? true : (f[c.key as "is_staff"] as boolean)}
            disabled={locked}
            onChange={(e) => setF((p) => ({ ...p, [c.key]: e.target.checked }))}
          />
        </td>
      ))}
      <td>
        {locked ? (
          <span style={{ color: "var(--muted-2)", fontSize: 11 }}>no editable</span>
        ) : (
          <div className="actions">
            {dirty ? <button className="btn" disabled={busy} onClick={save}>Guardar</button> : null}
            <button className="btn ghost" disabled={busy} title="Eliminar" onClick={remove}>✕</button>
          </div>
        )}
      </td>
    </tr>
  );
}

export function RolePrivilegeMatrix({ roles }: { roles: RolePrivilege[] }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [nr, setNr] = useState({
    role_name: "",
    description: "",
    is_staff: true,
    can_write: false,
    can_admin: false,
    can_sign: false,
    can_audit: false,
  });

  async function seed() {
    setBusy(true);
    try {
      const res = await seedRolePrivileges();
      if (!res.ok) alert(res.error ?? "No se pudo sembrar");
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  async function add() {
    const name = nr.role_name.trim().toUpperCase();
    if (!name) return;
    setBusy(true);
    try {
      const res = await createRolePrivilege({ ...nr, role_name: name });
      if (!res.ok) alert(res.error ?? "No se pudo agregar");
      else setNr((p) => ({ ...p, role_name: "", description: "" }));
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <style>{`.rule-in{background:var(--surface-2);border:1px solid var(--border);color:var(--text);border-radius:6px;padding:6px 8px;font-size:12.5px;}`}</style>

      <div className="card rise section-gap">
        <div className="head" style={{ justifyContent: "space-between" }}>
          <h2>Agregar rol</h2>
          {roles.length === 0 ? (
            <button className="btn" disabled={busy} onClick={seed}>Sembrar roles base</button>
          ) : null}
        </div>
        <div className="form-row" style={{ flexWrap: "wrap", alignItems: "flex-end" }}>
          <label className="field" style={{ minWidth: 160 }}>
            <span>Nombre del rol</span>
            <input
              placeholder="P. EJ. FINANCE"
              value={nr.role_name}
              onChange={(e) => setNr((p) => ({ ...p, role_name: e.target.value }))}
            />
          </label>
          <label className="field" style={{ flex: 1, minWidth: 200 }}>
            <span>Descripción</span>
            <input
              placeholder="Para qué sirve este rol"
              value={nr.description}
              onChange={(e) => setNr((p) => ({ ...p, description: e.target.value }))}
            />
          </label>
          {CAPS.map((c) => (
            <label
              key={c.key as string}
              className="field"
              style={{ alignItems: "center", textAlign: "center" }}
              title={c.hint}
            >
              <span>{c.label}</span>
              <input
                type="checkbox"
                checked={nr[c.key as "is_staff"] as boolean}
                onChange={(e) => setNr((p) => ({ ...p, [c.key]: e.target.checked }))}
              />
            </label>
          ))}
          <button className="btn" disabled={busy || !nr.role_name.trim()} onClick={add}>Agregar</button>
        </div>
      </div>

      <div className="card rise">
        <div className="head">
          <h2>Privilegios por rol</h2>
          <span className="count">{roles.length}</span>
        </div>
        {roles.length === 0 ? (
          <div className="empty">
            Sin roles configurados. Usa «Sembrar roles base» para partir de la matriz por defecto.
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="tbl">
              <thead>
                <tr>
                  <th>Rol</th>
                  <th>Descripción</th>
                  {CAPS.map((c) => (
                    <th key={c.key as string} style={{ textAlign: "center" }} title={c.hint}>
                      {c.label}
                    </th>
                  ))}
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {roles.map((r) => <MatrixRow key={r.id} r={r} />)}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
