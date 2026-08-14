// Tipos y helpers de presentación (sin dependencias server-only).
// Seguro de importar tanto en Server como en Client Components.

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

export interface Declaration {
  id: string;
  declaration_number: string;
  status: string;
  aforo_channel: string | null;
  signed: boolean;
  external_ref: string | null;
  error_code: string | null;
  error_description: string | null;
  is_simulated: boolean;
}

export interface CustomerSummary {
  id: string;
  ruc: string;
  legal_name: string;
  status: string;
  email: string | null;
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

export function readiness(n: string | number): number {
  return Math.round(Number(n));
}

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
