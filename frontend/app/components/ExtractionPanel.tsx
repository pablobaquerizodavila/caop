"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { verifyExtraction } from "@/app/lib/actions";
import {
  type CaseExtractionDoc,
  confidenceClass,
  confidenceLabel,
  docLabel,
  type Extraction,
  fieldLabel,
} from "@/app/lib/format";

function FieldRow({
  caseId,
  documentId,
  version,
  f,
}: {
  caseId: string;
  documentId: string;
  version: number;
  f: Extraction;
}) {
  const router = useRouter();
  const initial = f.verified_value ?? f.extracted_value ?? "";
  const [val, setVal] = useState(initial);
  const [busy, setBusy] = useState(false);
  const dirty = val !== initial;

  async function save() {
    setBusy(true);
    try {
      await verifyExtraction(caseId, documentId, version, f.id, val);
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  const cc = confidenceClass(f.confidence_score);

  return (
    <div className="chk">
      <div className="left" style={{ flex: 1, minWidth: 0 }}>
        <span className={`pill ${cc}`}>{confidenceLabel(f.confidence_score)}</span>
        <div style={{ flex: 1 }}>
          <div className="doc">{fieldLabel(f.field_name)}</div>
          <div className="tag">
            {f.verified_value ? "verificado" : f.extracted_value ? "extraído" : "no reconocido"}
          </div>
        </div>
      </div>
      <div className="actions">
        <input
          type="text"
          value={val}
          placeholder="—"
          onChange={(e) => setVal(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && dirty && !busy) save();
          }}
          style={{ minWidth: 160 }}
        />
        {dirty ? (
          <button className="btn" disabled={busy} onClick={save}>
            Guardar
          </button>
        ) : null}
      </div>
    </div>
  );
}

export function ExtractionPanel({ caseId, docs }: { caseId: string; docs: CaseExtractionDoc[] }) {
  if (!docs || docs.length === 0) return null;

  return (
    <div className="card section-gap rise">
      <div className="head">
        <h2>Datos extraídos (OCR)</h2>
        <span className="count">{docs.length} doc.</span>
      </div>
      {docs.map((d) => (
        <div key={d.document_id}>
          <div className="form-row" style={{ paddingBottom: 4 }}>
            <span className="tag mono">
              {docLabel(d.doc_type)} · {d.filename}
              {d.model_version ? ` · ${d.model_version}` : ""}
            </span>
          </div>
          {d.fields.map((f) => (
            <FieldRow
              key={f.id}
              caseId={caseId}
              documentId={d.document_id}
              version={d.version}
              f={f}
            />
          ))}
        </div>
      ))}
    </div>
  );
}
