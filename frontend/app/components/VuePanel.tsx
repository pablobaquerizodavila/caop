"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import {
  applyVueSuggestions,
  createVuePermit,
  deleteVuePermit,
  exemptVuePermit,
  requestVuePermit,
} from "@/app/lib/actions";
import {
  type VueCatalogEntry,
  type VuePermit,
  type VueSuggestion,
  vueStatusClass,
  vueStatusLabel,
} from "@/app/lib/format";

function PermitRow({
  caseId,
  p,
}: {
  caseId: string;
  p: VuePermit;
}) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [scenario, setScenario] = useState("APPROVE");

  const done = p.status === "APPROVED" || p.status === "EXEMPT";

  async function act(fn: () => Promise<{ ok: boolean; error?: string }>) {
    setBusy(true);
    try {
      const r = await fn();
      if (!r.ok) alert(r.error ?? "No se pudo completar la acción");
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="chk" style={{ alignItems: "flex-start" }}>
      <div className="left" style={{ alignItems: "flex-start" }}>
        <span className={`pill ${vueStatusClass(p.status)}`}>{vueStatusLabel(p.status)}</span>
        <div>
          <div className="doc">
            {p.entity} · <span className="mono">{p.document_code}</span>
            {!p.blocking ? <span className="tag"> · no bloqueante</span> : null}
          </div>
          {p.description ? <div className="tag">{p.description}</div> : null}
          {p.permit_number ? (
            <div className="tag mono">
              N.º {p.permit_number}
              {p.valid_until ? ` · vence ${p.valid_until}` : ""}
            </div>
          ) : null}
          {p.error_description ? (
            <div className="tag" style={{ color: "var(--crit)" }}>
              {p.error_description}
            </div>
          ) : null}
        </div>
      </div>
      <div className="actions" style={{ justifyContent: "flex-end" }}>
        {!done ? (
          <>
            <select value={scenario} onChange={(e) => setScenario(e.target.value)} disabled={busy}>
              <option value="APPROVE">Aprobar</option>
              <option value="PENDING">En trámite</option>
              <option value="REJECT">Rechazar</option>
              <option value="UNAVAILABLE">VUE caída</option>
            </select>
            <button
              className="btn"
              disabled={busy}
              onClick={() => act(() => requestVuePermit(caseId, p.id, scenario))}
            >
              Enviar a VUE
            </button>
            <button
              className="btn ghost"
              disabled={busy}
              onClick={() => act(() => exemptVuePermit(caseId, p.id, ""))}
            >
              Eximir
            </button>
          </>
        ) : null}
        <button
          className="btn ghost"
          disabled={busy}
          title="Eliminar"
          onClick={() => act(() => deleteVuePermit(caseId, p.id))}
        >
          ✕
        </button>
      </div>
    </div>
  );
}

export function VuePanel({
  caseId,
  permits,
  catalog,
  suggestions = [],
}: {
  caseId: string;
  permits: VuePermit[];
  catalog: VueCatalogEntry[];
  suggestions?: VueSuggestion[];
}) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [sel, setSel] = useState("");

  const pendingBlocking = permits.filter((p) => p.blocking && !p.satisfied).length;

  async function applySuggestions() {
    setBusy(true);
    try {
      const r = await applyVueSuggestions(caseId);
      if (!r.ok) alert(r.error ?? "No se pudieron agregar los sugeridos");
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  async function add() {
    if (sel === "") return;
    const entry = catalog[Number(sel)];
    if (!entry) return;
    setBusy(true);
    try {
      const r = await createVuePermit(caseId, {
        entity: entry.entity,
        document_code: entry.document_code,
        description: entry.description,
        blocking: true,
      });
      if (!r.ok) alert(r.error ?? "No se pudo agregar");
      setSel("");
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card section-gap rise">
      <div className="head">
        <h2>Control previo (VUE)</h2>
        {permits.length > 0 ? (
          <span className={`pill ${pendingBlocking > 0 ? "warn" : "ok"}`}>
            {pendingBlocking > 0 ? `${pendingBlocking} pendiente(s)` : "Al día"}
          </span>
        ) : (
          <span className="count">0</span>
        )}
      </div>

      {suggestions.length > 0 ? (
        <div className="blocker-banner" style={{ margin: "12px 18px 0", alignItems: "flex-start" }}>
          <div style={{ flex: 1 }}>
            💡 <b>{suggestions.length}</b> control(es) previo(s) sugerido(s) por subpartida:{" "}
            {suggestions.map((s) => `${s.entity}/${s.document_code}`).join(", ")}
          </div>
          <button className="btn" disabled={busy} onClick={applySuggestions}>
            Agregar sugeridos
          </button>
        </div>
      ) : null}

      <div className="form-row">
        <select value={sel} onChange={(e) => setSel(e.target.value)} style={{ flex: 1, minWidth: 200 }}>
          <option value="">Agregar documento de control previo…</option>
          {catalog.map((c, i) => (
            <option key={`${c.entity}-${c.document_code}`} value={i}>
              {c.entity} — {c.document_code} · {c.description}
            </option>
          ))}
        </select>
        <button className="btn" disabled={busy || sel === ""} onClick={add}>
          Agregar
        </button>
      </div>

      {permits.length === 0 ? (
        <div className="empty">
          Sin documentos de control previo. Agrega los que apliquen a la mercancía.
        </div>
      ) : (
        permits.map((p) => <PermitRow key={p.id} caseId={caseId} p={p} />)
      )}

      {pendingBlocking > 0 ? (
        <div className="form-row">
          <span className="tag" style={{ color: "var(--warn)" }}>
            ⚠️ La DAI no puede prepararse hasta aprobar/eximir el control previo bloqueante.
          </span>
        </div>
      ) : null}
    </div>
  );
}
