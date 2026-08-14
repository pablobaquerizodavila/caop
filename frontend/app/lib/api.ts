// Cliente de API del backend CAOP (server-side fetch).
// En SSR (dentro del contenedor) se usa la red interna de compose (backend:8000);
// NEXT_PUBLIC_API_URL (host público) queda para peticiones desde el navegador.
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

export const API =
  process.env.API_INTERNAL_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://backend:8000";

export async function apiGet<T>(path: string): Promise<T | null> {
  const token = cookies().get("access_token")?.value;
  let res: Response;
  try {
    res = await fetch(`${API}/api/v1${path}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      cache: "no-store",
    });
  } catch {
    return null;
  }
  // Token ausente/expirado -> reautenticar (redirect fuera del try/catch).
  if (res.status === 401) redirect("/login");
  if (!res.ok) return null;
  return (await res.json()) as T;
}

export interface CaseSummary {
  id: string;
  shipment_id: string;
  case_number: string;
  customs_regime: string;
  current_state: string;
  next_expected_event: string | null;
  risk_level: string;
  customs_readiness_score: string | number;
  blocker: string | null;
}

export interface ChecklistItem {
  id: string;
  doc_type: string;
  category: string;
  blocking: boolean;
  status: string;
  document_id: string | null;
  due_at: string | null;
}

export interface CaseEvent {
  event_type: string;
  event_source: string;
  timestamp: string;
  normalized_payload: Record<string, unknown> | null;
}

export interface SlaItem {
  milestone: string;
  start_time: string;
  deadline: string | null;
  status: string;
  escalation_level: number;
}

export interface CaseDetail extends CaseSummary {
  checklist: ChecklistItem[];
  events: CaseEvent[];
  sla: SlaItem[];
}

export interface SlaRisk {
  id: string;
  entity_id: string;
  milestone: string;
  deadline: string | null;
  status: string;
  escalation_level: number;
}

export const SLA_RISKY = ["AT_RISK", "CRITICAL", "BREACHED"];

export function slaChipClass(status: string): string {
  const map: Record<string, string> = {
    ON_TIME: "ok",
    MET: "ok",
    AT_RISK: "warn",
    CRITICAL: "risk",
    BREACHED: "crit",
  };
  return map[status] ?? "";
}

export interface QuoteSummary {
  id: string;
  quote_number: string;
  version: number;
  status: string;
  currency: string;
  total_cif: string | number;
  total_taxes: string | number;
  customer_price_total: string | number;
  landed_cost_total: string | number;
  landed_cost_per_unit: string | number;
  confidence: string | number | null;
  valid_until: string | null;
  calculation_date: string;
}

// ----- Helpers de presentación -----
export function readiness(n: string | number): number {
  return Math.round(Number(n));
}

// Semáforo operacional del spec (§54): NORMAL/ATTENTION/AT_RISK/CRITICAL
export type Sem = "ok" | "warn" | "risk" | "crit";

export function semaphore(c: CaseSummary): Sem {
  if (c.blocker) return "risk";
  const r = readiness(c.customs_readiness_score);
  if (c.current_state === "READY_FOR_CUSTOMS" || r >= 100) return "ok";
  if (r < 40) return "crit";
  if (r < 100) return "warn";
  return "ok";
}

export const STATE_LABELS: Record<string, string> = {
  CASE_CREATED: "Creado",
  AWAITING_DOCUMENTS: "Esperando documentos",
  READY_FOR_CUSTOMS: "Listo para aduana",
};

export const DOC_LABELS: Record<string, string> = {
  COMMERCIAL_INVOICE: "Factura comercial",
  PACKING_LIST: "Packing list",
  BILL_OF_LADING: "Bill of Lading",
  AIR_WAYBILL: "Air Waybill",
  INSURANCE_POLICY: "Póliza de seguro",
  CERTIFICATE_OF_ORIGIN: "Certificado de origen",
};

export function money(v: string | number, cur = "USD"): string {
  return `${cur} ${Number(v).toLocaleString("es-EC", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function stateLabel(s: string): string {
  return STATE_LABELS[s] ?? s;
}

export function docLabel(s: string): string {
  return DOC_LABELS[s] ?? s;
}
