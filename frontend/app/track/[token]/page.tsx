import { TrackDetail, fmtDateTime } from "@/app/components/TrackDetail";
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

  return (
    <div className="trk-wrap">
      <header className="trk-header">
        <div className="trk-mark">C</div>
        <div>
          <div className="brand-name">CAOP</div>
          <div className="brand-sub">Seguimiento de importación</div>
        </div>
      </header>

      <TrackDetail v={v} />

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
