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

/** Elimina un cliente. Sin cascade, el backend responde 409 si hay historial. */
export async function deleteCustomer(
  customerId: string,
  cascade = false,
): Promise<{ ok: boolean; status?: number; error?: string }> {
  const qs = cascade ? "?cascade=true" : "";
  const res = await fetch(`${API}/api/v1/customers/${customerId}${qs}`, {
    method: "DELETE",
    headers: authHeader(),
    cache: "no-store",
  });
  revalidatePath("/customers");
  if (res.ok) return { ok: true };
  let error = `Error ${res.status}`;
  try {
    const body = await res.json();
    if (typeof body.detail === "string") error = body.detail;
  } catch {
    /* ignore */
  }
  return { ok: false, status: res.status, error };
}

/** Reemplaza un documento subiendo una nueva versión (conserva el historial). */
export async function replaceDocumentVersion(
  documentId: string,
  customerId: string,
  formData: FormData,
): Promise<{ ok: boolean; error?: string }> {
  const file = formData.get("file");
  if (!file || typeof file === "string") return { ok: false, error: "Sin archivo" };
  const fd = new FormData();
  fd.append("file", file, (file as File).name);
  const expiry = String(formData.get("expiry_date") ?? "");
  if (expiry) fd.append("expiry_date", expiry);
  const res = await fetch(`${API}/api/v1/documents/${documentId}/versions`, {
    method: "POST",
    headers: authHeader(),
    body: fd,
    cache: "no-store",
  });
  revalidatePath(`/customers/${customerId}`);
  return res.ok ? { ok: true } : { ok: false, error: `Error ${res.status}` };
}

/** Sube un documento (PDF/imagen) ligado a un cliente (p. ej. RUC, Nombramiento). */
export async function uploadCustomerDocument(
  customerId: string,
  docType: string,
  formData: FormData,
): Promise<{ ok: boolean; error?: string }> {
  const file = formData.get("file");
  if (!file || typeof file === "string") return { ok: false, error: "Sin archivo" };
  const fd = new FormData();
  fd.append("file", file, (file as File).name);
  fd.append("customer_id", customerId);
  fd.append("doc_type", docType);
  const expiry = String(formData.get("expiry_date") ?? "");
  if (expiry) fd.append("expiry_date", expiry);
  const res = await fetch(`${API}/api/v1/documents`, {
    method: "POST",
    headers: authHeader(),
    body: fd,
    cache: "no-store",
  });
  revalidatePath(`/customers/${customerId}`);
  return res.ok ? { ok: true } : { ok: false, error: `Error ${res.status}` };
}

// ---------- CRM: contactos, consentimiento, proveedores ----------
export async function addContact(customerId: string, data: unknown): Promise<Result> {
  const r = await postJson(`/customers/${customerId}/contacts`, data);
  revalidatePath(`/customers/${customerId}`);
  return r;
}

export async function deleteContact(customerId: string, contactId: string): Promise<Result> {
  const res = await fetch(`${API}/api/v1/customers/${customerId}/contacts/${contactId}`, {
    method: "DELETE", headers: authHeader(), cache: "no-store",
  });
  revalidatePath(`/customers/${customerId}`);
  return res.ok ? { ok: true } : { ok: false, error: `Error ${res.status}` };
}

export async function addConsent(customerId: string, data: unknown): Promise<Result> {
  const r = await postJson(`/customers/${customerId}/consents`, data);
  revalidatePath(`/customers/${customerId}`);
  return r;
}

export async function revokeConsent(customerId: string, consentId: string): Promise<Result> {
  const res = await fetch(`${API}/api/v1/customers/${customerId}/consents/${consentId}/revoke`, {
    method: "POST", headers: authHeader(), cache: "no-store",
  });
  revalidatePath(`/customers/${customerId}`);
  return res.ok ? { ok: true } : { ok: false, error: `Error ${res.status}` };
}

export async function createSupplier(data: unknown): Promise<Result> {
  const r = await postJson("/suppliers", data);
  revalidatePath("/suppliers");
  return r;
}

export async function updateSupplier(id: string, data: unknown): Promise<Result> {
  const res = await fetch(`${API}/api/v1/suppliers/${id}`, {
    method: "PATCH", headers: { ...authHeader(), "Content-Type": "application/json" },
    body: JSON.stringify(data), cache: "no-store",
  });
  revalidatePath("/suppliers");
  return res.ok ? { ok: true } : { ok: false, error: `Error ${res.status}` };
}

export async function deleteSupplier(id: string): Promise<Result> {
  const res = await fetch(`${API}/api/v1/suppliers/${id}`, {
    method: "DELETE", headers: authHeader(), cache: "no-store",
  });
  revalidatePath("/suppliers");
  return res.ok ? { ok: true } : { ok: false, error: `Error ${res.status}` };
}

export async function createQuote(payload: unknown): Promise<Result> {
  const r = await postJson("/quotes", payload);
  revalidatePath("/quotes");
  return r;
}

/** Elimina una cotización. Si ya generó expediente, sin cascade responde 409. */
export async function deleteQuote(
  quoteId: string,
  cascade = false,
): Promise<{ ok: boolean; status?: number; error?: string }> {
  const qs = cascade ? "?cascade=true" : "";
  const res = await fetch(`${API}/api/v1/quotes/${quoteId}${qs}`, {
    method: "DELETE",
    headers: authHeader(),
    cache: "no-store",
  });
  revalidatePath("/quotes");
  if (res.ok) return { ok: true };
  let error = `Error ${res.status}`;
  try {
    const b = await res.json();
    if (typeof b.detail === "string") error = b.detail;
  } catch {
    /* ignore */
  }
  return { ok: false, status: res.status, error };
}

/** Edita una cotización en DRAFT (reemplaza ítems/cabecera y recalcula). */
export async function updateQuote(quoteId: string, payload: unknown): Promise<Result> {
  const res = await fetch(`${API}/api/v1/quotes/${quoteId}`, {
    method: "PUT",
    headers: { ...authHeader(), "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  revalidatePath("/quotes");
  revalidatePath(`/quotes/${quoteId}`);
  if (!res.ok) {
    let error = `Error ${res.status}`;
    try {
      const b = await res.json();
      if (typeof b.detail === "string") error = b.detail;
    } catch { /* ignore */ }
    return { ok: false, error };
  }
  const b = await res.json();
  return { ok: true, id: b.id };
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

export interface PreviewLineItem {
  description: string | null;
  model: string | null;
  hs_code: string | null;
  quantity: string | null;
  unit_price: string | null;
  amount: string | null;
  confidence: number;
}

async function _preview(
  path: string,
  formData: FormData,
): Promise<{
  ok: boolean;
  fields?: PreviewField[];
  line_items?: PreviewLineItem[];
  model?: string;
  error?: string;
}> {
  const file = formData.get("file");
  if (!file || typeof file === "string") return { ok: false, error: "Sin archivo" };
  const fd = new FormData();
  fd.append("file", file, (file as File).name);
  const res = await fetch(`${API}/api/v1${path}`, {
    method: "POST",
    headers: authHeader(), // sin Content-Type: fetch fija el boundary del multipart
    body: fd,
    cache: "no-store",
  });
  if (!res.ok) return { ok: false, error: `Error ${res.status}` };
  const j = await res.json();
  return {
    ok: true,
    fields: j.fields as PreviewField[],
    line_items: (j.line_items ?? []) as PreviewLineItem[],
    model: j.model_version as string,
  };
}

export async function extractPreview(formData: FormData) {
  return _preview("/documents/extract-preview", formData);
}

export async function extractTransportPreview(formData: FormData) {
  return _preview("/documents/extract-transport-preview", formData);
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

// ---------- Tarifario de bodega (configuración global) ----------
export async function createWarehouseTariff(data: unknown): Promise<Result> {
  const res = await fetch(`${API}/api/v1/warehouse/tariffs`, {
    method: "POST",
    headers: { ...authHeader(), "Content-Type": "application/json" },
    body: JSON.stringify(data),
    cache: "no-store",
  });
  revalidatePath("/tariffs");
  if (!res.ok) return { ok: false, error: `Error ${res.status}` };
  return { ok: true };
}

export async function updateWarehouseTariff(tariffId: string, data: unknown): Promise<Result> {
  const res = await fetch(`${API}/api/v1/warehouse/tariffs/${tariffId}`, {
    method: "PATCH",
    headers: { ...authHeader(), "Content-Type": "application/json" },
    body: JSON.stringify(data),
    cache: "no-store",
  });
  revalidatePath("/tariffs");
  return res.ok ? { ok: true } : { ok: false, error: `Error ${res.status}` };
}

export async function deleteWarehouseTariff(tariffId: string): Promise<Result> {
  const res = await fetch(`${API}/api/v1/warehouse/tariffs/${tariffId}`, {
    method: "DELETE",
    headers: authHeader(),
    cache: "no-store",
  });
  revalidatePath("/tariffs");
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

// --- Reglas HS -> VUE (configuración global) ---
export async function createVueRule(data: unknown): Promise<Result> {
  const res = await fetch(`${API}/api/v1/vue/rules`, {
    method: "POST",
    headers: { ...authHeader(), "Content-Type": "application/json" },
    body: JSON.stringify(data),
    cache: "no-store",
  });
  revalidatePath("/vue-rules");
  if (!res.ok) return { ok: false, error: `Error ${res.status}` };
  return { ok: true };
}

export async function updateVueRule(ruleId: string, data: unknown): Promise<Result> {
  const res = await fetch(`${API}/api/v1/vue/rules/${ruleId}`, {
    method: "PATCH",
    headers: { ...authHeader(), "Content-Type": "application/json" },
    body: JSON.stringify(data),
    cache: "no-store",
  });
  revalidatePath("/vue-rules");
  return res.ok ? { ok: true } : { ok: false, error: `Error ${res.status}` };
}

export async function deleteVueRule(ruleId: string): Promise<Result> {
  const res = await fetch(`${API}/api/v1/vue/rules/${ruleId}`, {
    method: "DELETE",
    headers: authHeader(),
    cache: "no-store",
  });
  revalidatePath("/vue-rules");
  return res.ok ? { ok: true } : { ok: false, error: `Error ${res.status}` };
}

export async function seedVueRules(): Promise<{ ok: boolean; created?: number; error?: string }> {
  const res = await fetch(`${API}/api/v1/vue/rules/seed-defaults`, {
    method: "POST",
    headers: authHeader(),
    cache: "no-store",
  });
  revalidatePath("/vue-rules");
  if (!res.ok) return { ok: false, error: `Error ${res.status}` };
  const j = await res.json();
  return { ok: true, created: Array.isArray(j.created) ? j.created.length : 0 };
}

export async function applyVueSuggestions(
  caseId: string,
): Promise<{ ok: boolean; count?: number; error?: string }> {
  const res = await fetch(`${API}/api/v1/cases/${caseId}/vue-permits/apply-suggestions`, {
    method: "POST",
    headers: authHeader(),
    cache: "no-store",
  });
  revalidatePath(`/cases/${caseId}`);
  if (!res.ok) return { ok: false, error: `Error ${res.status}` };
  const j = await res.json();
  return { ok: true, count: Array.isArray(j) ? j.length : 0 };
}

// ---------- Centro de notificaciones ----------
export async function resendNotification(
  id: string,
): Promise<{ ok: boolean; status?: string; error?: string }> {
  const res = await fetch(`${API}/api/v1/notifications/${id}/resend`, {
    method: "POST",
    headers: authHeader(),
    cache: "no-store",
  });
  revalidatePath("/notifications");
  if (!res.ok) return { ok: false, error: `Error ${res.status}` };
  return { ok: true, status: (await res.json()).status };
}

export async function updateNotificationTemplate(id: string, data: unknown): Promise<Result> {
  const res = await fetch(`${API}/api/v1/notifications/templates/${id}`, {
    method: "PATCH",
    headers: { ...authHeader(), "Content-Type": "application/json" },
    body: JSON.stringify(data),
    cache: "no-store",
  });
  revalidatePath("/notifications");
  return res.ok ? { ok: true } : { ok: false, error: `Error ${res.status}` };
}

// ---------- Facturación electrónica (SRI) ----------
export async function createInvoice(caseId: string, settlementId: string): Promise<Result> {
  const res = await fetch(`${API}/api/v1/settlements/${settlementId}/invoice`, {
    method: "POST",
    headers: authHeader(),
    cache: "no-store",
  });
  revalidatePath(`/cases/${caseId}`);
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

export async function authorizeInvoice(
  caseId: string, invoiceId: string, scenario: string,
): Promise<Result> {
  const res = await fetch(`${API}/api/v1/invoices/${invoiceId}/authorize`, {
    method: "POST",
    headers: { ...authHeader(), "Content-Type": "application/json" },
    body: JSON.stringify({ scenario }),
    cache: "no-store",
  });
  revalidatePath(`/cases/${caseId}`);
  return res.ok ? { ok: true } : { ok: false, error: `Error ${res.status}` };
}

export async function getInvoiceXml(invoiceId: string): Promise<string | null> {
  const res = await fetch(`${API}/api/v1/invoices/${invoiceId}/xml`, {
    headers: authHeader(),
    cache: "no-store",
  });
  if (!res.ok) return null;
  return await res.text();
}

export async function createCreditNote(caseId: string, invoiceId: string, data: unknown): Promise<Result> {
  const res = await fetch(`${API}/api/v1/invoices/${invoiceId}/credit-notes`, {
    method: "POST",
    headers: { ...authHeader(), "Content-Type": "application/json" },
    body: JSON.stringify(data),
    cache: "no-store",
  });
  revalidatePath(`/cases/${caseId}`);
  if (!res.ok) {
    let error = `Error ${res.status}`;
    try { error = (await res.json()).detail ?? error; } catch { /* ignore */ }
    return { ok: false, error };
  }
  return { ok: true };
}

export async function authorizeCreditNote(
  caseId: string, cnId: string, scenario: string,
): Promise<Result> {
  const res = await fetch(`${API}/api/v1/credit-notes/${cnId}/authorize`, {
    method: "POST",
    headers: { ...authHeader(), "Content-Type": "application/json" },
    body: JSON.stringify({ scenario }),
    cache: "no-store",
  });
  revalidatePath(`/cases/${caseId}`);
  return res.ok ? { ok: true } : { ok: false, error: `Error ${res.status}` };
}

export async function getCreditNoteXml(cnId: string): Promise<string | null> {
  const res = await fetch(`${API}/api/v1/credit-notes/${cnId}/xml`, {
    headers: authHeader(),
    cache: "no-store",
  });
  if (!res.ok) return null;
  return await res.text();
}

export async function createDebitNote(caseId: string, invoiceId: string, data: unknown): Promise<Result> {
  const res = await fetch(`${API}/api/v1/invoices/${invoiceId}/debit-notes`, {
    method: "POST",
    headers: { ...authHeader(), "Content-Type": "application/json" },
    body: JSON.stringify(data),
    cache: "no-store",
  });
  revalidatePath(`/cases/${caseId}`);
  if (!res.ok) {
    let error = `Error ${res.status}`;
    try { error = (await res.json()).detail ?? error; } catch { /* ignore */ }
    return { ok: false, error };
  }
  return { ok: true };
}

export async function authorizeDebitNote(
  caseId: string, dnId: string, scenario: string,
): Promise<Result> {
  const res = await fetch(`${API}/api/v1/debit-notes/${dnId}/authorize`, {
    method: "POST",
    headers: { ...authHeader(), "Content-Type": "application/json" },
    body: JSON.stringify({ scenario }),
    cache: "no-store",
  });
  revalidatePath(`/cases/${caseId}`);
  return res.ok ? { ok: true } : { ok: false, error: `Error ${res.status}` };
}

export async function getDebitNoteXml(dnId: string): Promise<string | null> {
  const res = await fetch(`${API}/api/v1/debit-notes/${dnId}/xml`, {
    headers: authHeader(),
    cache: "no-store",
  });
  if (!res.ok) return null;
  return await res.text();
}

// ---------- Guías de remisión ----------
export async function createWaybill(data: unknown): Promise<Result> {
  const res = await fetch(`${API}/api/v1/waybills`, {
    method: "POST",
    headers: { ...authHeader(), "Content-Type": "application/json" },
    body: JSON.stringify(data),
    cache: "no-store",
  });
  revalidatePath("/waybills");
  if (!res.ok) {
    let error = `Error ${res.status}`;
    try { error = (await res.json()).detail ?? error; } catch { /* ignore */ }
    return { ok: false, error };
  }
  return { ok: true };
}

export async function authorizeWaybill(id: string, scenario: string): Promise<Result> {
  const res = await fetch(`${API}/api/v1/waybills/${id}/authorize`, {
    method: "POST",
    headers: { ...authHeader(), "Content-Type": "application/json" },
    body: JSON.stringify({ scenario }),
    cache: "no-store",
  });
  revalidatePath("/waybills");
  return res.ok ? { ok: true } : { ok: false, error: `Error ${res.status}` };
}

export async function getWaybillXml(id: string): Promise<string | null> {
  const res = await fetch(`${API}/api/v1/waybills/${id}/xml`, {
    headers: authHeader(),
    cache: "no-store",
  });
  if (!res.ok) return null;
  return await res.text();
}

// ---------- Retenciones ----------
export async function createRetention(data: unknown): Promise<Result> {
  const res = await fetch(`${API}/api/v1/retentions`, {
    method: "POST",
    headers: { ...authHeader(), "Content-Type": "application/json" },
    body: JSON.stringify(data),
    cache: "no-store",
  });
  revalidatePath("/retentions");
  if (!res.ok) {
    let error = `Error ${res.status}`;
    try { error = (await res.json()).detail ?? error; } catch { /* ignore */ }
    return { ok: false, error };
  }
  return { ok: true };
}

export async function authorizeRetention(id: string, scenario: string): Promise<Result> {
  const res = await fetch(`${API}/api/v1/retentions/${id}/authorize`, {
    method: "POST",
    headers: { ...authHeader(), "Content-Type": "application/json" },
    body: JSON.stringify({ scenario }),
    cache: "no-store",
  });
  revalidatePath("/retentions");
  return res.ok ? { ok: true } : { ok: false, error: `Error ${res.status}` };
}

export async function getRetentionXml(id: string): Promise<string | null> {
  const res = await fetch(`${API}/api/v1/retentions/${id}/xml`, {
    headers: authHeader(),
    cache: "no-store",
  });
  if (!res.ok) return null;
  return await res.text();
}

async function _fetchBase64(path: string): Promise<string | null> {
  const res = await fetch(`${API}/api/v1${path}`, { headers: authHeader(), cache: "no-store" });
  if (!res.ok) return null;
  return Buffer.from(await res.arrayBuffer()).toString("base64");
}

export async function getInvoiceRide(invoiceId: string): Promise<string | null> {
  return _fetchBase64(`/invoices/${invoiceId}/ride`);
}

export async function getPortalInvoiceRide(caseId: string): Promise<string | null> {
  return _fetchBase64(`/portal/cases/${caseId}/invoice/ride`);
}

export async function getPortalInvoiceXml(caseId: string): Promise<string | null> {
  const res = await fetch(`${API}/api/v1/portal/cases/${caseId}/invoice/xml`, {
    headers: authHeader(),
    cache: "no-store",
  });
  if (!res.ok) return null;
  return await res.text();
}

// ---------- Exportaciones CSV ----------
export async function exportCsv(path: string): Promise<string | null> {
  const res = await fetch(`${API}/api/v1/exports/${path}`, {
    headers: authHeader(),
    cache: "no-store",
  });
  if (!res.ok) return null;
  return await res.text();
}

// ---------- Documentos ----------
export async function documentVersionUrl(
  documentId: string,
  version: number,
): Promise<string | null> {
  const res = await fetch(
    `${API}/api/v1/documents/${documentId}/versions/${version}/download`,
    { headers: authHeader(), cache: "no-store" },
  );
  if (!res.ok) return null;
  return (await res.json()).url as string;
}

// ---------- Alertas proactivas ----------
export async function sendAlertDigest(): Promise<{
  ok: boolean; total?: number; sent?: number; note?: string; error?: string;
}> {
  const res = await fetch(`${API}/api/v1/alerts/digest/send`, {
    method: "POST",
    headers: { ...authHeader(), "Content-Type": "application/json" },
    body: JSON.stringify({}),
    cache: "no-store",
  });
  if (!res.ok) return { ok: false, error: `Error ${res.status}` };
  const j = await res.json();
  return { ok: true, total: j.total, sent: Array.isArray(j.sent) ? j.sent.length : 0, note: j.note };
}

// ---------- Liquidación al cliente ----------
export async function generateSettlement(caseId: string): Promise<Result> {
  const res = await fetch(`${API}/api/v1/cases/${caseId}/settlement`, {
    method: "POST",
    headers: authHeader(),
    cache: "no-store",
  });
  revalidatePath(`/cases/${caseId}`);
  return res.ok ? { ok: true } : { ok: false, error: `Error ${res.status}` };
}

export async function updateSettlement(caseId: string, id: string, data: unknown): Promise<Result> {
  const res = await fetch(`${API}/api/v1/settlements/${id}`, {
    method: "PATCH",
    headers: { ...authHeader(), "Content-Type": "application/json" },
    body: JSON.stringify(data),
    cache: "no-store",
  });
  revalidatePath(`/cases/${caseId}`);
  return res.ok ? { ok: true } : { ok: false, error: `Error ${res.status}` };
}

export async function addSettlementLine(caseId: string, id: string, data: unknown): Promise<Result> {
  const res = await fetch(`${API}/api/v1/settlements/${id}/lines`, {
    method: "POST",
    headers: { ...authHeader(), "Content-Type": "application/json" },
    body: JSON.stringify(data),
    cache: "no-store",
  });
  revalidatePath(`/cases/${caseId}`);
  return res.ok ? { ok: true } : { ok: false, error: `Error ${res.status}` };
}

export async function updateSettlementLine(
  caseId: string, lineId: string, data: unknown,
): Promise<Result> {
  const res = await fetch(`${API}/api/v1/settlement-lines/${lineId}`, {
    method: "PATCH",
    headers: { ...authHeader(), "Content-Type": "application/json" },
    body: JSON.stringify(data),
    cache: "no-store",
  });
  revalidatePath(`/cases/${caseId}`);
  return res.ok ? { ok: true } : { ok: false, error: `Error ${res.status}` };
}

export async function deleteSettlementLine(caseId: string, lineId: string): Promise<Result> {
  const res = await fetch(`${API}/api/v1/settlement-lines/${lineId}`, {
    method: "DELETE",
    headers: authHeader(),
    cache: "no-store",
  });
  revalidatePath(`/cases/${caseId}`);
  return res.ok ? { ok: true } : { ok: false, error: `Error ${res.status}` };
}

export async function issueSettlement(caseId: string, id: string): Promise<Result> {
  const res = await fetch(`${API}/api/v1/settlements/${id}/issue`, {
    method: "POST",
    headers: authHeader(),
    cache: "no-store",
  });
  revalidatePath(`/cases/${caseId}`);
  return res.ok ? { ok: true } : { ok: false, error: `Error ${res.status}` };
}

export async function addPayment(caseId: string, settlementId: string, data: unknown): Promise<Result> {
  const res = await fetch(`${API}/api/v1/settlements/${settlementId}/payments`, {
    method: "POST",
    headers: { ...authHeader(), "Content-Type": "application/json" },
    body: JSON.stringify(data),
    cache: "no-store",
  });
  revalidatePath(`/cases/${caseId}`);
  revalidatePath("/reports");
  return res.ok ? { ok: true } : { ok: false, error: `Error ${res.status}` };
}

export async function deletePayment(caseId: string, paymentId: string): Promise<Result> {
  const res = await fetch(`${API}/api/v1/payments/${paymentId}`, {
    method: "DELETE",
    headers: authHeader(),
    cache: "no-store",
  });
  revalidatePath(`/cases/${caseId}`);
  revalidatePath("/reports");
  return res.ok ? { ok: true } : { ok: false, error: `Error ${res.status}` };
}

export async function sendPaymentReminder(
  caseId: string, settlementId: string,
): Promise<{ ok: boolean; status?: string; to?: string; reason?: string; error?: string }> {
  const res = await fetch(`${API}/api/v1/settlements/${settlementId}/reminder`, {
    method: "POST",
    headers: authHeader(),
    cache: "no-store",
  });
  revalidatePath(`/cases/${caseId}`);
  if (!res.ok) return { ok: false, error: `Error ${res.status}` };
  const j = await res.json();
  return { ok: true, status: j.status, to: j.to, reason: j.reason };
}

export async function settlementPdf(id: string): Promise<string | null> {
  await fetch(`${API}/api/v1/settlements/${id}/pdf`, {
    method: "POST",
    headers: authHeader(),
    cache: "no-store",
  });
  const res = await fetch(`${API}/api/v1/settlements/${id}/pdf/download`, {
    headers: authHeader(),
    cache: "no-store",
  });
  if (!res.ok) return null;
  return (await res.json()).url as string;
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

// ---------- Arancel: autocompletar subpartida ----------
export interface TariffSuggestion {
  code: string;
  description: string;
  full_description?: string | null;
  physical_unit?: string | null;
  ad_valorem?: string | number | null;
}

export async function searchTariffCodes(q: string): Promise<TariffSuggestion[]> {
  if (!q || q.trim().length < 2) return [];
  const res = await fetch(
    `${API}/api/v1/tariff/codes?q=${encodeURIComponent(q)}&limit=15`,
    { headers: authHeader(), cache: "no-store" },
  );
  if (!res.ok) return [];
  return (await res.json()) as TariffSuggestion[];
}

export async function tariffDetail(hsCode: string): Promise<unknown | null> {
  const res = await fetch(
    `${API}/api/v1/tariff/codes/${encodeURIComponent(hsCode)}`,
    { headers: authHeader(), cache: "no-store" },
  );
  if (!res.ok) return null;
  return await res.json();
}

export async function tariffCalculate(payload: unknown): Promise<unknown | null> {
  const res = await fetch(`${API}/api/v1/tariff/calculate`, {
    method: "POST",
    headers: { ...authHeader(), "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  if (!res.ok) return null;
  return await res.json();
}

export async function tariffHistory(hsCode: string): Promise<unknown[]> {
  const res = await fetch(
    `${API}/api/v1/tariff/codes/${encodeURIComponent(hsCode)}/history`,
    { headers: authHeader(), cache: "no-store" },
  );
  if (!res.ok) return [];
  return (await res.json()) as unknown[];
}

// ---------- Reconciliación tributaria (estimado vs. liquidación SENAE) ----------
export async function getReconciliation(caseId: string): Promise<unknown | null> {
  const res = await fetch(`${API}/api/v1/cases/${caseId}/reconciliation`, {
    headers: authHeader(), cache: "no-store",
  });
  if (!res.ok) return null;
  return await res.json();
}

export async function setReconciliation(
  caseId: string, actual: Record<string, number>, reason: string,
): Promise<{ ok: boolean; error?: string }> {
  const res = await fetch(`${API}/api/v1/cases/${caseId}/reconciliation`, {
    method: "PUT", headers: { ...authHeader(), "Content-Type": "application/json" },
    body: JSON.stringify({ actual, reason: reason || null }), cache: "no-store",
  });
  revalidatePath(`/cases/${caseId}`);
  return res.ok ? { ok: true } : { ok: false, error: `Error ${res.status}` };
}

// ---------- Certificados de origen (por cotización) ----------
export async function addCertificate(quoteId: string, data: unknown): Promise<{ ok: boolean; error?: string }> {
  const res = await fetch(`${API}/api/v1/quotes/${quoteId}/certificates`, {
    method: "POST", headers: { ...authHeader(), "Content-Type": "application/json" },
    body: JSON.stringify(data), cache: "no-store",
  });
  revalidatePath(`/quotes/${quoteId}`);
  if (!res.ok) {
    let error = `Error ${res.status}`;
    try { error = (await res.json()).detail ?? error; } catch { /* ignore */ }
    return { ok: false, error };
  }
  return { ok: true };
}

export async function validateCertificate(
  quoteId: string, certId: string, validation_status: string,
): Promise<{ ok: boolean; error?: string }> {
  const res = await fetch(`${API}/api/v1/quotes/${quoteId}/certificates/${certId}`, {
    method: "PATCH", headers: { ...authHeader(), "Content-Type": "application/json" },
    body: JSON.stringify({ validation_status }), cache: "no-store",
  });
  revalidatePath(`/quotes/${quoteId}`);
  return res.ok ? { ok: true } : { ok: false, error: `Error ${res.status}` };
}

export async function deleteCertificate(quoteId: string, certId: string): Promise<{ ok: boolean; error?: string }> {
  const res = await fetch(`${API}/api/v1/quotes/${quoteId}/certificates/${certId}`, {
    method: "DELETE", headers: authHeader(), cache: "no-store",
  });
  revalidatePath(`/quotes/${quoteId}`);
  return res.ok ? { ok: true } : { ok: false, error: `Error ${res.status}` };
}

// ---------- Certificados de origen (por expediente, #7) ----------
export async function addCaseCertificate(caseId: string, data: unknown): Promise<{ ok: boolean; error?: string }> {
  const res = await fetch(`${API}/api/v1/cases/${caseId}/certificates`, {
    method: "POST", headers: { ...authHeader(), "Content-Type": "application/json" },
    body: JSON.stringify(data), cache: "no-store",
  });
  revalidatePath(`/cases/${caseId}`);
  if (!res.ok) {
    let error = `Error ${res.status}`;
    try { error = (await res.json()).detail ?? error; } catch { /* ignore */ }
    return { ok: false, error };
  }
  return { ok: true };
}

export async function validateCaseCertificate(
  caseId: string, certId: string, validation_status: string,
): Promise<{ ok: boolean; error?: string }> {
  const res = await fetch(`${API}/api/v1/cases/${caseId}/certificates/${certId}`, {
    method: "PATCH", headers: { ...authHeader(), "Content-Type": "application/json" },
    body: JSON.stringify({ validation_status }), cache: "no-store",
  });
  revalidatePath(`/cases/${caseId}`);
  return res.ok ? { ok: true } : { ok: false, error: `Error ${res.status}` };
}

export async function deleteCaseCertificate(caseId: string, certId: string): Promise<{ ok: boolean; error?: string }> {
  const res = await fetch(`${API}/api/v1/cases/${caseId}/certificates/${certId}`, {
    method: "DELETE", headers: authHeader(), cache: "no-store",
  });
  revalidatePath(`/cases/${caseId}`);
  return res.ok ? { ok: true } : { ok: false, error: `Error ${res.status}` };
}

// ---------- Arancel: preferencias / acuerdos ----------
export async function seedAgreements(): Promise<{ ok: boolean; agreements?: number; error?: string }> {
  const res = await fetch(`${API}/api/v1/tariff/seed-agreements`, {
    method: "POST", headers: authHeader(), cache: "no-store",
  });
  revalidatePath("/tariff");
  if (!res.ok) return { ok: false, error: `Error ${res.status}` };
  const j = await res.json();
  return { ok: true, agreements: Array.isArray(j.agreements_created) ? j.agreements_created.length : 0 };
}

export async function createTariffPreference(data: unknown): Promise<{ ok: boolean; error?: string }> {
  const res = await fetch(`${API}/api/v1/tariff/preferences`, {
    method: "POST", headers: { ...authHeader(), "Content-Type": "application/json" },
    body: JSON.stringify(data), cache: "no-store",
  });
  revalidatePath("/tariff");
  if (!res.ok) {
    let error = `Error ${res.status}`;
    try { error = (await res.json()).detail ?? error; } catch { /* ignore */ }
    return { ok: false, error };
  }
  return { ok: true };
}

export async function deleteTariffPreference(id: string): Promise<{ ok: boolean; error?: string }> {
  const res = await fetch(`${API}/api/v1/tariff/preferences/${id}`, {
    method: "DELETE", headers: authHeader(), cache: "no-store",
  });
  revalidatePath("/tariff");
  return res.ok ? { ok: true } : { ok: false, error: `Error ${res.status}` };
}

export async function createIceMeasure(data: unknown): Promise<{ ok: boolean; error?: string }> {
  const res = await fetch(`${API}/api/v1/tariff/ice-measures`, {
    method: "POST", headers: { ...authHeader(), "Content-Type": "application/json" },
    body: JSON.stringify(data), cache: "no-store",
  });
  revalidatePath("/tariff");
  if (!res.ok) {
    let error = `Error ${res.status}`;
    try { error = (await res.json()).detail ?? error; } catch { /* ignore */ }
    return { ok: false, error };
  }
  return { ok: true };
}

export async function deleteIceMeasure(id: string): Promise<{ ok: boolean; error?: string }> {
  const res = await fetch(`${API}/api/v1/tariff/ice-measures/${id}`, {
    method: "DELETE", headers: authHeader(), cache: "no-store",
  });
  revalidatePath("/tariff");
  return res.ok ? { ok: true } : { ok: false, error: `Error ${res.status}` };
}

// ---------- Sección B: catálogos y carga masiva ----------
export async function seedControlCatalog(): Promise<{ ok: boolean; authorities?: number; documents?: number; error?: string }> {
  const res = await fetch(`${API}/api/v1/tariff/seed-control`, {
    method: "POST", headers: authHeader(), cache: "no-store",
  });
  revalidatePath("/tariff");
  if (!res.ok) return { ok: false, error: `Error ${res.status}` };
  const j = await res.json();
  return { ok: true, authorities: j.authorities_created, documents: j.documents_created };
}

export async function bulkImportCsv(
  kind: string, formData: FormData,
): Promise<{ ok: boolean; created?: number; errors?: string[]; error?: string }> {
  const file = formData.get("file");
  if (!file || typeof file === "string") return { ok: false, error: "Selecciona un archivo CSV" };
  const fd = new FormData();
  fd.append("file", file, (file as File).name);
  const res = await fetch(`${API}/api/v1/tariff/bulk/${kind}`, {
    method: "POST", headers: authHeader(), body: fd, cache: "no-store",
  });
  revalidatePath("/tariff");
  if (!res.ok) {
    let error = `Error ${res.status}`;
    try { error = (await res.json()).detail ?? error; } catch { /* ignore */ }
    return { ok: false, error };
  }
  const j = await res.json();
  return { ok: true, created: j.created, errors: j.errors };
}

export async function setSourceUrl(code: string, url: string): Promise<{ ok: boolean; error?: string }> {
  const res = await fetch(`${API}/api/v1/tariff/sources/${code}/url?url=${encodeURIComponent(url)}`, {
    method: "PATCH", headers: authHeader(), cache: "no-store",
  });
  revalidatePath("/tariff");
  return res.ok ? { ok: true } : { ok: false, error: `Error ${res.status}` };
}

// ---------- Vigilante de fuentes (#9) ----------
export async function runTariffSync(): Promise<{ ok: boolean; new?: number; sources?: number; status?: string; error?: string }> {
  const res = await fetch(`${API}/api/v1/tariff/sync/run`, {
    method: "POST", headers: authHeader(), cache: "no-store",
  });
  revalidatePath("/tariff");
  if (!res.ok) return { ok: false, error: `Error ${res.status}` };
  const j = await res.json();
  return { ok: true, new: j.new, sources: j.sources, status: j.status };
}

// ---------- Base legal y control previo (#5/#6) ----------
async function _tpost(path: string, data: unknown): Promise<{ ok: boolean; error?: string }> {
  const res = await fetch(`${API}/api/v1/tariff/${path}`, {
    method: "POST", headers: { ...authHeader(), "Content-Type": "application/json" },
    body: JSON.stringify(data), cache: "no-store",
  });
  revalidatePath("/tariff");
  if (!res.ok) {
    let error = `Error ${res.status}`;
    try { error = (await res.json()).detail ?? error; } catch { /* ignore */ }
    return { ok: false, error };
  }
  return { ok: true };
}

async function _tdelete(path: string): Promise<{ ok: boolean; error?: string }> {
  const res = await fetch(`${API}/api/v1/tariff/${path}`, {
    method: "DELETE", headers: authHeader(), cache: "no-store",
  });
  revalidatePath("/tariff");
  return res.ok ? { ok: true } : { ok: false, error: `Error ${res.status}` };
}

export async function createLegalInstrument(d: unknown) { return _tpost("legal-instruments", d); }
export async function deleteLegalInstrument(id: string) { return _tdelete(`legal-instruments/${id}`); }
export async function createControlAuthority(d: unknown) { return _tpost("control-authorities", d); }
export async function createControlDocument(d: unknown) { return _tpost("control-documents", d); }
export async function createRestriction(d: unknown) { return _tpost("restrictions", d); }
export async function deleteRestriction(id: string) { return _tdelete(`restrictions/${id}`); }

// ---------- Tarifas condicionales / por tramos ----------
export async function createTariffTier(data: unknown): Promise<{ ok: boolean; error?: string }> {
  const res = await fetch(`${API}/api/v1/tariff/tiers`, {
    method: "POST", headers: { ...authHeader(), "Content-Type": "application/json" },
    body: JSON.stringify(data), cache: "no-store",
  });
  revalidatePath("/tariff");
  if (!res.ok) {
    let error = `Error ${res.status}`;
    try { error = (await res.json()).detail ?? error; } catch { /* ignore */ }
    return { ok: false, error };
  }
  return { ok: true };
}

export async function deleteTariffTier(id: string): Promise<{ ok: boolean; error?: string }> {
  const res = await fetch(`${API}/api/v1/tariff/tiers/${id}`, {
    method: "DELETE", headers: authHeader(), cache: "no-store",
  });
  revalidatePath("/tariff");
  return res.ok ? { ok: true } : { ok: false, error: `Error ${res.status}` };
}

// ---------- Medidas de defensa comercial ----------
export async function createTradeRemedy(data: unknown): Promise<{ ok: boolean; error?: string }> {
  const res = await fetch(`${API}/api/v1/tariff/trade-remedies`, {
    method: "POST", headers: { ...authHeader(), "Content-Type": "application/json" },
    body: JSON.stringify(data), cache: "no-store",
  });
  revalidatePath("/tariff");
  if (!res.ok) {
    let error = `Error ${res.status}`;
    try { error = (await res.json()).detail ?? error; } catch { /* ignore */ }
    return { ok: false, error };
  }
  return { ok: true };
}

export async function deleteTradeRemedy(id: string): Promise<{ ok: boolean; error?: string }> {
  const res = await fetch(`${API}/api/v1/tariff/trade-remedies/${id}`, {
    method: "DELETE", headers: authHeader(), cache: "no-store",
  });
  revalidatePath("/tariff");
  return res.ok ? { ok: true } : { ok: false, error: `Error ${res.status}` };
}

// ---------- SAFP (franja de precios) ----------
export async function createPriceBand(data: unknown): Promise<{ ok: boolean; error?: string }> {
  const res = await fetch(`${API}/api/v1/tariff/price-bands`, {
    method: "POST", headers: { ...authHeader(), "Content-Type": "application/json" },
    body: JSON.stringify(data), cache: "no-store",
  });
  revalidatePath("/tariff");
  if (!res.ok) {
    let error = `Error ${res.status}`;
    try { error = (await res.json()).detail ?? error; } catch { /* ignore */ }
    return { ok: false, error };
  }
  return { ok: true };
}

export async function deletePriceBand(id: string): Promise<{ ok: boolean; error?: string }> {
  const res = await fetch(`${API}/api/v1/tariff/price-bands/${id}`, {
    method: "DELETE", headers: authHeader(), cache: "no-store",
  });
  revalidatePath("/tariff");
  return res.ok ? { ok: true } : { ok: false, error: `Error ${res.status}` };
}

export async function listBandPeriods(measureId: string): Promise<unknown[]> {
  const res = await fetch(`${API}/api/v1/tariff/price-bands/${measureId}/periods`, {
    headers: authHeader(), cache: "no-store",
  });
  if (!res.ok) return [];
  return (await res.json()) as unknown[];
}

export async function createBandPeriod(measureId: string, data: unknown): Promise<{ ok: boolean; error?: string }> {
  const res = await fetch(`${API}/api/v1/tariff/price-bands/${measureId}/periods`, {
    method: "POST", headers: { ...authHeader(), "Content-Type": "application/json" },
    body: JSON.stringify(data), cache: "no-store",
  });
  revalidatePath("/tariff");
  if (!res.ok) {
    let error = `Error ${res.status}`;
    try { error = (await res.json()).detail ?? error; } catch { /* ignore */ }
    return { ok: false, error };
  }
  return { ok: true };
}

export async function deleteBandPeriod(id: string): Promise<{ ok: boolean; error?: string }> {
  const res = await fetch(`${API}/api/v1/tariff/price-band-periods/${id}`, {
    method: "DELETE", headers: authHeader(), cache: "no-store",
  });
  revalidatePath("/tariff");
  return res.ok ? { ok: true } : { ok: false, error: `Error ${res.status}` };
}

// ---------- Arancel: administración (import / publicar) ----------
export async function importTariff(
  formData: FormData,
): Promise<{ ok: boolean; codes?: number; rules?: number; version_id?: string; status?: string; errors?: string[]; error?: string }> {
  const file = formData.get("file");
  const version = String(formData.get("version_number") ?? "").trim();
  const eff = String(formData.get("effective_from") ?? "").trim();
  if (!file || typeof file === "string") return { ok: false, error: "Selecciona el PDF del arancel" };
  if (!version || !eff) return { ok: false, error: "Indica versión y fecha de vigencia" };
  const fd = new FormData();
  fd.append("file", file, (file as File).name);
  const res = await fetch(
    `${API}/api/v1/tariff/import?version_number=${encodeURIComponent(version)}&effective_from=${encodeURIComponent(eff)}`,
    { method: "POST", headers: authHeader(), body: fd, cache: "no-store" },
  );
  if (!res.ok) {
    let error = `Error ${res.status}`;
    try { error = (await res.json()).detail ?? error; } catch { /* ignore */ }
    return { ok: false, error };
  }
  const j = await res.json();
  revalidatePath("/tariff");
  return { ok: true, codes: j.codes, rules: j.rules, version_id: j.version_id, status: j.status, errors: j.errors };
}

export async function importTariffUrl(
  url: string, version_number: string, effective_from: string,
): Promise<{ ok: boolean; codes?: number; rules?: number; changes?: Record<string, number>; error?: string }> {
  const q = `url=${encodeURIComponent(url)}&version_number=${encodeURIComponent(version_number)}&effective_from=${encodeURIComponent(effective_from)}`;
  const res = await fetch(`${API}/api/v1/tariff/import-url?${q}`, {
    method: "POST", headers: authHeader(), cache: "no-store",
  });
  revalidatePath("/tariff");
  if (!res.ok) {
    let error = `Error ${res.status}`;
    try { error = (await res.json()).detail ?? error; } catch { /* ignore */ }
    return { ok: false, error };
  }
  const j = await res.json();
  return { ok: true, codes: j.codes, rules: j.rules, changes: j.changes };
}

export async function versionChanges(versionId: string): Promise<unknown[]> {
  const res = await fetch(`${API}/api/v1/tariff/versions/${versionId}/changes`, {
    headers: authHeader(), cache: "no-store",
  });
  if (!res.ok) return [];
  return (await res.json()) as unknown[];
}

export async function publishTariffVersion(
  versionId: string,
): Promise<{ ok: boolean; codes?: number; rules?: number; error?: string }> {
  const res = await fetch(`${API}/api/v1/tariff/versions/${versionId}/publish`, {
    method: "POST", headers: authHeader(), cache: "no-store",
  });
  if (!res.ok) {
    let error = `Error ${res.status}`;
    try { error = (await res.json()).detail ?? error; } catch { /* ignore */ }
    return { ok: false, error };
  }
  const j = await res.json();
  revalidatePath("/tariff");
  return { ok: true, codes: j.codes, rules: j.rules };
}

// ---------- Administración: privilegios por rol ----------
export async function seedRolePrivileges(): Promise<{ ok: boolean; created?: number; error?: string }> {
  const res = await fetch(`${API}/api/v1/admin/roles/seed-defaults`, {
    method: "POST", headers: authHeader(), cache: "no-store",
  });
  revalidatePath("/admin");
  if (!res.ok) return { ok: false, error: `Error ${res.status}` };
  const j = await res.json();
  return { ok: true, created: Array.isArray(j.created) ? j.created.length : 0 };
}

export async function createRolePrivilege(data: unknown): Promise<Result> {
  const r = await postJson("/admin/roles", data);
  revalidatePath("/admin");
  return r;
}

export async function updateRolePrivilege(id: string, data: unknown): Promise<Result> {
  const res = await fetch(`${API}/api/v1/admin/roles/${id}`, {
    method: "PATCH", headers: { ...authHeader(), "Content-Type": "application/json" },
    body: JSON.stringify(data), cache: "no-store",
  });
  revalidatePath("/admin");
  if (!res.ok) {
    let error = `Error ${res.status}`;
    try { error = (await res.json()).detail ?? error; } catch { /* ignore */ }
    return { ok: false, error };
  }
  return { ok: true };
}

export async function deleteRolePrivilege(id: string): Promise<Result> {
  const res = await fetch(`${API}/api/v1/admin/roles/${id}`, {
    method: "DELETE", headers: authHeader(), cache: "no-store",
  });
  revalidatePath("/admin");
  if (!res.ok) {
    let error = `Error ${res.status}`;
    try { error = (await res.json()).detail ?? error; } catch { /* ignore */ }
    return { ok: false, error };
  }
  return { ok: true };
}

// ---------- Administración: usuarios (Keycloak) ----------
export async function createKcUser(data: unknown): Promise<Result> {
  const r = await postJson("/admin/users", data);
  revalidatePath("/admin");
  return r;
}

export async function updateKcUser(id: string, data: unknown): Promise<Result> {
  const res = await fetch(`${API}/api/v1/admin/users/${id}`, {
    method: "PATCH", headers: { ...authHeader(), "Content-Type": "application/json" },
    body: JSON.stringify(data), cache: "no-store",
  });
  revalidatePath("/admin");
  if (!res.ok) {
    let error = `Error ${res.status}`;
    try { error = (await res.json()).detail ?? error; } catch { /* ignore */ }
    return { ok: false, error };
  }
  return { ok: true };
}

export async function deleteKcUser(id: string): Promise<Result> {
  const res = await fetch(`${API}/api/v1/admin/users/${id}`, {
    method: "DELETE", headers: authHeader(), cache: "no-store",
  });
  revalidatePath("/admin");
  if (!res.ok) {
    let error = `Error ${res.status}`;
    try { error = (await res.json()).detail ?? error; } catch { /* ignore */ }
    return { ok: false, error };
  }
  return { ok: true };
}

export async function setKcUserRoles(id: string, roles: string[]): Promise<Result> {
  const res = await fetch(`${API}/api/v1/admin/users/${id}/roles`, {
    method: "POST", headers: { ...authHeader(), "Content-Type": "application/json" },
    body: JSON.stringify({ roles }), cache: "no-store",
  });
  revalidatePath("/admin");
  if (!res.ok) {
    let error = `Error ${res.status}`;
    try { error = (await res.json()).detail ?? error; } catch { /* ignore */ }
    return { ok: false, error };
  }
  return { ok: true };
}

export async function resetKcUserPassword(
  id: string, password: string, temporary: boolean,
): Promise<Result> {
  const res = await fetch(`${API}/api/v1/admin/users/${id}/reset-password`, {
    method: "POST", headers: { ...authHeader(), "Content-Type": "application/json" },
    body: JSON.stringify({ password, temporary }), cache: "no-store",
  });
  if (!res.ok) {
    let error = `Error ${res.status}`;
    try { error = (await res.json()).detail ?? error; } catch { /* ignore */ }
    return { ok: false, error };
  }
  return { ok: true };
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
