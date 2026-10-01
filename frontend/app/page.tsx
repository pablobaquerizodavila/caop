import Link from "next/link";
import { cookies } from "next/headers";

export const dynamic = "force-dynamic";

const YEAR = new Date().getFullYear();

const SERVICES: [string, string][] = [
  ["Clasificación arancelaria", "Subpartida correcta contra el Arancel del Ecuador vigente — Ad-Valorem, FODINFA, IVA, ICE y preferencias. Trazable, con versión, auditable."],
  ["Despacho de importación", "Gestión integral del expediente ante SENAE / ECUAPASS: DAI, aforo, liquidación y control previo VUE, de principio a fin."],
  ["Cotización y landed cost", "Tributos, flete, seguro y honorarios calculados antes de embarcar. El costo puesto en bodega, sin sorpresas."],
  ["Seguimiento en tiempo real", "Cada carga con estado y documentos al día. Alertas de demurrage, almacenaje, SLA y vencimiento de documentos."],
];

const STEPS: [string, string, string][] = [
  ["01", "Cotiza", "Subes la proforma o la lees por OCR. Tributos y landed cost al instante."],
  ["02", "Despacha", "La cotización se convierte en expediente. Gestionamos el despacho ante aduana."],
  ["03", "Monitorea", "Estado, documentos y costos en tiempo real hasta la nacionalización."],
];

export default function Landing() {
  const authed = Boolean(cookies().get("access_token")?.value);
  const primaryHref = authed ? "/panel" : "/login";
  const primaryLabel = authed ? "Ir al panel" : "Ingresar";

  return (
    <div className="px">
      <style dangerouslySetInnerHTML={{ __html: CSS }} />

      <header className="px-nav">
        <div className="px-wrap px-nav-in">
          <Link href="/" className="px-logo">PANAMTRACK</Link>
          <nav className="px-nav-links">
            <a href="#servicios">Servicios</a>
            <a href="#proceso">Proceso</a>
            <Link href={primaryHref} className="px-btn">{primaryLabel}</Link>
          </nav>
        </div>
      </header>

      <section className="px-hero">
        <video className="px-hero-vid" autoPlay muted loop playsInline preload="auto" poster="/hero-poster.jpg">
          <source src="/hero.mp4" type="video/mp4" />
        </video>
        <div className="px-hero-scrim" aria-hidden />
        <div className="px-wrap"><div className="px-hero-in">
          <div className="px-eyebrow">Agencia de aduanas · Ecuador</div>
          <h1 className="px-h1">Despachos<br />aduaneros</h1>
          <p className="px-body">
            Panamerican Tracking Dispatch nacionaliza tu carga ante SENAE / ECUAPASS con
            clasificación arancelaria trazable, costo puesto en bodega calculado desde el inicio
            y seguimiento en tiempo real de cada expediente.
          </p>
          <div className="px-cta">
            <Link href={primaryHref} className="px-btn px-btn-lg">{primaryLabel} →</Link>
            <a href="#servicios" className="px-btn px-btn-lg px-btn-2">Servicios</a>
          </div>
          <div className="px-trust">
            <span>Integrado con</span>
            <b>SENAE</b><b>ECUAPASS</b><b>Arancel</b><b>VUE</b>
          </div>
        </div></div>
      </section>

      <section id="servicios" className="px-sec px-sec-img" style={{ background: "linear-gradient(rgba(0,0,0,0.86), rgba(0,0,0,0.86)), url(/svc.jpg) center/cover no-repeat" }}>
        <div className="px-wrap">
          <div className="px-kicker">Capacidades</div>
          <h2 className="px-h2">Lo que hacemos</h2>
          <div className="px-list">
            {SERVICES.map(([t, d], i) => (
              <div key={t} className="px-item">
                <div className="px-item-n">{String(i + 1).padStart(2, "0")}</div>
                <div className="px-item-t">{t}</div>
                <p className="px-body px-item-d">{d}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="proceso" className="px-sec px-sec-img" style={{ background: "linear-gradient(rgba(0,0,0,0.84), rgba(0,0,0,0.84)), url(/proc.jpg) center/cover no-repeat" }}>
        <div className="px-wrap">
          <div className="px-kicker">Operación</div>
          <h2 className="px-h2">Cómo funciona</h2>
          <div className="px-steps">
            {STEPS.map(([n, t, d]) => (
              <div key={n} className="px-step">
                <div className="px-step-n">{n}</div>
                <div className="px-item-t">{t}</div>
                <p className="px-body px-item-d">{d}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="px-sec px-final px-sec-img" style={{ background: "linear-gradient(rgba(0,0,0,0.70), rgba(0,0,0,0.78)), url(/cta.jpg) center/cover no-repeat" }}>
        <div className="px-wrap">
          <h2 className="px-h2">Despacha sin<br />sorpresas</h2>
          <div className="px-cta">
            <Link href={primaryHref} className="px-btn px-btn-lg">{primaryLabel} →</Link>
            <a href="mailto:info@panamtrack.com" className="px-btn px-btn-lg px-btn-2">Contacto</a>
          </div>
        </div>
      </section>

      <footer className="px-foot">
        <div className="px-wrap px-foot-in">
          <span className="px-logo px-logo-sm">PANAMTRACK</span>
          <div className="px-foot-links">
            <span>Panamerican Tracking Dispatch</span>
            <a href="mailto:info@panamtrack.com">info@panamtrack.com</a>
            <Link href="/login">Ingresar</Link>
            <span>© {YEAR}</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

const CSS = `
.px{
  --black:#000000; --white:#f0f0fa; --steel:#545457; --gun:#404040;
  --din: var(--font-din), "Barlow", ui-sans-serif, system-ui, sans-serif;
  background:var(--black); color:var(--white); font-family:var(--din);
  min-height:100vh; -webkit-font-smoothing:antialiased;
}
.px *{ box-sizing:border-box; }
.px a{ color:inherit; text-decoration:none; }
.px-wrap{ max-width:1180px; margin:0 auto; padding:0 40px; }

/* NAV */
.px-nav{ position:sticky; top:0; z-index:20; background:var(--black); border-bottom:1px solid var(--gun); }
.px-nav-in{ display:flex; align-items:center; justify-content:space-between; height:62px; }
.px-logo{ font-weight:700; font-size:16px; letter-spacing:0.14em; text-transform:uppercase; }
.px-logo-sm{ font-size:13px; }
.px-nav-links{ display:flex; align-items:center; gap:30px; }
.px-nav-links a{ font-size:12px; font-weight:700; letter-spacing:0.10em; text-transform:uppercase; color:var(--white); }
.px-nav-links a[href^="#"]{ color:var(--steel); }
.px-nav-links a[href^="#"]:hover{ color:var(--white); }

/* BUTTONS — ghost outline, never filled */
.px-btn{
  display:inline-flex; align-items:center; gap:8px;
  border:1px solid var(--white); border-radius:4px; background:transparent; color:var(--white);
  font-size:12px; font-weight:700; letter-spacing:0.10em; text-transform:uppercase;
  padding:12px 20px; transition:background .15s, color .15s;
}
.px-btn:hover{ background:var(--white); color:var(--black); }
.px-btn-lg{ padding:15px 28px; font-size:13px; }
.px-btn-2{ border-color:var(--steel); color:var(--steel); }
.px-btn-2:hover{ background:transparent; border-color:var(--white); color:var(--white); }

/* HERO */
.px-hero{ position:relative; overflow:hidden; display:flex; align-items:center; min-height:calc(100vh - 62px); padding:60px 0; }
.px-hero-vid{ position:absolute; inset:0; width:100%; height:100%; object-fit:cover; z-index:0; }
.px-hero-scrim{ position:absolute; inset:0; z-index:1;
  background:linear-gradient(90deg, rgba(0,0,0,0.94) 0%, rgba(0,0,0,0.80) 38%, rgba(0,0,0,0.45) 70%, rgba(0,0,0,0.30) 100%); }
.px-hero > .px-wrap{ position:relative; z-index:2; width:100%; }
.px-hero-in{ max-width:620px; }
.px-eyebrow{ font-size:12px; font-weight:700; letter-spacing:0.10em; text-transform:uppercase; color:var(--steel); margin-bottom:30px; }
.px-h1{
  font-weight:700; font-size:clamp(44px,6.5vw,72px); line-height:1.0; letter-spacing:0.02em;
  text-transform:uppercase; margin:0 0 30px; overflow-wrap:break-word;
}
.px-body{
  font-size:13px; font-weight:400; letter-spacing:0.10em; line-height:1.7; color:var(--white);
  max-width:460px; margin:0 0 30px;
}
.px-cta{ display:flex; gap:12px; flex-wrap:wrap; }
.px-trust{ display:flex; align-items:center; gap:14px; flex-wrap:wrap; margin-top:40px; }
.px-trust span{ font-size:10px; font-weight:700; letter-spacing:0.10em; text-transform:uppercase; color:var(--steel); }
.px-trust b{ font-size:10px; font-weight:700; letter-spacing:0.10em; text-transform:uppercase; color:var(--white); padding:6px 12px; border:1px solid var(--gun); border-radius:4px; }

/* SECTIONS */
.px-sec{ padding:60px 0; border-top:1px solid var(--gun); }
.px-sec-img{ padding:100px 0; background-color:var(--black); }
.px-kicker{ font-size:10px; font-weight:700; letter-spacing:0.10em; text-transform:uppercase; color:var(--steel); margin-bottom:18px; }
.px-h2{
  font-weight:700; font-size:clamp(34px,5vw,48px); line-height:1.05; letter-spacing:0.02em;
  text-transform:uppercase; margin:0 0 60px;
}
.px-final .px-h2{ margin-bottom:30px; }

.px-list{ display:grid; grid-template-columns:1fr 1fr; gap:60px 60px; }
.px-item-n, .px-step-n{ font-size:12px; font-weight:700; letter-spacing:0.10em; color:var(--steel); margin-bottom:14px; }
.px-item-t{ font-size:16px; font-weight:700; letter-spacing:0.06em; text-transform:uppercase; margin-bottom:12px; }
.px-item-d{ margin:0; max-width:480px; }

.px-steps{ display:grid; grid-template-columns:repeat(3,1fr); gap:40px; }
.px-step-n{ font-size:28px; font-weight:700; letter-spacing:0.02em; color:var(--white); margin-bottom:16px; }

/* FOOTER */
.px-foot{ padding:40px 0; border-top:1px solid var(--gun); }
.px-foot-in{ display:flex; align-items:center; justify-content:space-between; gap:24px; flex-wrap:wrap; }
.px-foot-links{ display:flex; align-items:center; gap:24px; flex-wrap:wrap; }
.px-foot-links span, .px-foot-links a{ font-size:11px; font-weight:400; letter-spacing:0.10em; text-transform:uppercase; color:var(--steel); }
.px-foot-links a:hover{ color:var(--white); }

@media(max-width:820px){
  .px-wrap{ padding:0 24px; }
  .px-list{ grid-template-columns:1fr; gap:40px; }
  .px-steps{ grid-template-columns:1fr; gap:40px; }
  .px-nav-links a[href^="#"]{ display:none; }
}
`;
