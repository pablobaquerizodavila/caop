"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { resendNotification, updateNotificationTemplate } from "@/app/lib/actions";
import {
  type NotificationItem,
  type NotificationTemplate,
  notifStatusClass,
} from "@/app/lib/format";
import { useCaps } from "@/app/lib/useCaps";

function TemplateRow({ tpl }: { tpl: NotificationTemplate }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState(false);
  const [subject, setSubject] = useState(tpl.subject_template ?? "");
  const [body, setBody] = useState(tpl.body_template);

  const dirty = subject !== (tpl.subject_template ?? "") || body !== tpl.body_template;

  async function save(extra?: Record<string, unknown>) {
    setBusy(true);
    try {
      const r = await updateNotificationTemplate(tpl.id, {
        subject_template: subject || null, body_template: body, ...extra,
      });
      if (!r.ok) alert(r.error ?? "No se pudo guardar");
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ borderBottom: "1px solid var(--border-soft)", padding: "10px 18px" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <span className={`pill ${tpl.active ? "ok" : ""}`}>{tpl.active ? "activa" : "inactiva"}</span>
        <span className="mono" style={{ fontSize: 12.5 }}>{tpl.code} · {tpl.channel} · v{tpl.version}</span>
        <span style={{ flex: 1 }} />
        <button className="btn ghost" onClick={() => setOpen((o) => !o)}>{open ? "Cerrar" : "Editar"}</button>
        <button className="btn ghost" disabled={busy} onClick={() => save({ active: !tpl.active })}>
          {tpl.active ? "Desactivar" : "Activar"}
        </button>
      </div>
      {open ? (
        <div className="stack" style={{ marginTop: 10 }}>
          {tpl.channel === "EMAIL" ? (
            <label className="field">
              <span>Asunto</span>
              <input type="text" value={subject} onChange={(e) => setSubject(e.target.value)} />
            </label>
          ) : null}
          <label className="field">
            <span>Cuerpo (usa {"{{variable}}"})</span>
            <textarea rows={5} value={body} onChange={(e) => setBody(e.target.value)}
              style={{ background: "var(--surface-2)", border: "1px solid var(--border)", color: "var(--text)", borderRadius: 7, padding: 10, fontSize: 13, fontFamily: "var(--mono)" }} />
          </label>
          <div className="actions">
            <button className="btn" disabled={busy || !dirty} onClick={() => save()}>Guardar</button>
          </div>
        </div>
      ) : null}
    </div>
  );
}

export function NotificationsCenter({
  notifications,
  templates,
}: {
  notifications: NotificationItem[];
  templates: NotificationTemplate[];
}) {
  const router = useRouter();
  const { canWrite, canAdmin } = useCaps();
  const [busy, setBusy] = useState<string | null>(null);

  async function resend(id: string) {
    setBusy(id);
    try {
      const r = await resendNotification(id);
      if (!r.ok) alert(r.error ?? "No se pudo reenviar");
      router.refresh();
    } finally {
      setBusy(null);
    }
  }

  return (
    <>
      <div className="card section-gap rise">
        <div className="head">
          <h2>Notificaciones enviadas</h2>
          <span className="count">{notifications.length}</span>
        </div>
        {notifications.length === 0 ? (
          <div className="empty">Sin notificaciones.</div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="tbl">
              <thead>
                <tr>
                  <th>Fecha</th><th>Canal</th><th>Destino</th><th>Asunto / plantilla</th>
                  <th>Estado</th><th></th>
                </tr>
              </thead>
              <tbody>
                {notifications.map((n) => (
                  <tr key={n.id}>
                    <td className="mono" style={{ fontSize: 11, color: "var(--muted)" }}>
                      {new Date(n.created_at).toLocaleString("es-EC")}
                    </td>
                    <td className="mono" style={{ fontSize: 12 }}>{n.channel}</td>
                    <td className="mono" style={{ fontSize: 12 }}>{n.to_address}</td>
                    <td style={{ fontSize: 12.5 }}>
                      {n.subject ?? n.template_code ?? "—"}
                      {n.error ? <div className="tag" style={{ color: "var(--crit)" }}>{n.error}</div> : null}
                    </td>
                    <td><span className={`pill ${notifStatusClass(n.status)}`}>{n.status}</span></td>
                    <td>
                      {canWrite ? (
                        <button className="btn ghost" disabled={busy === n.id} onClick={() => resend(n.id)}>
                          Reenviar
                        </button>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="card rise">
        <div className="head">
          <h2>Plantillas</h2>
          <span className="count">{templates.length}</span>
        </div>
        {!canAdmin ? (
          <div className="empty">La edición de plantillas requiere rol de administración.</div>
        ) : templates.length === 0 ? (
          <div className="empty">Sin plantillas. Usa el sembrado de plantillas base.</div>
        ) : (
          templates.map((t) => <TemplateRow key={t.id} tpl={t} />)
        )}
      </div>
    </>
  );
}
