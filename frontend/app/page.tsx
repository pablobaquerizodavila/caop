async function getHealth() {
  const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  try {
    const res = await fetch(`${base}/api/v1/health`, { cache: "no-store" });
    if (!res.ok) return { status: "error", version: "-" };
    return (await res.json()) as { status: string; version: string };
  } catch {
    return { status: "unreachable", version: "-" };
  }
}

export default async function Home() {
  const health = await getHealth();
  const ok = health.status === "ok";

  return (
    <main style={{ maxWidth: 720, margin: "0 auto", padding: "4rem 1.5rem" }}>
      <h1 style={{ fontSize: "2rem", marginBottom: "0.25rem" }}>CAOP</h1>
      <p style={{ opacity: 0.7, marginTop: 0 }}>
        Customs Autonomous Operations Platform — Sprint S0 (Fundaciones)
      </p>

      <section
        style={{
          marginTop: "2rem",
          padding: "1.25rem 1.5rem",
          borderRadius: 12,
          background: "#161f2b",
          border: "1px solid #22303f",
        }}
      >
        <h2 style={{ fontSize: "1rem", margin: "0 0 0.75rem" }}>Estado del backend</h2>
        <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
          <span
            style={{
              width: 10,
              height: 10,
              borderRadius: "50%",
              background: ok ? "#2ecc71" : "#e74c3c",
              display: "inline-block",
            }}
          />
          <code>
            {health.status}
            {ok ? ` · v${health.version}` : ""}
          </code>
        </div>
      </section>
    </main>
  );
}
