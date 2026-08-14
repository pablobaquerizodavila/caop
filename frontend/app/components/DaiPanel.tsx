"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import {
  daiAdvance,
  daiPrepare,
  daiResolveObservation,
  daiSign,
  daiTransmit,
} from "@/app/lib/actions";
import type { Declaration } from "@/app/lib/format";
import { useCaps } from "@/app/lib/useCaps";

const CHIP: Record<string, string> = {
  READY_FOR_SIGNATURE: "accent",
  SIGNED: "accent",
  ACCEPTED: "ok",
  LIQUIDATED: "accent",
  PAID: "accent",
  AFORO_ASSIGNED: "warn",
  OBSERVED: "risk",
  OBSERVATION_RESOLVED: "accent",
  RELEASED: "ok",
  REJECTED: "crit",
};

const CHANNELS = ["AUTOMATICO", "DOCUMENTAL", "FISICO", "NO_INTRUSIVO"];

export function DaiPanel({
  caseId,
  readiness,
  dai,
}: {
  caseId: string;
  readiness: number;
  dai: Declaration | null;
}) {
  const router = useRouter();
  const { canWrite, canSign } = useCaps();
  const [busy, setBusy] = useState(false);
  const [scenario, setScenario] = useState("ACCEPT");
  const [channel, setChannel] = useState("AUTOMATICO");
  const [observe, setObserve] = useState(false);

  async function run(fn: () => Promise<{ ok: boolean; error?: string }>) {
    setBusy(true);
    try {
      const res = await fn();
      if (!res.ok) alert(res.error ?? "Error");
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  const st = dai?.status;

  return (
    <div className="card section-gap rise">
      <div className="head">
        <h2>DAI · SENAE {dai?.is_simulated ? "(simulado)" : ""}</h2>
        {dai ? <span className={`pill ${CHIP[st ?? ""] ?? ""}`}>{st}</span> : null}
      </div>
      <div className="card-pad">
        {!dai ? (
          readiness >= 100 ? (
            <div className="actions">
              <span className="muted" style={{ marginRight: 8 }}>
                Expediente listo.
              </span>
              {canWrite ? (
                <button className="btn" disabled={busy} onClick={() => run(() => daiPrepare(caseId))}>
                  Preparar DAI
                </button>
              ) : (
                <span className="muted">Sin permiso para preparar la DAI.</span>
              )}
            </div>
          ) : (
            <div className="muted">
              Completa el checklist (readiness 100%) para preparar la DAI.
            </div>
          )
        ) : (
          <div className="stack">
            <div className="mono" style={{ fontSize: 12.5, color: "var(--muted)" }}>
              {dai.declaration_number}
              {dai.aforo_channel ? ` · aforo ${dai.aforo_channel}` : ""}
              {dai.external_ref ? ` · ref ${dai.external_ref}` : ""}
            </div>
            {dai.error_description ? (
              <div className="form-error">{dai.error_description}</div>
            ) : null}

            <div className="actions">
              {st === "READY_FOR_SIGNATURE" ? (
                canSign ? (
                  <button className="btn" disabled={busy} onClick={() => run(() => daiSign(caseId))}>
                    Firmar (agente)
                  </button>
                ) : (
                  <span className="muted">La firma requiere rol de agente afianzado.</span>
                )
              ) : null}

              {canWrite && (st === "SIGNED" || st === "REJECTED") ? (
                <>
                  <select value={scenario} onChange={(e) => setScenario(e.target.value)}>
                    <option value="ACCEPT">Escenario: aceptar</option>
                    <option value="REJECT">Escenario: rechazar</option>
                    <option value="UNAVAILABLE">Escenario: SENAE no disponible</option>
                  </select>
                  <button className="btn" disabled={busy} onClick={() => run(() => daiTransmit(caseId, scenario))}>
                    Transmitir
                  </button>
                </>
              ) : null}

              {canWrite && st === "PAID" ? (
                <>
                  <select value={channel} onChange={(e) => setChannel(e.target.value)}>
                    {CHANNELS.map((c) => (
                      <option key={c} value={c}>
                        Aforo: {c}
                      </option>
                    ))}
                  </select>
                  <label className="muted" style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12.5 }}>
                    <input type="checkbox" checked={observe} onChange={(e) => setObserve(e.target.checked)} />
                    con observación
                  </label>
                  <button className="btn" disabled={busy} onClick={() => run(() => daiAdvance(caseId, channel, observe))}>
                    Asignar aforo
                  </button>
                </>
              ) : null}

              {canWrite && ["ACCEPTED", "LIQUIDATED", "AFORO_ASSIGNED", "OBSERVATION_RESOLVED"].includes(st ?? "") ? (
                <button className="btn" disabled={busy} onClick={() => run(() => daiAdvance(caseId))}>
                  Avanzar
                </button>
              ) : null}

              {canWrite && st === "OBSERVED" ? (
                <button className="btn" disabled={busy} onClick={() => run(() => daiResolveObservation(caseId))}>
                  Resolver observación
                </button>
              ) : null}

              {st === "RELEASED" ? <span className="pill ok">Levante autorizado ✓</span> : null}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
