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
