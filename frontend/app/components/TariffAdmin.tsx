"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { importTariff, publishTariffVersion } from "@/app/lib/actions";

interface Version {
  id: string;
  number: string;
  status: string;
  codes_count: number;
  rules_count: number;
  published_at?: string | null;
  created_at: string;
}

function statusPill(s: string): string {
  if (s === "ACTIVE") return "ok";
  if (s === "STAGED" || s === "PENDING_APPROVAL") return "warn";
  return "";
}

export function TariffAdmin({ versions }: { versions: Version[] }) {
  const router = useRouter();
  const fileRef = useRef<HTMLInputElement>(null);
  const [version, setVersion] = useState("");
  const [eff, setEff] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  async function doImport() {
    const file = fileRef.current?.files?.[0];
    if (!file || !version.trim() || !eff) {
      setMsg("Completa versión, fecha de vigencia y selecciona el PDF.");
      return;
    }
    setBusy(true);
    setMsg("Subiendo e ingiriendo el arancel… puede tardar ~40s.");
    try {
      const fd = new FormData();
      fd.append("file", file, file.name);
      fd.append("version_number", version.trim());
      fd.append("effective_from", eff);
      const r = await importTariff(fd);
      if (!r.ok) {
        setMsg(`Error: ${r.error}`);
      } else {
        setMsg(
          `Versión ${version} importada en STAGED: ${r.codes} códigos, ${r.rules} reglas` +
            (r.errors && r.errors.length ? ` · ${r.errors.length} avisos de validación` : "") +
            ". Publícala en la tabla para activarla.",
        );
        if (fileRef.current) fileRef.current.value = "";
        setVersion("");
        router.refresh();
      }
    } finally {
      setBusy(false);
    }
  }

  async function doPublish(v: Version) {
    const activa = versions.find((x) => x.status === "ACTIVE");
    const verb = v.status === "SUPERSEDED" ? "revertir a" : "publicar";
    if (!confirm(
      `¿${verb === "publicar" ? "Publicar" : "Revertir a"} la versión ${v.number}?` +
        (activa && activa.id !== v.id ? ` Reemplazará la versión activa (${activa.number}).` : ""),
    )) return;
    setBusy(true);
    try {
      const r = await publishTariffVersion(v.id);
      setMsg(r.ok ? `Versión ${v.number} ACTIVA: ${r.codes} códigos, ${r.rules} reglas.` : `Error: ${r.error}`);
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card rise section-gap">
      <div className="head"><h2>Administración del arancel</h2></div>

      <div className="form-row" style={{ flexWrap: "wrap", alignItems: "flex-end", gap: 12 }}>
        <label className="field" style={{ minWidth: 190 }}>
          <span>Versión (identificador)</span>
          <input value={version} placeholder="p. ej. COMEX-011-2023" onChange={(e) => setVersion(e.target.value)} />
        </label>
        <label className="field">
          <span>Vigente desde</span>
          <input type="date" value={eff} onChange={(e) => setEff(e.target.value)} />
        </label>
        <label className="field" style={{ minWidth: 220 }}>
          <span>PDF del Arancel del Ecuador</span>
          <input ref={fileRef} type="file" accept="application/pdf" />
        </label>
        <button className="btn" disabled={busy} onClick={doImport}>Importar</button>
      </div>
      {msg ? <div style={{ marginTop: 10, fontSize: 12.5, color: "var(--muted)" }}>{msg}</div> : null}

      <div style={{ marginTop: 16, overflowX: "auto" }}>
        <table className="tbl" style={{ width: "100%" }}>
          <thead>
            <tr>
              <th>Versión</th><th>Estado</th><th className="num">Códigos</th>
              <th className="num">Reglas</th><th>Publicada</th><th></th>
            </tr>
          </thead>
          <tbody>
            {versions.length === 0 ? (
              <tr><td colSpan={6} className="empty">Sin versiones. Importa el Arancel del Ecuador.</td></tr>
            ) : null}
            {versions.map((v) => (
              <tr key={v.id}>
                <td className="mono">{v.number}</td>
                <td><span className={`pill ${statusPill(v.status)}`}>{v.status}</span></td>
                <td className="num">{v.codes_count}</td>
                <td className="num">{v.rules_count}</td>
                <td style={{ color: "var(--muted-2)", fontSize: 12 }}>
                  {v.published_at ? new Date(v.published_at).toLocaleString() : "—"}
                </td>
                <td>
                  {v.status !== "ACTIVE" ? (
                    <button className="btn ghost" disabled={busy} onClick={() => doPublish(v)}>
                      {v.status === "SUPERSEDED" ? "Revertir" : "Publicar"}
                    </button>
                  ) : <span style={{ color: "var(--muted-2)", fontSize: 11 }}>activa</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
