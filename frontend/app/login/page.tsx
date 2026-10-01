export const dynamic = "force-dynamic";

export default function LoginPage({
  searchParams,
}: {
  searchParams: { error?: string };
}) {
  const err = searchParams.error;
  return (
    <div className="pxl">
      <style dangerouslySetInnerHTML={{ __html: CSS }} />
      <div className="pxl-box">
        <a href="/" className="pxl-logo">PANAMTRACK</a>
        <div className="pxl-eyebrow">Panamerican Tracking Dispatch · SENAE / ECUAPASS</div>

        {err ? (
          <div className="pxl-err">No se pudo iniciar sesión ({err}). Intenta nuevamente.</div>
        ) : null}

        <a href="/api/auth/login" className="pxl-btn">Ingresar →</a>

        <p className="pxl-note">Acceso restringido al personal autorizado.</p>
        <a href="/" className="pxl-back">← Volver al inicio</a>
      </div>
    </div>
  );
}

const CSS = `
.pxl{
  --black:#000000; --white:#f0f0fa; --steel:#545457; --gun:#404040;
  --din: var(--font-din), "Barlow", ui-sans-serif, system-ui, sans-serif;
  min-height:100vh; display:grid; place-items:center; padding:2rem;
  background:var(--black); color:var(--white); font-family:var(--din);
}
.pxl-box{ width:100%; max-width:380px; text-align:center; }
.pxl-logo{ font-weight:700; font-size:22px; letter-spacing:0.14em; text-transform:uppercase; color:var(--white); text-decoration:none; display:inline-block; }
.pxl-eyebrow{ font-size:10px; font-weight:700; letter-spacing:0.10em; text-transform:uppercase; color:var(--steel); margin:14px 0 30px; }
.pxl-err{ border:1px solid var(--steel); color:var(--white); font-size:11px; letter-spacing:0.06em; padding:10px 12px; margin-bottom:20px; border-radius:4px; }
.pxl-btn{
  display:block; border:1px solid var(--white); border-radius:4px; background:transparent; color:var(--white);
  font-size:13px; font-weight:700; letter-spacing:0.10em; text-transform:uppercase; padding:14px 16px;
  text-decoration:none; transition:background .15s, color .15s;
}
.pxl-btn:hover{ background:var(--white); color:var(--black); }
.pxl-note{ color:var(--steel); font-size:10px; font-weight:700; letter-spacing:0.10em; text-transform:uppercase; margin-top:22px; }
.pxl-back{ color:var(--steel); font-size:11px; letter-spacing:0.08em; text-transform:uppercase; margin-top:14px; display:inline-block; text-decoration:none; }
.pxl-back:hover{ color:var(--white); }
`;
