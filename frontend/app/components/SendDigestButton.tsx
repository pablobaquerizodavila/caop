"use client";

import { useState } from "react";

import { sendAlertDigest } from "@/app/lib/actions";

export function SendDigestButton() {
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  async function send() {
    setBusy(true);
    setMsg(null);
    try {
      const r = await sendAlertDigest();
      if (!r.ok) setMsg(r.error ?? "No se pudo enviar");
      else if (r.note) setMsg(r.note);
      else setMsg(`Enviado a ${r.sent} destinatario(s) · ${r.total} excepción(es).`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
      {msg ? <span className="tag" style={{ color: "var(--muted)" }}>{msg}</span> : null}
      <button className="btn ghost" disabled={busy} onClick={send}>
        {busy ? "Enviando…" : "Enviar resumen"}
      </button>
    </div>
  );
}
