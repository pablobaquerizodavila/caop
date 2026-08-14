"use client";

import { useState } from "react";

import { exportCsv } from "@/app/lib/actions";

export function ExportCsvButton({
  path,
  filename,
  label = "Exportar CSV",
}: {
  path: string;
  filename: string;
  label?: string;
}) {
  const [busy, setBusy] = useState(false);

  async function download() {
    setBusy(true);
    try {
      const csv = await exportCsv(path);
      if (csv === null) {
        alert("No se pudo exportar");
        return;
      }
      const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setBusy(false);
    }
  }

  return (
    <button className="btn ghost" disabled={busy} onClick={download}>
      {busy ? "Exportando…" : label}
    </button>
  );
}
