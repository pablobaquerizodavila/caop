import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import type { ReactNode } from "react";

import { NavLink } from "@/app/components/NavLink";
import { capsFromRoles, parseRolesCookie } from "@/app/lib/rbac";

export default function AppLayout({ children }: { children: ReactNode }) {
  const user = cookies().get("caop_user")?.value;
  const caps = capsFromRoles(parseRolesCookie(cookies().get("caop_roles")?.value));
  // Los clientes (rol CUSTOMER sin rol de staff) usan el portal, no la torre interna.
  if (caps.isCustomerOnly) redirect("/portal");
  const primaryRole = caps.roles[0] ?? "—";
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="mark">C</div>
          <div>
            <div className="name">CAOP</div>
            <div className="sub">CONTROL TOWER</div>
          </div>
        </div>
        <nav className="nav">
          <NavLink href="/">Torre de Control</NavLink>
          <NavLink href="/cases">Expedientes</NavLink>
          <NavLink href="/quotes">Cotizaciones</NavLink>
          <NavLink href="/customers">Clientes</NavLink>
          <NavLink href="/notifications">Notificaciones</NavLink>
          <NavLink href="/reports">Reportes</NavLink>
          {caps.canAdmin ? (
            <>
              <NavLink href="/vue-rules">Reglas VUE</NavLink>
              <NavLink href="/tariffs">Tarifarios</NavLink>
            </>
          ) : null}
          {caps.canAdmin || caps.roles.includes("AUDITOR") ? (
            <NavLink href="/audit">Auditoría</NavLink>
          ) : null}
        </nav>
        <div className="foot">
          {user ? (
            <div style={{ marginBottom: 12 }}>
              <div style={{ color: "var(--muted)" }}>Sesión</div>
              <div className="mono" style={{ color: "var(--text)" }}>
                {user}
              </div>
              <div className="mono" style={{ color: "var(--muted-2)", fontSize: 10 }}>
                {primaryRole}
                {caps.isViewer ? " · solo lectura" : ""}
              </div>
              <a href="/api/auth/logout" style={{ color: "var(--accent)" }}>
                Salir
              </a>
            </div>
          ) : null}
          EC · SENAE / ECUAPASS
          <br />
          América/Guayaquil
        </div>
      </aside>
      <main className="main">{children}</main>
    </div>
  );
}
