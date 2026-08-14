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
  source_quote_id?: string | null;
  source_quote_number?: string | null;
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
  case_id?: string | null;
  case_number?: string | null;
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

export interface Transport {
  id: string;
  transport_mode: string | null;
  load_type: string | null;
  carrier: string | null;
  mbl_number: string | null;
  hbl_number: string | null;
  mawb_number: string | null;
  hawb_number: string | null;
  vessel: string | null;
  voyage: string | null;
  flight_number: string | null;
  pol: string | null;
  pod: string | null;
  etd: string | null;
  eta: string | null;
  ata: string | null;
}

export interface ContainerRow {
  id: string;
  container_number: string;
  iso_type: string | null;
  status: string;
  arrival_date: string | null;
  free_days: number | null;
  daily_rate: number;
  last_free_day: string | null;
  days_to_last_free_day: number | null;
  days_overdue: number;
  estimated_demurrage: number;
  alarm: string;
}

export interface DemurrageSummary {
  containers: ContainerRow[];
  money_at_risk: number;
  max_alarm: string;
}

export interface AtRiskContainer {
  case_id: string;
  case_number: string;
  container_number: string;
  alarm: string;
  days_to_last_free_day: number | null;
  estimated_demurrage: number;
}

export function alarmClass(a: string): string {
  return { OK: "ok", WARN: "warn", AT_RISK: "risk", CRITICAL: "crit" }[a] ?? "";
}

export interface CustomerSummary {
  id: string;
  ruc: string;
  legal_name: string;
  status: string;
  email: string | null;
}

export interface CustomerHistory {
  customer: { id: string; ruc: string; legal_name: string; trade_name: string | null; email: string | null; status: string };
  stats: { total_cases: number; ready_for_customs: number; total_quotes: number };
  cases: {
    id: string;
    case_number: string;
    current_state: string;
    customs_readiness_score: number;
    transport_mode: string | null;
    origin_country: string | null;
    source_quote_number: string | null;
    created_at: string | null;
  }[];
  quotes: {
    id: string;
    quote_number: string;
    version: number;
    status: string;
    currency: string;
    landed_cost_total: number;
    case_number: string | null;
    created_at: string | null;
  }[];
}

// ---------- Track & Trace (portal público del cliente) ----------
export interface TrackMilestone {
  key: string;
  label: string;
  status: "done" | "current" | "pending";
  at: string | null;
  detail: string | null;
}

export interface TrackContainer {
  number: string;
  status_label: string;
  last_free_day: string | null;
  days_to_last_free_day: number | null;
  alarm: string;
  alarm_label: string;
}

export interface TrackTransport {
  mode: string | null;
  origin: string | null;
  destination: string | null;
  carrier: string | null;
  vessel_or_flight: string | null;
  etd: string | null;
  eta: string | null;
  ata: string | null;
}

export interface TrackView {
  reference: string;
  customer_name: string;
  status_label: string;
  status_sem: Sem;
  progress_pct: number;
  next_step: string | null;
  attention: string | null;
  transport: TrackTransport;
  milestones: TrackMilestone[];
  containers: TrackContainer[];
  last_update: string | null;
}

export interface TrackingLink {
  token: string;
  url: string;
  enabled: boolean;
}

// ---------- Portal del cliente ----------
export interface PortalProfile {
  linked: boolean;
  customer: { id: string; ruc: string; legal_name: string; trade_name: string | null; email: string | null } | null;
  cases: number;
  quotes: number;
}

export interface PortalCaseSummary {
  id: string;
  case_number: string;
  status_label: string;
  status_sem: Sem;
  transport_mode: string | null;
  origin_country: string | null;
  created_at: string | null;
}

export interface PortalQuote {
  id: string;
  quote_number: string;
  version: number;
  status: string;
  currency: string;
  customer_price_total: number;
  landed_cost_total: number;
  valid_until: string | null;
  created_at: string | null;
}

export interface PortalCaseDetail {
  track: TrackView;
  settlement: Settlement | null;
  invoice: Einvoice | null;
}

// ---------- Extracción / OCR de documentos ----------
export interface Extraction {
  id: string;
  field_name: string;
  extracted_value: string | null;
  verified_value: string | null;
  confidence_score: number | null;
  source_page: number | null;
  model_version: string | null;
}

export interface CaseExtractionDoc {
  document_id: string;
  version: number;
  doc_type: string;
  filename: string;
  model_version: string | null;
  fields: Extraction[];
}

export const FIELD_LABELS: Record<string, string> = {
  invoice_number: "N.º de factura",
  supplier_name: "Proveedor",
  incoterm: "Incoterm",
  currency: "Moneda",
  total_amount: "Monto total",
  date: "Fecha",
  line_item_count: "N.º de ítems",
};

export function fieldLabel(s: string): string {
  return FIELD_LABELS[s] ?? s;
}

export function confidenceClass(c: number | null): Sem | "" {
  if (c === null || c <= 0) return "";
  if (c >= 0.8) return "ok";
  if (c >= 0.5) return "warn";
  return "risk";
}

export function confidenceLabel(c: number | null): string {
  if (c === null || c <= 0) return "sin dato";
  return `${Math.round(c * 100)}%`;
}

// ---------- VUE — control previo ----------
export interface VuePermit {
  id: string;
  entity: string;
  document_code: string;
  description: string | null;
  permit_number: string | null;
  status: string;
  blocking: boolean;
  external_ref: string | null;
  issued_at: string | null;
  valid_until: string | null;
  error_description: string | null;
  notes: string | null;
  satisfied: boolean;
}

export interface VueCatalogEntry {
  entity: string;
  document_code: string;
  description: string;
}

export interface VueSuggestion {
  hs_prefix: string;
  entity: string;
  document_code: string;
  description: string | null;
  blocking: boolean;
}

export interface VueRule {
  id: string;
  hs_prefix: string;
  entity: string;
  document_code: string;
  description: string | null;
  blocking: boolean;
  note: string | null;
  status: string;
}

export const VUE_STATUS_LABELS: Record<string, string> = {
  REQUIRED: "Requerido",
  REQUESTED: "En trámite",
  APPROVED: "Aprobado",
  REJECTED: "Rechazado",
  EXEMPT: "Exento",
  EXPIRED: "Vencido",
};

export function vueStatusLabel(s: string): string {
  return VUE_STATUS_LABELS[s] ?? s;
}

export function vueStatusClass(s: string): Sem | "" {
  const map: Record<string, Sem> = {
    APPROVED: "ok",
    EXEMPT: "ok",
    REQUESTED: "warn",
    REQUIRED: "warn",
    REJECTED: "crit",
    EXPIRED: "crit",
  };
  return map[s] ?? "";
}

// ---------- Almacenaje (bodega / depósito temporal) ----------
export interface WarehouseStorage {
  id: string;
  warehouse_name: string | null;
  reference: string | null;
  entry_date: string | null;
  free_days: number | null;
  rate_type: string;
  daily_rate: number;
  chargeable_weight_kg: number | null;
  withdrawal_date: string | null;
  status: string;
  currency: string;
  last_free_day: string | null;
  days_to_last_free_day: number | null;
  days_overdue: number;
  estimated_storage: number;
  alarm: string;
}

export interface WarehouseSummary {
  items: WarehouseStorage[];
  money_at_risk: number;
  max_alarm: string;
}

export interface AtRiskStorage {
  case_id: string;
  case_number: string;
  reference: string | null;
  warehouse_name: string | null;
  alarm: string;
  days_to_last_free_day: number | null;
  estimated_storage: number;
}

export const RATE_TYPE_LABELS: Record<string, string> = {
  PER_DAY: "Por día",
  PER_KG_DAY: "Por kg-día",
  FLAT: "Monto fijo",
};

export interface WarehouseTariff {
  id: string;
  warehouse_name: string;
  transport_mode: string | null;
  free_days: number;
  rate_type: string;
  daily_rate: number;
  currency: string;
  note: string | null;
  active: boolean;
}

// ---------- Liquidación al cliente ----------
export interface SettlementLine {
  id: string;
  kind: string; // FEE / DISBURSEMENT
  category: string;
  description: string | null;
  amount: number;
  taxable: boolean;
  sort_no: number;
}

export interface Settlement {
  id: string;
  settlement_number: string;
  currency: string;
  status: string;
  iva_rate: number;
  subtotal_fees: number;
  subtotal_disbursements: number;
  tax_amount: number;
  total: number;
  notes: string | null;
  issued_at: string | null;
  lines: SettlementLine[];
}

export const SETTLE_CAT_LABELS: Record<string, string> = {
  HONORARIO: "Honorarios",
  TRIBUTO: "Tributos aduaneros",
  FLETE: "Flete",
  SEGURO: "Seguro",
  ALMACENAJE: "Almacenaje",
  DEMURRAGE: "Demurrage",
  PORTUARIO: "Gastos portuarios",
  TRANSPORTE: "Transporte interno",
  OTRO: "Otros",
};

export function settleCatLabel(s: string): string {
  return SETTLE_CAT_LABELS[s] ?? s;
}

// ---------- Documentos / auditoría ----------
export interface DocVersion {
  id: string;
  version: number;
  filename: string;
  size: number;
  sha256: string;
  content_type: string | null;
  created_at: string;
}

export interface CaseDocument {
  id: string;
  doc_type: string;
  source: string;
  versions: DocVersion[];
}

export interface AuditEvent {
  id: string;
  timestamp: string;
  action: string;
  entity: string;
  entity_id: string | null;
  role: string | null;
  service: string | null;
  correlation_id: string | null;
  old_value: Record<string, unknown> | null;
  new_value: Record<string, unknown> | null;
}

export interface NotificationItem {
  id: string;
  channel: string;
  template_code: string | null;
  template_version: number | null;
  to_address: string;
  subject: string | null;
  body: string | null;
  status: string;
  error: string | null;
  customer_id: string | null;
  customs_case_id: string | null;
  created_at: string;
}

export interface NotificationTemplate {
  id: string;
  code: string;
  version: number;
  channel: string;
  subject_template: string | null;
  body_template: string;
  active: boolean;
}

export function notifStatusClass(s: string): Sem | "" {
  const map: Record<string, Sem> = {
    SENT: "ok", DELIVERED: "ok", READ: "ok",
    QUEUED: "warn", SIMULATED: "warn", FAILED: "crit",
  };
  return map[s] ?? "";
}

export function humanSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

// ---------- Facturación electrónica (SRI) ----------
export interface Einvoice {
  id: string;
  settlement_id: string;
  document_type: string;
  ambiente: string;
  estab: string;
  pto_emi: string;
  secuencial: string;
  access_key: string;
  issue_date: string;
  status: string;
  signed: boolean;
  authorization_number: string | null;
  authorized_at: string | null;
  is_simulated: boolean;
  subtotal: number;
  tax_amount: number;
  total: number;
  error: string | null;
}

export interface CreditNote {
  id: string;
  invoice_id: string;
  estab: string;
  pto_emi: string;
  secuencial: string;
  access_key: string;
  issue_date: string;
  status: string;
  authorization_number: string | null;
  is_simulated: boolean;
  motivo: string;
  subtotal: number;
  tax_amount: number;
  total: number;
  error: string | null;
}

export function einvoiceStatusClass(s: string): Sem | "" {
  const map: Record<string, Sem> = {
    AUTHORIZED: "ok", SIGNED: "warn", DRAFT: "warn", REJECTED: "crit",
  };
  return map[s] ?? "";
}

// ---------- Cobranza ----------
export interface Payment {
  id: string;
  amount: number;
  paid_at: string;
  method: string;
  reference: string | null;
  notes: string | null;
}

export interface PaymentsView {
  payments: Payment[];
  total: number;
  paid: number;
  balance: number;
  status: string; // PENDING / PARTIAL / PAID
}

export interface Receivable {
  settlement_id: string;
  settlement_number: string;
  customs_case_id: string | null;
  customer: string;
  currency: string;
  total: number;
  paid: number;
  balance: number;
  due_date: string | null;
  days_overdue: number;
  bucket: string;
}

export interface Receivables {
  items: Receivable[];
  aging: Record<string, number>;
  total_balance: number;
}

export function payStatusClass(s: string): Sem | "" {
  return { PAID: "ok", PARTIAL: "warn", PENDING: "risk" }[s] as Sem ?? "";
}

export function payStatusLabel(s: string): string {
  return { PAID: "Pagada", PARTIAL: "Parcial", PENDING: "Pendiente" }[s] ?? s;
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
