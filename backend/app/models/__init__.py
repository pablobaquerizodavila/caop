"""Modelos ORM. Importar todos aquí para que Alembic los detecte."""

from app.models.audit import AuditEvent
from app.models.checklist import ChecklistItem, Requirement
from app.models.customer import ConsentRecord, Contact, Customer
from app.models.credit_note import CreditNote
from app.models.customs_declaration import CustomsDeclaration
from app.models.document import Document, DocumentExtraction, DocumentVersion
from app.models.einvoice import ElectronicInvoice
from app.models.notification import Notification, NotificationTemplate
from app.models.organization import Organization
from app.models.quote import CostLine, Quote, QuoteItem, QuoteStatusHistory
from app.models.role import Role, user_roles
from app.models.settlement import Payment, Settlement, SettlementLine
from app.models.shipment import CaseEvent, Container, CustomsCase, Shipment
from app.models.sla import SLAInstance
from app.models.sla_config import BusinessCalendar, SLAPolicy
from app.models.supplier import Supplier
from app.models.tax import TaxRule
from app.models.user import User
from app.models.vue import VuePermit, VueRule
from app.models.warehouse import WarehouseStorage
from app.models.warehouse_tariff import WarehouseTariff

__all__ = [
    "AuditEvent",
    "BusinessCalendar",
    "CaseEvent",
    "ChecklistItem",
    "ConsentRecord",
    "Container",
    "CreditNote",
    "Contact",
    "CostLine",
    "Customer",
    "CustomsCase",
    "CustomsDeclaration",
    "Document",
    "DocumentExtraction",
    "DocumentVersion",
    "ElectronicInvoice",
    "Notification",
    "NotificationTemplate",
    "Organization",
    "Payment",
    "Quote",
    "QuoteItem",
    "QuoteStatusHistory",
    "Requirement",
    "Role",
    "Settlement",
    "SettlementLine",
    "Shipment",
    "SLAInstance",
    "SLAPolicy",
    "Supplier",
    "TaxRule",
    "User",
    "VuePermit",
    "VueRule",
    "WarehouseStorage",
    "WarehouseTariff",
    "user_roles",
]
