import type { Metadata } from "next";
import type { ReactNode } from "react";

import "./track.css";

export const metadata: Metadata = {
  title: "Seguimiento de importación — CAOP",
  description: "Siga el avance de su importación en tiempo real.",
  robots: { index: false, follow: false },
};

export default function TrackLayout({ children }: { children: ReactNode }) {
  return <div className="trk-page">{children}</div>;
}
