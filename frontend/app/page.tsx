import Link from "next/link";
import { cookies } from "next/headers";

export const dynamic = "force-dynamic";

const YEAR = new Date().getFullYear();

const SERVICES = [
  {
    t: "Clasificación arancelaria",
    d: "Subpartida correcta contra el Arancel del Ecuador vigente, con Ad-Valorem, FODINFA, IVA, ICE y preferencias — trazable y con versión.",
    k: "HS",
  },
  {
    t: "Despacho de importación",
    d: "Gestión integral del expediente ante SENAE / ECUAPASS: DAI, aforo, liquidación y control previo (VUE), de principio a fin.",
    k: "SENAE",
  },
  {
    t: "Cotización y landed cost",
    d: "Cotizamos tributos, flete, seguro y honorarios; conoces el costo puesto en bodega antes de embarcar, sin sorpresas.",
    k: "CIF",
  },
  {
    t: "Seguimiento en tiempo real",
    d: "Cada carga con estado y documentos al día. Alertas de demurrage, almacenaje, SLA y vencimiento de documentos.",
    k: "TRACK",
  },
];

const STEPS = [
  ["01", "Cotiza", "Subes la proforma (o la lees por OCR) y calculamos tributos y landed cost al instante."],
  ["02", "Despacha", "Convertimos la cotización en expediente y gestionamos el despacho ante aduana."],
  ["03", "Monitorea", "Sigues el estado, los documentos y los costos en tiempo real hasta la nacionalización."],
];

export default function Landing() {
  const authed = Boolean(cookies().get("access_token")?.value);
  const primaryHref = authed ? "/panel" : "/login";
  const primaryLabel = authed ? "Ir al panel" : "Ingresar";

  return (
    <div className="pt-landing">
      <style dangerouslySetInnerHTML={{ __html: CSS }} />

      <header className="pt-nav">
        <div className="pt-wrap pt-nav-inner">
          <Link href="/" className="pt-brand">
            <span className="pt-logo">PT</span>
            <span className="pt-brand-txt">
              panamtrack <span className="pt-brand-sub">· Panamerican Tracking Dispatch</span>
            </span>
          </Link>
          <nav className="pt-nav-links">
            <a href="#servicios">Servicios</a>
            <a href="#como">Cómo funciona</a>
            <Link href={primaryHref} className="pt-btn pt-btn-primary">{primaryLabel}</Link>
          </nav>
        </div>
      </header>

      <section className="pt-hero">
        <div className="pt-wrap pt-hero-inner">
          <div className="pt-eyebrow">Agencia de aduanas · Ecuador</div>
          <h1>
            Despachos aduaneros, <span className="pt-accent">claros y a tiempo.</span>
          </h1>
          <p className="pt-lede">
            Panamerican Tracking Dispatch nacionaliza tu carga ante SENAE / ECUAPASS con
            clasificación arancelaria trazable, costo puesto en bodega calculado desde el inicio y
            seguimiento en tiempo real de cada expediente.
          </p>
          <div className="pt-cta-row">
            <Link href={primaryHref} className="pt-btn pt-btn-primary pt-btn-lg">{primaryLabel}</Link>
            <a href="#servicios" className="pt-btn pt-btn-ghost pt-btn-lg">Ver servicios</a>
          </div>
          <div className="pt-trust">
            <span>Integrado con</span>
            <b>SENAE</b><b>ECUAPASS</b><b>Arancel del Ecuador</b><b>VUE</b>
          </div>
        </div>
        <div className="pt-hero-glow" aria-hidden />
      </section>

      <section id="servicios" className="pt-section">
        <div className="pt-wrap">
          <h2 className="pt-h2">Lo que hacemos</h2>
          <p className="pt-sub">Del arancel a la nacionalización, en una sola operación.</p>
          <div className="pt-grid">
            {SERVICES.map((s) => (
              <div key={s.t} className="pt-service">
                <span className="pt-chip">{s.k}</span>
                <h3>{s.t}</h3>
                <p>{s.d}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="como" className="pt-section pt-section-alt">
        <div className="pt-wrap">
          <h2 className="pt-h2">Cómo funciona</h2>
          <p className="pt-sub">Tres pasos, una plataforma.</p>
          <div className="pt-steps">
            {STEPS.map(([n, t, d]) => (
              <div key={n} className="pt-step">
                <div className="pt-step-n">{n}</div>
                <h3>{t}</h3>
                <p>{d}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="pt-section pt-final">
        <div className="pt-wrap pt-final-inner">
          <h2 className="pt-h2">¿Listo para despachar sin sorpresas?</h2>
          <p className="pt-sub">Accede a tu panel o escríbenos para empezar.</p>
          <div className="pt-cta-row" style={{ justifyContent: "center" }}>
            <Link href={primaryHref} className="pt-btn pt-btn-primary pt-btn-lg">{primaryLabel}</Link>
            <a href="mailto:info@panamtrack.com" className="pt-btn pt-btn-ghost pt-btn-lg">Contáctanos</a>
          </div>
        </div>
      </section>

      <footer className="pt-footer">
        <div className="pt-wrap pt-footer-inner">
          <div>
            <span className="pt-logo pt-logo-sm">PT</span>
            <span style={{ marginLeft: 10, fontWeight: 600 }}>panamtrack</span>
            <div className="pt-foot-sub">Panamerican Tracking Dispatch · Agencia de aduanas · Ecuador</div>
          </div>
          <div className="pt-foot-links">
            <a href="mailto:info@panamtrack.com">info@panamtrack.com</a>
            <Link href="/login">Ingresar</Link>
            <span className="pt-foot-copy">© {YEAR} panamtrack</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

const CSS = `
.pt-landing{background:var(--bg);color:var(--text);font-family:var(--sans);min-height:100vh}
.pt-wrap{max-width:1100px;margin:0 auto;padding:0 24px}
.pt-landing a{color:inherit;text-decoration:none}
.pt-accent{color:var(--accent)}

.pt-nav{position:sticky;top:0;z-index:20;background:rgba(10,15,22,.72);backdrop-filter:blur(10px);border-bottom:1px solid var(--border-soft)}
.pt-nav-inner{display:flex;align-items:center;justify-content:space-between;height:64px}
.pt-brand{display:flex;align-items:center;gap:12px;font-weight:600}
.pt-logo{width:34px;height:34px;border-radius:9px;display:grid;place-items:center;font-family:var(--mono);font-weight:700;color:#04201d;font-size:14px;background:radial-gradient(circle at 30% 30%,var(--accent),var(--accent-dim));box-shadow:0 0 18px var(--accent-glow)}
.pt-logo-sm{width:28px;height:28px;font-size:12px;vertical-align:middle}
.pt-brand-txt{font-size:15px}
.pt-brand-sub{color:var(--muted-2);font-weight:400;font-size:12.5px}
.pt-nav-links{display:flex;align-items:center;gap:22px;font-size:14px;color:var(--muted)}
.pt-nav-links a:hover{color:var(--text)}

.pt-btn{display:inline-flex;align-items:center;justify-content:center;border-radius:9px;font-weight:600;font-size:14px;padding:9px 16px;transition:.15s;border:1px solid transparent;cursor:pointer}
.pt-btn-primary{background:var(--accent);color:#04201d;box-shadow:0 0 22px var(--accent-glow)}
.pt-btn-primary:hover{filter:brightness(1.08)}
.pt-btn-ghost{background:transparent;border-color:var(--border);color:var(--text)}
.pt-btn-ghost:hover{border-color:var(--accent);color:var(--accent)}
.pt-btn-lg{padding:13px 24px;font-size:15px}

.pt-hero{position:relative;overflow:hidden;padding:96px 0 84px;border-bottom:1px solid var(--border-soft)}
.pt-hero-inner{position:relative;z-index:2;max-width:820px}
.pt-hero-glow{position:absolute;top:-180px;right:-120px;width:620px;height:620px;border-radius:50%;background:radial-gradient(circle,var(--accent-glow),transparent 62%);pointer-events:none;z-index:1}
.pt-eyebrow{color:var(--accent);font-family:var(--mono);font-size:12.5px;letter-spacing:.14em;text-transform:uppercase;margin-bottom:18px}
.pt-hero h1{font-size:clamp(34px,5.6vw,58px);line-height:1.05;letter-spacing:-.02em;margin:0 0 20px;text-wrap:balance}
.pt-lede{font-size:clamp(16px,2.1vw,19px);line-height:1.6;color:var(--muted);max-width:660px;margin:0 0 30px}
.pt-cta-row{display:flex;gap:12px;flex-wrap:wrap}
.pt-trust{display:flex;align-items:center;gap:16px;flex-wrap:wrap;margin-top:40px;color:var(--muted-2);font-size:12.5px}
.pt-trust b{color:var(--muted);font-family:var(--mono);font-weight:500;font-size:12.5px;padding:5px 11px;border:1px solid var(--border-soft);border-radius:7px}

.pt-section{padding:76px 0}
.pt-section-alt{background:var(--surface);border-top:1px solid var(--border-soft);border-bottom:1px solid var(--border-soft)}
.pt-h2{font-size:clamp(26px,3.4vw,36px);letter-spacing:-.02em;margin:0 0 8px;text-wrap:balance}
.pt-sub{color:var(--muted);font-size:16px;margin:0 0 40px}

.pt-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:18px}
.pt-service{background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:26px}
.pt-section-alt .pt-service{background:var(--surface-2)}
.pt-service h3{font-size:18px;margin:14px 0 8px}
.pt-service p{color:var(--muted);line-height:1.6;margin:0;font-size:14.5px}
.pt-chip{display:inline-block;font-family:var(--mono);font-size:11px;letter-spacing:.08em;color:var(--accent);background:var(--accent-glow);border:1px solid var(--accent-dim);border-radius:6px;padding:3px 9px}

.pt-steps{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}
.pt-step{padding:8px 4px}
.pt-step-n{font-family:var(--mono);font-size:26px;font-weight:700;color:var(--accent);opacity:.85}
.pt-step h3{font-size:18px;margin:12px 0 8px}
.pt-step p{color:var(--muted);line-height:1.6;margin:0;font-size:14.5px}

.pt-final{text-align:center}
.pt-final-inner{max-width:680px;margin:0 auto}

.pt-footer{border-top:1px solid var(--border-soft);padding:34px 0;color:var(--muted)}
.pt-footer-inner{display:flex;justify-content:space-between;align-items:center;gap:20px;flex-wrap:wrap}
.pt-foot-sub{color:var(--muted-2);font-size:12.5px;margin-top:6px}
.pt-foot-links{display:flex;align-items:center;gap:20px;font-size:13.5px}
.pt-foot-links a:hover{color:var(--accent)}
.pt-foot-copy{color:var(--muted-2)}

@media(max-width:760px){
  .pt-grid,.pt-steps{grid-template-columns:1fr}
  .pt-brand-sub,.pt-nav-links a[href^="#"]{display:none}
  .pt-hero{padding:64px 0 56px}
}
`;
