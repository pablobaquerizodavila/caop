"""Modelos ORM. Importar todos aquí para que Alembic los detecte."""

from app.models.audit import AuditEvent
from app.models.checklist import ChecklistItem, Requirement
from app.models.customer import ConsentRecord, Contact, Customer
from app.models.credit_note import CreditNote
from app.models.customs_declaration import CustomsDeclaration
from app.models.debit_note import DebitNote
from app.models.document import Document, DocumentExtraction, DocumentVersion
from app.models.einvoice import ElectronicInvoice
from app.models.notification import Notification, NotificationTemplate
from app.models.organization import Organization
from app.models.quote import CostLine, Quote, QuoteItem, QuoteStatusHistory
from app.models.reconciliation import TaxReconciliation
from app.models.retention import RetentionLine, RetentionVoucher
from app.models.role import Role, user_roles
from app.models.role_privilege import RolePrivilege
from app.models.settlement import Payment, Settlement, SettlementLine
from app.models.shipment import CaseEvent, Container, CustomsCase, Shipment
from app.models.sla import SLAInstance
from app.models.sla_config import BusinessCalendar, SLAPolicy
from app.models.supplier import Supplier
from app.models.tariff import (
    LegalInstrument,
    OfficialSource,
    TariffCode,
    TariffImport,
    TariffVersion,
)
from app.models.tax import TaxRule
from app.models.trade import (
    CertificateOfOrigin,
    Country,
    IceMeasure,
    PriceBandMeasure,
    PriceBandPeriod,
    TariffPreference,
    TradeAgreement,
)
from app.models.user import User
from app.models.vue import VuePermit, VueRule
from app.models.warehouse import WarehouseStorage
from app.models.waybill import WaybillGuide, WaybillItem
from app.models.warehouse_tariff import WarehouseTariff

__all__ = [
    "AuditEvent",
    "BusinessCalendar",
    "CaseEvent",
    "CertificateOfOrigin",
    "ChecklistItem",
    "ConsentRecord",
    "Container",
    "CreditNote",
    "Contact",
    "CostLine",
    "Country",
    "Customer",
    "CustomsCase",
    "CustomsDeclaration",
    "DebitNote",
    "Document",
    "DocumentExtraction",
    "DocumentVersion",
    "IceMeasure",
    "ElectronicInvoice",
    "Notification",
    "NotificationTemplate",
    "Organization",
    "Payment",
    "PriceBandMeasure",
    "PriceBandPeriod",
    "Quote",
    "QuoteItem",
    "QuoteStatusHistory",
    "Requirement",
    "RetentionLine",
    "RetentionVoucher",
    "Role",
    "RolePrivilege",
    "LegalInstrument",
    "OfficialSource",
    "Settlement",
    "SettlementLine",
    "Shipment",
    "SLAInstance",
    "SLAPolicy",
    "Supplier",
    "TariffCode",
    "TariffImport",
    "TariffPreference",
    "TariffVersion",
    "TaxReconciliation",
    "TaxRule",
    "TradeAgreement",
    "User",
    "VuePermit",
    "VueRule",
    "WarehouseStorage",
    "WarehouseTariff",
    "WaybillGuide",
    "WaybillItem",
    "user_roles",
]
