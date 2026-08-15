"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";

import {
  createTariffPreference,
  deleteTariffPreference,
  importTariff,
  publishTariffVersion,
  seedAgreements,
} from "@/app/lib/actions";

interface Version {
  id: string;
  number: string;
  status: string;
  codes_count: number;
  rules_count: number;
  published_at?: string | null;
  created_at: string;
}
interface Agreement { id: string; code: string; name: string; members?: string[] | null }
interface Preference {
  id: string; agreement_id: string; origin_country?: string | null; hs_prefix?: string | null;
  liberation_pct: string | number; requires_certificate: boolean; verification_status: string;
}

function statusPill(s: string): string {
  if (s === "ACTIVE") return "ok";
  if (s === "STAGED" || s === "PENDING_APPROVAL") return "warn";
  return "";
}

export function TariffAdmin({
  versions,
  agreements = [],
  preferences = [],
}: {
  versions: Version[];
  agreements?: Agreement[];
  preferences?: Preference[];
}) {
  const router = useRouter();
  const fileRef = useRef<HTMLInputElement>(null);
  const [version, setVersion] = useState("");
  const [eff, setEff] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [np, setNp] = useState({
    agreement_id: "", origin_country: "", hs_prefix: "", liberation_pct: "100",
    effective_from: "", requires_certificate: true,
  });

  const agName = (id: string) => agreements.find((a) => a.id === id)?.code ?? id.slice(0, 8);

  async function doSeedAgreements() {
    setBusy(true);
    try {
      const r = await seedAgreements();
      setMsg(r.ok ? `Acuerdos sembrados: ${r.agreements}. Carga las preferencias por subpartida desde los anexos.` : `Error: ${r.error}`);
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  async function addPref() {
    if (!np.agreement_id || !np.effective_from) {
      setMsg("Elige acuerdo y fecha de vigencia para la preferencia.");
      return;
    }
    setBusy(true);
    try {
      const r = await createTariffPreference({
        agreement_id: np.agreement_id,
        origin_country: np.origin_country.trim().toUpperCase() || null,
        hs_prefix: np.hs_prefix.trim() || null,
        liberation_pct: Number(np.liberation_pct) || 0,
        requires_certificate: np.requires_certificate,
        effective_from: np.effective_from,
      });
      if (!r.ok) setMsg(`Error: ${r.error}`);
      else { setNp({ ...np, origin_country: "", hs_prefix: "", liberation_pct: "100" }); router.refresh(); }
    } finally {
      setBusy(false);
    }
  }

  async function removePref(id: string) {
    if (!confirm("¿Eliminar esta preferencia?")) return;
    setBusy(true);
    try {
      await deleteTariffPreference(id);
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

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
    <>
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

    <div className="card rise section-gap">
      <div className="head" style={{ justifyContent: "space-between" }}>
        <h2>Preferencias arancelarias</h2>
        {agreements.length === 0 ? (
          <button className="btn" disabled={busy} onClick={doSeedAgreements}>Sembrar acuerdos</button>
        ) : <span className="count">{agreements.length} acuerdos</span>}
      </div>

      {agreements.length > 0 ? (
        <>
          <div className="form-row" style={{ flexWrap: "wrap", alignItems: "flex-end", gap: 10 }}>
            <label className="field" style={{ minWidth: 180 }}>
              <span>Acuerdo</span>
              <select value={np.agreement_id} onChange={(e) => setNp((p) => ({ ...p, agreement_id: e.target.value }))}>
                <option value="">—</option>
                {agreements.map((a) => <option key={a.id} value={a.id}>{a.code} · {a.name.slice(0, 30)}</option>)}
              </select>
            </label>
            <label className="field"><span>Origen (ISO2, opc.)</span>
              <input value={np.origin_country} maxLength={2} placeholder="todos"
                onChange={(e) => setNp((p) => ({ ...p, origin_country: e.target.value }))} style={{ width: 90 }} />
            </label>
            <label className="field"><span>Prefijo HS (opc.)</span>
              <input value={np.hs_prefix} placeholder="todos"
                onChange={(e) => setNp((p) => ({ ...p, hs_prefix: e.target.value }))} style={{ width: 110 }} />
            </label>
            <label className="field"><span>% Liberación</span>
              <input value={np.liberation_pct}
                onChange={(e) => setNp((p) => ({ ...p, liberation_pct: e.target.value }))} style={{ width: 80 }} />
            </label>
            <label className="field"><span>Vigente desde</span>
              <input type="date" value={np.effective_from}
                onChange={(e) => setNp((p) => ({ ...p, effective_from: e.target.value }))} />
            </label>
            <label className="field" style={{ alignItems: "center" }}><span>Cert.</span>
              <input type="checkbox" checked={np.requires_certificate}
                onChange={(e) => setNp((p) => ({ ...p, requires_certificate: e.target.checked }))} />
            </label>
            <button className="btn" disabled={busy || !np.agreement_id} onClick={addPref}>Agregar</button>
          </div>

          <div style={{ marginTop: 14, overflowX: "auto" }}>
            <table className="tbl" style={{ width: "100%" }}>
              <thead>
                <tr><th>Acuerdo</th><th>Origen</th><th>Prefijo HS</th><th className="num">Liberación</th>
                  <th>Cert.</th><th>Estado</th><th></th></tr>
              </thead>
              <tbody>
                {preferences.length === 0 ? (
                  <tr><td colSpan={7} className="empty">Sin preferencias cargadas. La CAN se siembra por defecto.</td></tr>
                ) : null}
                {preferences.map((p) => (
                  <tr key={p.id}>
                    <td className="mono">{agName(p.agreement_id)}</td>
                    <td>{p.origin_country || "todos"}</td>
                    <td className="mono">{p.hs_prefix || "todos"}</td>
                    <td className="num">{String(p.liberation_pct)}%</td>
                    <td>{p.requires_certificate ? "sí" : "no"}</td>
                    <td><span className={`pill ${p.verification_status === "VERIFIED" ? "ok" : "warn"}`}>{p.verification_status}</span></td>
                    <td><button className="btn ghost" disabled={busy} onClick={() => removePref(p.id)}>✕</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : (
        <div className="empty">Siembra los acuerdos comerciales vigentes para empezar a cargar preferencias.</div>
      )}
    </div>
    </>
  );
}
