export const dynamic = "force-dynamic";

export default function LoginPage({
  searchParams,
}: {
  searchParams: { error?: string };
}) {
  const err = searchParams.error;
  return (
    <div
      style={{
        minHeight: "100vh",
        display: "grid",
        placeItems: "center",
        padding: "2rem",
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: 380,
          textAlign: "center",
          background: "var(--surface)",
          border: "1px solid var(--border-soft)",
          borderRadius: "var(--radius)",
          padding: "38px 32px",
          boxShadow: "var(--shadow)",
        }}
      >
        <div
          className="mark"
          style={{
            width: 46,
            height: 46,
            borderRadius: 12,
            margin: "0 auto 18px",
            display: "grid",
            placeItems: "center",
            fontFamily: "var(--mono)",
            fontWeight: 700,
            color: "#04201d",
            fontSize: 20,
            background: "radial-gradient(circle at 30% 30%, var(--accent), var(--accent-dim))",
            boxShadow: "0 0 22px var(--accent-glow)",
          }}
        >
          C
        </div>
        <h1 style={{ fontSize: 22, margin: "0 0 4px" }}>CAOP</h1>
        <div className="eyebrow" style={{ marginBottom: 22 }}>
          CONTROL TOWER · SENAE / ECUAPASS
        </div>

        {err ? (
          <div
            style={{
              background: "rgba(248,113,113,0.1)",
              border: "1px solid rgba(248,113,113,0.3)",
              color: "#ffc9c9",
              borderRadius: 8,
              padding: "8px 12px",
              fontSize: 12.5,
              marginBottom: 16,
            }}
          >
            No se pudo iniciar sesión ({err}). Intenta nuevamente.
          </div>
        ) : null}

        <a
          href="/api/auth/login"
          style={{
            display: "block",
            background: "var(--accent)",
            color: "#04201d",
            fontWeight: 600,
            padding: "11px 16px",
            borderRadius: 8,
            textDecoration: "none",
          }}
        >
          Ingresar con Keycloak
        </a>
        <p style={{ color: "var(--muted-2)", fontSize: 11.5, marginTop: 18 }}>
          Acceso restringido al personal autorizado.
        </p>
      </div>
    </div>
  );
}
