import { cookies } from "next/headers";
import Link from "next/link";
import type { Metadata } from "next";
import type { ReactNode } from "react";

import "../track/track.css";

export const metadata: Metadata = {
  title: "Portal del cliente — CAOP",
  description: "Consulte sus importaciones, cotizaciones y liquidaciones.",
};

export default function PortalLayout({ children }: { children: ReactNode }) {
  const user = cookies().get("caop_user")?.value ?? "cliente";
  return (
    <div className="trk-page">
      <div className="trk-wrap" style={{ maxWidth: 860 }}>
        <header className="trk-header">
          <div className="trk-mark">C</div>
          <div>
            <div className="brand-name">CAOP</div>
            <div className="brand-sub">Portal del cliente</div>
          </div>
        </header>

        <nav className="trk-nav">
          <Link href="/portal">Inicio</Link>
          <Link href="/portal/quotes">Cotizaciones</Link>
          <span className="spacer" />
          <span className="who">{user}</span>
          <a className="out" href="/api/auth/logout">Salir</a>
        </nav>

        {children}
      </div>
    </div>
  );
}
