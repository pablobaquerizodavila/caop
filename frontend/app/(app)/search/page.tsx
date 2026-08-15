import Link from "next/link";

import { apiGet, type SearchHit, type SearchResults } from "@/app/lib/api";

export const dynamic = "force-dynamic";

function Section({
  title,
  hits,
  href,
}: {
  title: string;
  hits: SearchHit[];
  href: (h: SearchHit) => string;
}) {
  if (hits.length === 0) return null;
  return (
    <div className="card section-gap rise">
      <div className="head">
        <h2>{title}</h2>
        <span className="count">{hits.length}</span>
      </div>
      {hits.map((h) => (
        <Link key={h.id} href={href(h)} className="chk" style={{ textDecoration: "none" }}>
          <div className="left">
            <span className="doc code">{h.label}</span>
          </div>
          <span className="tag mono">{h.sub}</span>
        </Link>
      ))}
    </div>
  );
}

export default async function SearchPage({ searchParams }: { searchParams: { q?: string } }) {
  const q = (searchParams.q ?? "").trim();
  const r = q.length >= 2 ? await apiGet<SearchResults>(`/search?q=${encodeURIComponent(q)}`) : null;
  const total = r ? r.cases.length + r.quotes.length + r.customers.length + r.suppliers.length : 0;

  return (
    <>
      <div className="topbar">
        <div>
          <div className="eyebrow">Búsqueda</div>
          <h1>Resultados{q ? ` · “${q}”` : ""}</h1>
        </div>
      </div>

      {!r ? (
        <div className="card"><div className="empty">Escribe al menos 2 caracteres para buscar.</div></div>
      ) : total === 0 ? (
        <div className="card"><div className="empty">Sin resultados para “{q}”.</div></div>
      ) : (
        <>
          <Section title="Expedientes" hits={r.cases} href={(h) => `/cases/${h.id}`} />
          <Section title="Cotizaciones" hits={r.quotes} href={() => `/quotes`} />
          <Section title="Clientes" hits={r.customers} href={(h) => `/customers/${h.id}`} />
          <Section title="Proveedores" hits={r.suppliers} href={() => `/suppliers`} />
        </>
      )}
    </>
  );
}
