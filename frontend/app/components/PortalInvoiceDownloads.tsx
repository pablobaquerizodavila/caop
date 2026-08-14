"use client";

import { useState } from "react";

import { getPortalInvoiceRide, getPortalInvoiceXml } from "@/app/lib/actions";

function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function PortalInvoiceDownloads({ caseId, accessKey }: { caseId: string; accessKey: string }) {
  const [busy, setBusy] = useState(false);

  async function ride() {
    setBusy(true);
    try {
      const b64 = await getPortalInvoiceRide(caseId);
      if (!b64) return alert("No se pudo generar el RIDE");
      const bin = atob(b64);
      const arr = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
      saveBlob(new Blob([arr], { type: "application/pdf" }), `RIDE-${accessKey}.pdf`);
    } finally {
      setBusy(false);
    }
  }

  async function xml() {
    setBusy(true);
    try {
      const txt = await getPortalInvoiceXml(caseId);
      if (!txt) return alert("No se pudo obtener el XML");
      saveBlob(new Blob([txt], { type: "application/xml" }), `${accessKey}.xml`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ display: "flex", gap: 10, marginTop: 10 }}>
      <button className="btn" disabled={busy} onClick={ride}>Descargar factura (PDF)</button>
      <button className="btn ghost" disabled={busy} onClick={xml}>XML</button>
    </div>
  );
}
