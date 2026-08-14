import Link from "next/link";

import { apiGet, type CaseDetail, docLabel, readiness, semaphore, stateLabel } from "@/app/lib/api";
import { Semaphore } from "@/app/components/ui";

export const dynamic = "force-dynamic";

const CHK_CLASS: Record<string, string> = {
  COMPLETE: "ok",
  MISSING: "warn",
  EXPIRED: "crit",
  INCORRECT: "crit",
  IN_REVIEW: "accent",
  NOT_APPLICABLE: "",
};

export default async function CaseDetailPage({ params }: { params: { id: string } }) {
  const c = await apiGet<CaseDetail>(`/cases/${params.id}`);

  if (!c) {
    return (
      <>
        <div className="topbar">
          <h1>Expediente</h1>
        </div>
        <div className="card">
          <div className="empty">Expediente no encontrado o backend no disponible.</div>
        </div>
      </>
    );
  }

  const r = readiness(c.customs_readiness_score);

  return (
    <>
      <div className="eyebrow" style={{ marginBottom: 10 }}>
        <Link href="/" style={{ color: "var(--accent)" }}>
          ← Torre de Control
        </Link>
      </div>

      <div className="detail-head rise">
        <div>
          <div className="num">{c.case_number}</div>
          <div className="meta">
            <span>
              <Semaphore sem={semaphore(c)} /> {stateLabel(c.current_state)}
            </span>
            <span className="mono">Régimen {c.customs_regime}</span>
            {c.next_expected_event ? (
              <span>
                Próximo: <span className="mono">{c.next_expected_event}</span>
              </span>
            ) : null}
          </div>
        </div>
        <div className="readiness-big">
          <div className="eyebrow">Customs Readiness</div>
          <div className="n" style={{ color: r >= 100 ? "var(--ok)" : "var(--accent)" }}>
            {r}%
          </div>
          <div className="bar">
            <div className="track">
              <div className="fill" style={{ width: `${Math.max(3, r)}%` }} />
            </div>
          </div>
        </div>
      </div>

      {c.blocker ? (
        <div className="blocker-banner rise">
          <Semaphore sem="risk" /> {c.blocker}
        </div>
      ) : null}

      <div className="cols">
        <div className="card rise">
          <div className="head">
            <h2>Checklist documental</h2>
            <span className="count">{c.checklist.length}</span>
          </div>
          {c.checklist.length === 0 ? (
            <div className="empty">Sin ítems de checklist.</div>
          ) : (
            c.checklist.map((it) => (
              <div className="chk" key={it.id}>
                <div className="left">
                  <span className={`pill ${CHK_CLASS[it.status] ?? ""}`}>{it.status}</span>
                  <div>
                    <div className="doc">{docLabel(it.doc_type)}</div>
                    <div className="tag">
                      {it.category}
                      {it.blocking ? " · bloqueante" : ""}
                    </div>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        <div>
          <div className="card section-gap rise">
            <div className="head">
              <h2>SLA</h2>
            </div>
            {c.sla.length === 0 ? (
              <div className="empty">Sin SLA.</div>
            ) : (
              c.sla.map((s, i) => (
                <div className="chk" key={i}>
                  <div className="left">
                    <span className="pill accent">{s.status}</span>
                    <div className="doc">{s.milestone}</div>
                  </div>
                  <div className="tag mono">
                    {s.deadline ? new Date(s.deadline).toLocaleString("es-EC") : "—"}
                  </div>
                </div>
              ))
            )}
          </div>

          <div className="card rise">
            <div className="head">
              <h2>Timeline</h2>
              <span className="count">{c.events.length}</span>
            </div>
            <div className="timeline">
              {c.events.length === 0 ? (
                <div className="empty">Sin eventos.</div>
              ) : (
                c.events.map((e, i) => (
                  <div className="tl-item" key={i}>
                    <div className="type">{e.event_type}</div>
                    <div className="ts">
                      {new Date(e.timestamp).toLocaleString("es-EC")} · {e.event_source}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
