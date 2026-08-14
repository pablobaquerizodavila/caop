import type { Metadata } from "next";
import { IBM_Plex_Mono, IBM_Plex_Sans } from "next/font/google";
import type { ReactNode } from "react";

import { NavLink } from "./components/NavLink";
import "./globals.css";

const sans = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-sans",
  display: "swap",
});
const mono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "CAOP — Torre de Control",
  description: "Customs Autonomous Operations Platform",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="es" className={`${sans.variable} ${mono.variable}`}>
      <body>
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
            </nav>
            <div className="foot">
              EC · SENAE / ECUAPASS
              <br />
              América/Guayaquil
            </div>
          </aside>
          <main className="main">{children}</main>
        </div>
      </body>
    </html>
  );
}
