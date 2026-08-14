"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { uploadCaseDocument } from "@/app/lib/actions";
import { docLabel } from "@/app/lib/format";

export function CaseUpload({
  caseId,
  docTypes,
}: {
  caseId: string;
  docTypes: string[];
}) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const formRef = useRef<HTMLFormElement>(null);

  async function onSubmit(formData: FormData) {
    setBusy(true);
    try {
      await uploadCaseDocument(formData);
      formRef.current?.reset();
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  return (
    <form ref={formRef} action={onSubmit} className="form-row">
      <input type="hidden" name="customs_case_id" value={caseId} />
      <select name="doc_type" defaultValue={docTypes[0] ?? "COMMERCIAL_INVOICE"}>
        {docTypes.map((d) => (
          <option key={d} value={d}>
            {docLabel(d)}
          </option>
        ))}
      </select>
      <input type="file" name="file" required />
      <button className="btn" type="submit" disabled={busy}>
        {busy ? "Subiendo…" : "Subir documento"}
      </button>
    </form>
  );
}
