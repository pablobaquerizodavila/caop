"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { deleteQuote } from "@/app/lib/actions";

export function DeleteQuoteButton({ quoteId }: { quoteId: string }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [caseMsg, setCaseMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function run(cascade: boolean) {
    setBusy(true);
    setError(null);
    const r = await deleteQuote(quoteId, cascade);
    if (r.ok) {
      router.push("/quotes");
      router.refresh();
      return;
    }
    setBusy(false);
    if (r.status === 409) {
      setCaseMsg(r.error ?? "La cotización ya generó un expediente.");
    } else {
      setError(r.error ?? "No se pudo eliminar la cotización");
    }
  }

  if (!confirming) {
    return (
      <button className="btn ghost" style={{ color: "var(--crit, #d33)" }} onClick={() => setConfirming(true)}>
        Eliminar cotización
      </button>
    );
  }

  return (
    <div className="stack" style={{ gap: 8, maxWidth: 460 }}>
      {error ? <div className="form-error">{error}</div> : null}
      {caseMsg ? (
        <>
          <div className="blocker-banner" style={{ borderColor: "rgba(211,51,51,0.4)" }}>
            {caseMsg} Esta acción es irreversible.
          </div>
          <div className="actions" style={{ display: "flex", gap: 8 }}>
            <button className="btn" style={{ background: "var(--crit, #d33)" }} disabled={busy} onClick={() => run(true)}>
              {busy ? "Eliminando…" : "Eliminar cotización y expediente"}
            </button>
            <button className="btn ghost" disabled={busy} onClick={() => { setConfirming(false); setCaseMsg(null); }}>
              Cancelar
            </button>
          </div>
        </>
      ) : (
        <>
          <div style={{ fontSize: 13, color: "var(--muted)" }}>¿Eliminar esta cotización?</div>
          <div className="actions" style={{ display: "flex", gap: 8 }}>
            <button className="btn" style={{ background: "var(--crit, #d33)" }} disabled={busy} onClick={() => run(false)}>
              {busy ? "Eliminando…" : "Sí, eliminar"}
            </button>
            <button className="btn ghost" disabled={busy} onClick={() => setConfirming(false)}>
              Cancelar
            </button>
          </div>
        </>
      )}
    </div>
  );
}
