"use server";

// Server Actions: corren en el servidor, leen la cookie httpOnly y reenvían el
// token al backend. El navegador nunca ve el access_token.
import { cookies } from "next/headers";
import { revalidatePath } from "next/cache";

const API = process.env.API_INTERNAL_URL ?? "http://backend:8000";

function authHeader(): Record<string, string> {
  const t = cookies().get("access_token")?.value;
  return t ? { Authorization: `Bearer ${t}` } : {};
}

export async function uploadCaseDocument(formData: FormData): Promise<void> {
  const caseId = String(formData.get("customs_case_id") ?? "");
  const docType = String(formData.get("doc_type") ?? "");
  const file = formData.get("file");
  if (!file || typeof file === "string") return;

  const fd = new FormData();
  fd.append("file", file, (file as File).name);
  if (caseId) fd.append("customs_case_id", caseId);
  if (docType) fd.append("doc_type", docType);

  await fetch(`${API}/api/v1/documents`, {
    method: "POST",
    headers: authHeader(),
    body: fd,
    cache: "no-store",
  });
  if (caseId) revalidatePath(`/cases/${caseId}`);
}

export async function setQuoteStatus(
  quoteId: string,
  status: string,
): Promise<{ ok: boolean; error?: string }> {
  const res = await fetch(`${API}/api/v1/quotes/${quoteId}/status`, {
    method: "POST",
    headers: { ...authHeader(), "Content-Type": "application/json" },
    body: JSON.stringify({ status }),
    cache: "no-store",
  });
  revalidatePath("/quotes");
  revalidatePath("/");
  if (!res.ok) {
    let detail = `Error ${res.status}`;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* ignore */
    }
    return { ok: false, error: detail };
  }
  return { ok: true };
}

type Result = { ok: boolean; id?: string; error?: string };

async function postJson(path: string, payload: unknown): Promise<Result> {
  const res = await fetch(`${API}/api/v1${path}`, {
    method: "POST",
    headers: { ...authHeader(), "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  if (!res.ok) {
    let error = `Error ${res.status}`;
    try {
      const body = await res.json();
      error =
        typeof body.detail === "string"
          ? body.detail
          : Array.isArray(body.detail)
            ? body.detail.map((d: { msg?: string }) => d.msg).join("; ")
            : error;
    } catch {
      /* ignore */
    }
    return { ok: false, error };
  }
  const body = await res.json();
  return { ok: true, id: body.id };
}

export async function createCustomer(payload: unknown): Promise<Result> {
  const r = await postJson("/customers", payload);
  revalidatePath("/customers");
  return r;
}

export async function createQuote(payload: unknown): Promise<Result> {
  const r = await postJson("/quotes", payload);
  revalidatePath("/quotes");
  return r;
}

export async function updateTransport(caseId: string, data: unknown): Promise<Result> {
  const res = await fetch(`${API}/api/v1/cases/${caseId}/transport`, {
    method: "PATCH",
    headers: { ...authHeader(), "Content-Type": "application/json" },
    body: JSON.stringify(data),
    cache: "no-store",
  });
  revalidatePath(`/cases/${caseId}`);
  return res.ok ? { ok: true } : { ok: false, error: `Error ${res.status}` };
}

export async function addContainer(caseId: string, data: unknown): Promise<Result> {
  const res = await fetch(`${API}/api/v1/cases/${caseId}/containers`, {
    method: "POST",
    headers: { ...authHeader(), "Content-Type": "application/json" },
    body: JSON.stringify(data),
    cache: "no-store",
  });
  revalidatePath(`/cases/${caseId}`);
  revalidatePath("/");
  return res.ok ? { ok: true } : { ok: false, error: `Error ${res.status}` };
}

export async function updateContainer(
  caseId: string, containerId: string, data: unknown,
): Promise<Result> {
  const res = await fetch(`${API}/api/v1/containers/${containerId}`, {
    method: "PATCH",
    headers: { ...authHeader(), "Content-Type": "application/json" },
    body: JSON.stringify(data),
    cache: "no-store",
  });
  revalidatePath(`/cases/${caseId}`);
  revalidatePath("/");
  return res.ok ? { ok: true } : { ok: false, error: `Error ${res.status}` };
}

async function daiPost(caseId: string, path: string, body?: unknown): Promise<Result> {
  const res = await fetch(`${API}/api/v1/cases/${caseId}/dai/${path}`, {
    method: "POST",
    headers: { ...authHeader(), "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: "no-store",
  });
  revalidatePath(`/cases/${caseId}`);
  revalidatePath("/");
  if (!res.ok) {
    let error = `Error ${res.status}`;
    try {
      error = (await res.json()).detail ?? error;
    } catch {
      /* ignore */
    }
    return { ok: false, error };
  }
  return { ok: true };
}

export const daiPrepare = (caseId: string) => daiPost(caseId, "prepare");
export const daiSign = (caseId: string) => daiPost(caseId, "sign");
export const daiTransmit = (caseId: string, scenario: string) =>
  daiPost(caseId, "transmit", { scenario });
export const daiAdvance = (caseId: string, aforo_channel?: string, observation = false) =>
  daiPost(caseId, "advance", { aforo_channel: aforo_channel || null, observation });
export const daiResolveObservation = (caseId: string) => daiPost(caseId, "resolve-observation");

// ---------- Extracción / OCR ----------
export interface PreviewField {
  field_name: string;
  value: string | null;
  confidence: number;
}

export async function extractPreview(
  formData: FormData,
): Promise<{ ok: boolean; fields?: PreviewField[]; model?: string; error?: string }> {
  const file = formData.get("file");
  if (!file || typeof file === "string") return { ok: false, error: "Sin archivo" };
  const fd = new FormData();
  fd.append("file", file, (file as File).name);
  const res = await fetch(`${API}/api/v1/documents/extract-preview`, {
    method: "POST",
    headers: authHeader(), // sin Content-Type: fetch fija el boundary del multipart
    body: fd,
    cache: "no-store",
  });
  if (!res.ok) return { ok: false, error: `Error ${res.status}` };
  const j = await res.json();
  return { ok: true, fields: j.fields as PreviewField[], model: j.model_version as string };
}


export async function verifyExtraction(
  caseId: string,
  documentId: string,
  version: number,
  extractionId: string,
  verifiedValue: string,
): Promise<{ ok: boolean; error?: string }> {
  const res = await fetch(
    `${API}/api/v1/documents/${documentId}/versions/${version}/extractions/${extractionId}`,
    {
      method: "PATCH",
      headers: { ...authHeader(), "Content-Type": "application/json" },
      body: JSON.stringify({ verified_value: verifiedValue }),
      cache: "no-store",
    },
  );
  revalidatePath(`/cases/${caseId}`);
  return res.ok ? { ok: true } : { ok: false, error: `Error ${res.status}` };
}

// ---------- Almacenaje (bodega) ----------
export async function addWarehouse(caseId: string, data: unknown): Promise<Result> {
  const res = await fetch(`${API}/api/v1/cases/${caseId}/warehouse`, {
    method: "POST",
    headers: { ...authHeader(), "Content-Type": "application/json" },
    body: JSON.stringify(data),
    cache: "no-store",
  });
  revalidatePath(`/cases/${caseId}`);
  revalidatePath("/");
  return res.ok ? { ok: true } : { ok: false, error: `Error ${res.status}` };
}

export async function updateWarehouse(
  caseId: string,
  storageId: string,
  data: unknown,
): Promise<Result> {
  const res = await fetch(`${API}/api/v1/warehouse/${storageId}`, {
    method: "PATCH",
    headers: { ...authHeader(), "Content-Type": "application/json" },
    body: JSON.stringify(data),
    cache: "no-store",
  });
  revalidatePath(`/cases/${caseId}`);
  revalidatePath("/");
  return res.ok ? { ok: true } : { ok: false, error: `Error ${res.status}` };
}

export async function deleteWarehouse(caseId: string, storageId: string): Promise<Result> {
  const res = await fetch(`${API}/api/v1/warehouse/${storageId}`, {
    method: "DELETE",
    headers: authHeader(),
    cache: "no-store",
  });
  revalidatePath(`/cases/${caseId}`);
  revalidatePath("/");
  return res.ok ? { ok: true } : { ok: false, error: `Error ${res.status}` };
}

// ---------- VUE — control previo ----------
export async function createVuePermit(
  caseId: string,
  data: unknown,
): Promise<{ ok: boolean; error?: string }> {
  const res = await fetch(`${API}/api/v1/cases/${caseId}/vue-permits`, {
    method: "POST",
    headers: { ...authHeader(), "Content-Type": "application/json" },
    body: JSON.stringify(data),
    cache: "no-store",
  });
  revalidatePath(`/cases/${caseId}`);
  return res.ok ? { ok: true } : { ok: false, error: `Error ${res.status}` };
}

export async function requestVuePermit(
  caseId: string,
  permitId: string,
  scenario: string,
): Promise<{ ok: boolean; error?: string }> {
  const res = await fetch(`${API}/api/v1/vue-permits/${permitId}/request`, {
    method: "POST",
    headers: { ...authHeader(), "Content-Type": "application/json" },
    body: JSON.stringify({ scenario }),
    cache: "no-store",
  });
  revalidatePath(`/cases/${caseId}`);
  return res.ok ? { ok: true } : { ok: false, error: `Error ${res.status}` };
}

export async function exemptVuePermit(
  caseId: string,
  permitId: string,
  reason: string,
): Promise<{ ok: boolean; error?: string }> {
  const res = await fetch(`${API}/api/v1/vue-permits/${permitId}/exempt`, {
    method: "POST",
    headers: { ...authHeader(), "Content-Type": "application/json" },
    body: JSON.stringify({ reason }),
    cache: "no-store",
  });
  revalidatePath(`/cases/${caseId}`);
  return res.ok ? { ok: true } : { ok: false, error: `Error ${res.status}` };
}

export async function deleteVuePermit(
  caseId: string,
  permitId: string,
): Promise<{ ok: boolean; error?: string }> {
  const res = await fetch(`${API}/api/v1/vue-permits/${permitId}`, {
    method: "DELETE",
    headers: authHeader(),
    cache: "no-store",
  });
  revalidatePath(`/cases/${caseId}`);
  return res.ok ? { ok: true } : { ok: false, error: `Error ${res.status}` };
}

// ---------- Track & Trace ----------
export async function rotateTracking(
  caseId: string,
): Promise<{ ok: boolean; url?: string; error?: string }> {
  const res = await fetch(`${API}/api/v1/cases/${caseId}/tracking/rotate`, {
    method: "POST",
    headers: authHeader(),
    cache: "no-store",
  });
  revalidatePath(`/cases/${caseId}`);
  if (!res.ok) return { ok: false, error: `Error ${res.status}` };
  const j = await res.json();
  return { ok: true, url: j.url as string };
}

export async function toggleTracking(
  caseId: string,
  enabled: boolean,
): Promise<{ ok: boolean; enabled?: boolean; error?: string }> {
  const res = await fetch(`${API}/api/v1/cases/${caseId}/tracking`, {
    method: "PATCH",
    headers: { ...authHeader(), "Content-Type": "application/json" },
    body: JSON.stringify({ enabled }),
    cache: "no-store",
  });
  revalidatePath(`/cases/${caseId}`);
  if (!res.ok) return { ok: false, error: `Error ${res.status}` };
  const j = await res.json();
  return { ok: true, enabled: j.enabled as boolean };
}

export async function sendTracking(
  caseId: string,
  channel: string,
): Promise<{ ok: boolean; to?: string; status?: string; error?: string }> {
  const res = await fetch(`${API}/api/v1/cases/${caseId}/tracking/send`, {
    method: "POST",
    headers: { ...authHeader(), "Content-Type": "application/json" },
    body: JSON.stringify({ channel }),
    cache: "no-store",
  });
  if (!res.ok) {
    let error = `Error ${res.status}`;
    try {
      error = (await res.json()).detail ?? error;
    } catch {
      /* ignore */
    }
    return { ok: false, error };
  }
  const j = await res.json();
  return { ok: true, to: j.to as string, status: j.status as string };
}

export async function generateQuotePdf(quoteId: string): Promise<string | null> {
  await fetch(`${API}/api/v1/quotes/${quoteId}/pdf`, {
    method: "POST",
    headers: authHeader(),
    cache: "no-store",
  });
  const res = await fetch(`${API}/api/v1/quotes/${quoteId}/pdf/download`, {
    headers: authHeader(),
    cache: "no-store",
  });
  if (!res.ok) return null;
  const j = await res.json();
  return j.url as string; // URL prefirmada de MinIO (alcanzable por el navegador)
}
