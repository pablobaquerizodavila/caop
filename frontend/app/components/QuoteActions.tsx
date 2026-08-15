"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { generateQuotePdf, setQuoteStatus } from "@/app/lib/actions";

export function QuoteActions({ quoteId, status }: { quoteId: string; status: string }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);

  const canSend = status === "DRAFT";
  const canAccept = ["SENT", "DELIVERED", "READ"].includes(status);

  async function changeStatus(next: string) {
    setBusy(true);
    try {
      const res = await setQuoteStatus(quoteId, next);
      if (!res.ok) alert(res.error ?? "No se pudo cambiar el estado");
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  async function pdf() {
    setBusy(true);
    try {
      const url = await generateQuotePdf(quoteId);
      if (url) window.open(url, "_blank");
      else alert("No se pudo generar el PDF");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="actions">
      {status === "DRAFT" ? (
        <Link className="btn ghost" href={`/quotes/${quoteId}/edit`}>
          Editar
        </Link>
      ) : null}
      {canSend ? (
        <button className="btn" disabled={busy} onClick={() => changeStatus("SENT")}>
          Enviar
        </button>
      ) : null}
      {canAccept ? (
        <button className="btn" disabled={busy} onClick={() => changeStatus("ACCEPTED")}>
          Aceptar
        </button>
      ) : null}
      <button className="btn ghost" disabled={busy} onClick={pdf}>
        PDF
      </button>
    </div>
  );
}
