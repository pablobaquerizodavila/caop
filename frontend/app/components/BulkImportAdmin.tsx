"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { bulkImportCsv, seedControlCatalog } from "@/app/lib/actions";

const TEMPLATES: Record<string, string> = {
  preferences: "agreement_code,origin_country,hs_prefix,liberation_pct,preferential_rate,requires_certificate,effective_from",
  ice: "hs_prefix,description,method,ad_valorem_pct,specific_rate,specific_unit,base_type,effective_from",
  remedies: "kind,hs_prefix,origin_country,product,method,ad_valorem_pct,specific_rate,effective_from,effective_to",
  restrictions: "hs_prefix,kind,authority_code,document_code,requirement,effective_from",
};

const LABELS: Record<string, string> = {
  preferences: "Preferencias", ice: "ICE", remedies: "Defensa comercial", restrictions: "Restricciones",
};

export function BulkImportAdmin() {
  const router = useRouter();
  const fileRef = useRef<HTMLInputElement>(null);
  const [kind, setKind] = useState("preferences");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  async function seed() {
    setBusy(true);
    try {
      const r = await seedControlCatalog();
      setMsg(r.ok ? `Catálogo de control sembrado: ${r.authorities} entidades, ${r.documents} documentos.` : `Error: ${r.error}`);
      router.refresh();
    } finally { setBusy(false); }
  }

  async function upload() {
    const file = fileRef.current?.files?.[0];
    if (!file) { setMsg("Selecciona un archivo CSV."); return; }
    setBusy(true);
    setMsg("Importando…");
    try {
      const fd = new FormData();
      fd.append("file", file, file.name);
      const r = await bulkImportCsv(kind, fd);
      if (!r.ok) setMsg(`Error: ${r.error}`);
      else {
        setMsg(`Importadas ${r.created} fila(s) de ${LABELS[kind]}.` + (r.errors && r.errors.length ? ` Avisos: ${r.errors.length} (${r.errors.slice(0, 3).join("; ")})` : ""));
        if (fileRef.current) fileRef.current.value = "";
      }
      router.refresh();
    } finally { setBusy(false); }
  }

  return (
    <div className="card rise section-gap">
      <div className="head" style={{ justifyContent: "space-between" }}>
        <h2>Carga masiva de datos (CSV)</h2>
        <button className="btn ghost" disabled={busy} onClick={seed}>Sembrar entidades de control</button>
      </div>
      <p style={{ color: "var(--muted)", fontSize: 12.5 }}>
        Carga los datos oficiales por archivo. Elige el tipo, descarga la estructura de columnas
        y sube el CSV. No se inventan valores: se persiste lo que trae el archivo.
      </p>
      <div className="form-row" style={{ flexWrap: "wrap", alignItems: "flex-end", gap: 10 }}>
        <label className="field"><span>Tipo</span>
          <select value={kind} onChange={(e) => setKind(e.target.value)}>
            {Object.keys(TEMPLATES).map((k) => <option key={k} value={k}>{LABELS[k]}</option>)}
          </select>
        </label>
        <label className="field" style={{ minWidth: 240 }}><span>Archivo CSV</span>
          <input ref={fileRef} type="file" accept=".csv,text/csv" />
        </label>
        <button className="btn" disabled={busy} onClick={upload}>Importar CSV</button>
      </div>
      <div style={{ marginTop: 8, fontSize: 11.5, color: "var(--muted-2)" }}>
        Columnas: <span className="mono">{TEMPLATES[kind]}</span>
      </div>
      {msg ? <div style={{ marginTop: 8, fontSize: 12.5, color: "var(--muted)" }}>{msg}</div> : null}
    </div>
  );
}
