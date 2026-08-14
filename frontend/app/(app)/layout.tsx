import { cookies } from "next/headers";
import type { ReactNode } from "react";

import { NavLink } from "@/app/components/NavLink";

export default function AppLayout({ children }: { children: ReactNode }) {
  const user = cookies().get("caop_user")?.value;
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
          <NavLink href="/reports">Reportes</NavLink>
          <NavLink href="/vue-rules">Reglas VUE</NavLink>
        </nav>
        <div className="foot">
          {user ? (
            <div style={{ marginBottom: 12 }}>
              <div style={{ color: "var(--muted)" }}>Sesión</div>
              <div className="mono" style={{ color: "var(--text)" }}>
                {user}
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
