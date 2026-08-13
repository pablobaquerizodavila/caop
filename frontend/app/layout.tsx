import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "CAOP — Customs Autonomous Operations Platform",
  description: "Plataforma de despacho aduanero y operación logística",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="es">
      <body
        style={{
          fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, sans-serif",
          margin: 0,
          background: "#0f1720",
          color: "#e6edf3",
        }}
      >
        {children}
      </body>
    </html>
  );
}
