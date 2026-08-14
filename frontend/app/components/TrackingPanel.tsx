"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { rotateTracking, sendTracking, toggleTracking } from "@/app/lib/actions";
import type { TrackingLink } from "@/app/lib/format";

export function TrackingPanel({ caseId, link }: { caseId: string; link: TrackingLink | null }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [url, setUrl] = useState(link?.url ?? "");
  const [enabled, setEnabled] = useState(link?.enabled ?? true);
  const [copied, setCopied] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  async function copy() {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      setMsg("No se pudo copiar; seleccione el enlace manualmente.");
    }
  }

  async function send(channel: string) {
    setBusy(true);
    setMsg(null);
    try {
      const r = await sendTracking(caseId, channel);
      if (r.ok) setMsg(`Enviado a ${r.to} (${r.status}).`);
      else setMsg(r.error ?? "No se pudo enviar.");
    } finally {
      setBusy(false);
    }
  }

  async function rotate() {
    if (!confirm("Al regenerar, el enlace anterior dejará de funcionar. ¿Continuar?")) return;
    setBusy(true);
    setMsg(null);
    try {
      const r = await rotateTracking(caseId);
      if (r.ok && r.url) {
        setUrl(r.url);
        setMsg("Enlace regenerado.");
      } else setMsg(r.error ?? "No se pudo regenerar.");
    } finally {
      setBusy(false);
    }
  }

  async function toggle() {
    setBusy(true);
    setMsg(null);
    try {
      const r = await toggleTracking(caseId, !enabled);
      if (r.ok) {
        setEnabled(r.enabled ?? !enabled);
        setMsg(r.enabled ? "Seguimiento activado." : "Seguimiento desactivado.");
      } else setMsg(r.error ?? "No se pudo actualizar.");
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card section-gap rise">
      <div className="head">
        <h2>Seguimiento del cliente</h2>
        <span className={`pill ${enabled ? "ok" : ""}`}>{enabled ? "ACTIVO" : "INACTIVO"}</span>
      </div>
      <div className="card-pad stack">
        <div className="field">
          <span>Enlace público (Track &amp; Trace)</span>
          <div className="actions">
            <input
              type="text"
              readOnly
              value={url}
              onFocus={(e) => e.currentTarget.select()}
              style={{ flex: 1, minWidth: 220 }}
            />
            <button className="btn ghost" disabled={busy || !url} onClick={copy}>
              {copied ? "Copiado ✓" : "Copiar"}
            </button>
            {url ? (
              <a className="btn ghost" href={url} target="_blank" rel="noopener noreferrer">
                Abrir
              </a>
            ) : null}
          </div>
        </div>

        <div className="actions">
          <button className="btn" disabled={busy || !enabled} onClick={() => send("EMAIL")}>
            Enviar por email
          </button>
          <button className="btn ghost" disabled={busy || !enabled} onClick={() => send("WHATSAPP")}>
            WhatsApp
          </button>
          <button className="btn ghost" disabled={busy} onClick={toggle}>
            {enabled ? "Desactivar" : "Activar"}
          </button>
          <button className="btn ghost" disabled={busy} onClick={rotate}>
            Regenerar
          </button>
        </div>

        {msg ? (
          <div className="tag" style={{ color: "var(--muted)" }}>
            {msg}
          </div>
        ) : null}
      </div>
    </div>
  );
}
