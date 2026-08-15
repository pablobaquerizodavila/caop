"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { deleteCustomer } from "@/app/lib/actions";

export function DeleteCustomerButton({ customerId }: { customerId: string }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [historyMsg, setHistoryMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function run(cascade: boolean) {
    setBusy(true);
    setError(null);
    const r = await deleteCustomer(customerId, cascade);
    if (r.ok) {
      router.push("/customers");
      router.refresh();
      return;
    }
    setBusy(false);
    if (r.status === 409) {
      // Tiene historial: pide confirmación explícita de borrado en cascada.
      setHistoryMsg(r.error ?? "El cliente tiene historial asociado.");
    } else {
      setError(r.error ?? "No se pudo eliminar el cliente");
    }
  }

  if (!confirming) {
    return (
      <button className="btn ghost" style={{ color: "var(--crit, #d33)" }} onClick={() => setConfirming(true)}>
        Eliminar cliente
      </button>
    );
  }

  return (
    <div className="stack" style={{ gap: 8, maxWidth: 460 }}>
      {error ? <div className="form-error">{error}</div> : null}
      {historyMsg ? (
        <>
          <div className="blocker-banner" style={{ borderColor: "rgba(211,51,51,0.4)" }}>
            {historyMsg} Esta acción es irreversible.
          </div>
          <div className="actions" style={{ display: "flex", gap: 8 }}>
            <button className="btn" style={{ background: "var(--crit, #d33)" }} disabled={busy} onClick={() => run(true)}>
              {busy ? "Eliminando…" : "Eliminar con todo el historial"}
            </button>
            <button className="btn ghost" disabled={busy} onClick={() => { setConfirming(false); setHistoryMsg(null); }}>
              Cancelar
            </button>
          </div>
        </>
      ) : (
        <>
          <div style={{ fontSize: 13, color: "var(--muted)" }}>
            ¿Eliminar este cliente? Si no tiene historial, se borra directamente.
          </div>
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
