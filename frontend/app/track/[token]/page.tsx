import type { TrackView } from "@/app/lib/format";

export const dynamic = "force-dynamic";

const API =
  process.env.API_INTERNAL_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://backend:8000";

// Fetch público: sin cookies ni Authorization (el token del enlace es la credencial).
async function fetchTrack(token: string): Promise<TrackView | null> {
  try {
    const res = await fetch(`${API}/api/v1/track/${encodeURIComponent(token)}`, {
      cache: "no-store",
    });
    if (!res.ok) return null;
    return (await res.json()) as TrackView;
  } catch {
    return null;
  }
}

const MESES = [
  "ene", "feb", "mar", "abr", "may", "jun",
  "jul", "ago", "sep", "oct", "nov", "dic",
];

// Fecha (solo día) sin desfase por zona horaria: parsea YYYY-MM-DD manualmente.
function fmtDay(iso: string | null): string | null {
  if (!iso) return null;
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  if (!y || !m || !d) return null;
  return `${d} ${MESES[m - 1]} ${y}`;
}

function fmtDateTime(iso: string | null): string | null {
  if (!iso) return null;
  const dt = new Date(iso);
  if (Number.isNaN(dt.getTime())) return null;
  return dt.toLocaleString("es-EC", {
    day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

function NotFound() {
  return (
    <div className="trk-wrap">
      <div className="trk-404">
        <div className="big">🔍</div>
        <h1>Seguimiento no disponible</h1>
        <p>
          El enlace no es válido o el seguimiento fue desactivado. Verifique el enlace o
          contacte a su ejecutivo de comercio exterior.
        </p>
      </div>
    </div>
  );
}

export default async function TrackPage({ params }: { params: { token: string } }) {
  const v = await fetchTrack(params.token);
  if (!v) return <NotFound />;

  const t = v.transport;

  return (
    <div className="trk-wrap">
      <header className="trk-header">
        <div className="trk-mark">C</div>
        <div>
          <div className="brand-name">CAOP</div>
          <div className="brand-sub">Seguimiento de importación</div>
        </div>
      </header>

      {/* Hero de estado */}
      <section className="trk-card trk-hero">
        <div className="ref">Expediente {v.reference}</div>
        <div className="cust">{v.customer_name}</div>
        <div className="trk-status">
          <span className={`lamp ${v.status_sem}`} />
          <span className="txt">{v.status_label}</span>
        </div>
        <div className="trk-progress">
          <div className="track">
            <div className="fill" style={{ width: `${Math.max(4, v.progress_pct)}%` }} />
          </div>
          <div className="pct">{v.progress_pct}%</div>
        </div>
        {v.next_step ? (
          <div className="trk-next">
            Siguiente paso: <strong>{v.next_step}</strong>
          </div>
        ) : null}
      </section>

      {v.attention ? (
        <div className="trk-attention">
          <span className="ic">⚠️</span>
          <span>{v.attention}</span>
        </div>
      ) : null}

      {/* Hitos */}
      <section className="trk-card">
        <h2>Avance del trámite</h2>
        <div className="trk-steps">
          {v.milestones.map((m) => {
            const when = m.at ? fmtDateTime(m.at) : null;
            return (
              <div className={`trk-step ${m.status}`} key={m.key}>
                <div className="dot">{m.status === "done" ? "✓" : ""}</div>
                <div className="lbl">{m.label}</div>
                {when || m.detail ? (
                  <div className="sub">
                    {when ? <span className="when">{when}</span> : null}
                    {when && m.detail ? " · " : null}
                    {m.detail ?? null}
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
      </section>

      {/* Transporte */}
      {t.origin || t.destination || t.carrier || t.vessel_or_flight ? (
        <section className="trk-card">
          <h2>Transporte {t.mode ? `· ${t.mode}` : ""}</h2>
          {t.origin || t.destination ? (
            <div className="trk-route">
              <div className="node">
                <div className="place">{t.origin ?? "—"}</div>
                <div className="tag">Origen</div>
              </div>
              <div className="line">
                <span className="ship">{t.mode === "Aéreo" ? "✈️" : "🚢"}</span>
              </div>
              <div className="node">
                <div className="place">{t.destination ?? "—"}</div>
                <div className="tag">Destino</div>
              </div>
            </div>
          ) : null}
          <div className="trk-grid">
            {t.carrier ? (
              <div className="trk-field">
                <div className="k">Naviera / Aerolínea</div>
                <div className="v">{t.carrier}</div>
              </div>
            ) : null}
            {t.vessel_or_flight ? (
              <div className="trk-field">
                <div className="k">{t.mode === "Aéreo" ? "Vuelo" : "Buque / Viaje"}</div>
                <div className="v mono">{t.vessel_or_flight}</div>
              </div>
            ) : null}
            {t.etd ? (
              <div className="trk-field">
                <div className="k">Salida (ETD)</div>
                <div className="v mono">{fmtDay(t.etd)}</div>
              </div>
            ) : null}
            {t.ata ? (
              <div className="trk-field">
                <div className="k">Arribo real</div>
                <div className="v mono">{fmtDay(t.ata)}</div>
              </div>
            ) : t.eta ? (
              <div className="trk-field">
                <div className="k">Arribo estimado (ETA)</div>
                <div className="v mono">{fmtDay(t.eta)}</div>
              </div>
            ) : null}
          </div>
        </section>
      ) : null}

      {/* Contenedores */}
      {v.containers.length > 0 ? (
        <section className="trk-card">
          <h2>Contenedores</h2>
          {v.containers.map((c) => (
            <div className="trk-cnt" key={c.number}>
              <div>
                <div className="num">{c.number}</div>
                <div className="st">
                  {c.status_label}
                  {c.last_free_day ? ` · último día libre ${fmtDay(c.last_free_day)}` : ""}
                </div>
              </div>
              <span className={`trk-chip ${alarmChipClass(c.alarm)}`}>{c.alarm_label}</span>
            </div>
          ))}
        </section>
      ) : null}

      <footer className="trk-foot">
        {v.last_update ? (
          <div>
            Última actualización: <span className="when">{fmtDateTime(v.last_update)}</span>
          </div>
        ) : null}
        <div>Powered by CAOP · Customs Autonomous Operations Platform</div>
      </footer>
    </div>
  );
}

function alarmChipClass(a: string): string {
  return { OK: "ok", WARN: "warn", AT_RISK: "risk", CRITICAL: "crit" }[a] ?? "ok";
}
