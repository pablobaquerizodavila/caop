"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import {
  createKcUser,
  deleteKcUser,
  resetKcUserPassword,
  setKcUserRoles,
  updateKcUser,
} from "@/app/lib/actions";
import type { KcUser } from "@/app/lib/format";

const PROTECTED_USER = "admin-caop"; // super administrador: no se elimina ni deshabilita.

function RoleChips({ roles }: { roles: string[] }) {
  if (roles.length === 0) return <span style={{ color: "var(--muted-2)" }}>sin roles</span>;
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
      {roles.map((r) => (
        <span key={r} className={`pill ${r === "SUPER_ADMIN" ? "accent" : ""}`}>{r}</span>
      ))}
    </div>
  );
}

function UserRow({ u, realmRoles }: { u: KcUser; realmRoles: string[] }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const isProtected = u.username === PROTECTED_USER || u.roles.includes("SUPER_ADMIN");
  const [roles, setRoles] = useState<string[]>(u.roles);
  const [profile, setProfile] = useState({
    email: u.email ?? "",
    first_name: u.first_name ?? "",
    last_name: u.last_name ?? "",
  });
  const [pw, setPw] = useState("");

  function toggleRole(r: string) {
    setRoles((prev) => (prev.includes(r) ? prev.filter((x) => x !== r) : [...prev, r]));
  }

  async function saveRoles() {
    setBusy(true);
    try {
      const res = await setKcUserRoles(u.id, roles);
      if (!res.ok) alert(res.error ?? "No se pudieron guardar los roles");
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  async function saveProfile() {
    setBusy(true);
    try {
      const res = await updateKcUser(u.id, profile);
      if (!res.ok) alert(res.error ?? "No se pudo guardar");
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  async function toggleEnabled() {
    if (isProtected) return;
    setBusy(true);
    try {
      const res = await updateKcUser(u.id, { enabled: !u.enabled });
      if (!res.ok) alert(res.error ?? "No se pudo cambiar el estado");
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  async function resetPassword() {
    if (!pw || pw.length < 6) { alert("La contraseña debe tener al menos 6 caracteres"); return; }
    setBusy(true);
    try {
      const res = await resetKcUserPassword(u.id, pw, true);
      if (!res.ok) alert(res.error ?? "No se pudo restablecer");
      else { setPw(""); alert("Contraseña temporal establecida. El usuario deberá cambiarla al ingresar."); }
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    if (isProtected) return;
    if (!confirm(`¿Eliminar al usuario ${u.username}? Esta acción no se puede deshacer.`)) return;
    setBusy(true);
    try {
      const res = await deleteKcUser(u.id);
      if (!res.ok) alert(res.error ?? "No se pudo eliminar");
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  const rolesDirty =
    roles.length !== u.roles.length || roles.some((r) => !u.roles.includes(r));
  const profileDirty =
    profile.email !== (u.email ?? "") ||
    profile.first_name !== (u.first_name ?? "") ||
    profile.last_name !== (u.last_name ?? "");

  return (
    <>
      <tr>
        <td>
          <span className="mono" style={{ color: "var(--text)" }}>{u.username}</span>
          {isProtected ? <span className="pill accent" style={{ marginLeft: 6 }}>super</span> : null}
        </td>
        <td style={{ color: "var(--muted)" }}>
          {[u.first_name, u.last_name].filter(Boolean).join(" ") || "—"}
          <div style={{ fontSize: 11, color: "var(--muted-2)" }}>{u.email ?? "—"}</div>
        </td>
        <td><RoleChips roles={u.roles} /></td>
        <td style={{ textAlign: "center" }}>
          <span className={`pill ${u.enabled ? "ok" : "warn"}`}>{u.enabled ? "activo" : "inactivo"}</span>
        </td>
        <td>
          <button className="btn ghost" onClick={() => setOpen((v) => !v)}>
            {open ? "Cerrar" : "Gestionar"}
          </button>
        </td>
      </tr>
      {open ? (
        <tr>
          <td colSpan={5} style={{ background: "var(--surface-2)" }}>
            <div style={{ display: "grid", gap: 16, padding: "12px 4px" }}>
              {/* Roles */}
              <div>
                <div className="eyebrow" style={{ marginBottom: 6 }}>Roles</div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
                  {realmRoles.map((r) => (
                    <label key={r} style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 12.5 }}>
                      <input type="checkbox" checked={roles.includes(r)} onChange={() => toggleRole(r)} />
                      <span className="mono">{r}</span>
                    </label>
                  ))}
                </div>
                {rolesDirty ? (
                  <button className="btn" style={{ marginTop: 8 }} disabled={busy} onClick={saveRoles}>
                    Guardar roles
                  </button>
                ) : null}
              </div>

              {/* Perfil */}
              <div>
                <div className="eyebrow" style={{ marginBottom: 6 }}>Datos</div>
                <div className="form-row" style={{ flexWrap: "wrap", alignItems: "flex-end" }}>
                  <label className="field" style={{ minWidth: 200 }}>
                    <span>Email</span>
                    <input value={profile.email}
                      onChange={(e) => setProfile((p) => ({ ...p, email: e.target.value }))} />
                  </label>
                  <label className="field" style={{ minWidth: 140 }}>
                    <span>Nombre</span>
                    <input value={profile.first_name}
                      onChange={(e) => setProfile((p) => ({ ...p, first_name: e.target.value }))} />
                  </label>
                  <label className="field" style={{ minWidth: 140 }}>
                    <span>Apellido</span>
                    <input value={profile.last_name}
                      onChange={(e) => setProfile((p) => ({ ...p, last_name: e.target.value }))} />
                  </label>
                  {profileDirty ? (
                    <button className="btn" disabled={busy} onClick={saveProfile}>Guardar datos</button>
                  ) : null}
                </div>
              </div>

              {/* Contraseña + estado + eliminar */}
              <div className="form-row" style={{ flexWrap: "wrap", alignItems: "flex-end" }}>
                <label className="field" style={{ minWidth: 200 }}>
                  <span>Nueva contraseña temporal</span>
                  <input type="password" value={pw} placeholder="mín. 6 caracteres"
                    onChange={(e) => setPw(e.target.value)} />
                </label>
                <button className="btn ghost" disabled={busy || !pw} onClick={resetPassword}>
                  Restablecer contraseña
                </button>
                {!isProtected ? (
                  <>
                    <button className="btn ghost" disabled={busy} onClick={toggleEnabled}>
                      {u.enabled ? "Deshabilitar" : "Habilitar"}
                    </button>
                    <button className="btn ghost" disabled={busy} onClick={remove}
                      style={{ color: "var(--danger, #f87171)", borderColor: "var(--danger, #f87171)" }}>
                      Eliminar usuario
                    </button>
                  </>
                ) : (
                  <span style={{ color: "var(--muted-2)", fontSize: 11, alignSelf: "center" }}>
                    El super administrador no se puede deshabilitar ni eliminar.
                  </span>
                )}
              </div>
            </div>
          </td>
        </tr>
      ) : null}
    </>
  );
}

export function UsersManager({ users, realmRoles }: { users: KcUser[]; realmRoles: string[] }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [nu, setNu] = useState({
    username: "",
    email: "",
    first_name: "",
    last_name: "",
    password: "",
    roles: [] as string[],
  });

  function toggleNewRole(r: string) {
    setNu((p) => ({
      ...p,
      roles: p.roles.includes(r) ? p.roles.filter((x) => x !== r) : [...p.roles, r],
    }));
  }

  async function add() {
    if (!nu.username.trim() || nu.password.length < 6) {
      alert("Usuario y contraseña (mín. 6) son obligatorios");
      return;
    }
    setBusy(true);
    try {
      const res = await createKcUser({
        username: nu.username.trim(),
        email: nu.email || null,
        first_name: nu.first_name || null,
        last_name: nu.last_name || null,
        password: nu.password,
        temporary: true,
        roles: nu.roles,
      });
      if (!res.ok) alert(res.error ?? "No se pudo crear el usuario");
      else {
        setNu({ username: "", email: "", first_name: "", last_name: "", password: "", roles: [] });
        alert("Usuario creado. La contraseña es temporal: deberá cambiarla al primer ingreso.");
      }
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div className="card rise section-gap">
        <div className="head"><h2>Nuevo usuario</h2></div>
        <div className="form-row" style={{ flexWrap: "wrap", alignItems: "flex-end" }}>
          <label className="field" style={{ minWidth: 150 }}>
            <span>Usuario *</span>
            <input value={nu.username} placeholder="p. ej. jperez"
              onChange={(e) => setNu((p) => ({ ...p, username: e.target.value }))} />
          </label>
          <label className="field" style={{ minWidth: 200 }}>
            <span>Email</span>
            <input value={nu.email} onChange={(e) => setNu((p) => ({ ...p, email: e.target.value }))} />
          </label>
          <label className="field" style={{ minWidth: 130 }}>
            <span>Nombre</span>
            <input value={nu.first_name} onChange={(e) => setNu((p) => ({ ...p, first_name: e.target.value }))} />
          </label>
          <label className="field" style={{ minWidth: 130 }}>
            <span>Apellido</span>
            <input value={nu.last_name} onChange={(e) => setNu((p) => ({ ...p, last_name: e.target.value }))} />
          </label>
          <label className="field" style={{ minWidth: 160 }}>
            <span>Contraseña temporal *</span>
            <input type="password" value={nu.password} placeholder="mín. 6 caracteres"
              onChange={(e) => setNu((p) => ({ ...p, password: e.target.value }))} />
          </label>
        </div>
        <div style={{ marginTop: 12 }}>
          <div className="eyebrow" style={{ marginBottom: 6 }}>Roles</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
            {realmRoles.map((r) => (
              <label key={r} style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 12.5 }}>
                <input type="checkbox" checked={nu.roles.includes(r)} onChange={() => toggleNewRole(r)} />
                <span className="mono">{r}</span>
              </label>
            ))}
          </div>
        </div>
        <div style={{ marginTop: 12 }}>
          <button className="btn" disabled={busy || !nu.username.trim() || nu.password.length < 6} onClick={add}>
            Crear usuario
          </button>
        </div>
      </div>

      <div className="card rise">
        <div className="head">
          <h2>Usuarios</h2>
          <span className="count">{users.length}</span>
        </div>
        {users.length === 0 ? (
          <div className="empty">
            No se pudieron cargar los usuarios (¿Keycloak disponible?) o aún no hay ninguno.
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="tbl">
              <thead>
                <tr>
                  <th>Usuario</th><th>Nombre / Email</th><th>Roles</th>
                  <th style={{ textAlign: "center" }}>Estado</th><th></th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => <UserRow key={u.id} u={u} realmRoles={realmRoles} />)}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
