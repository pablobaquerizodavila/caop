"""Modelos ORM. Importar todos aquí para que Alembic los detecte."""

from app.models.audit import AuditEvent
from app.models.checklist import ChecklistItem, Requirement
from app.models.customer import ConsentRecord, Contact, Customer
from app.models.document import Document, DocumentExtraction, DocumentVersion
from app.models.notification import Notification, NotificationTemplate
from app.models.organization import Organization
from app.models.quote import CostLine, Quote, QuoteItem, QuoteStatusHistory
from app.models.role import Role, user_roles
from app.models.shipment import CaseEvent, CustomsCase, Shipment
from app.models.sla import SLAInstance
from app.models.supplier import Supplier
from app.models.tax import TaxRule
from app.models.user import User

__all__ = [
    "AuditEvent",
    "CaseEvent",
    "ChecklistItem",
    "ConsentRecord",
    "Contact",
    "CostLine",
    "Customer",
    "CustomsCase",
    "Document",
    "DocumentExtraction",
    "DocumentVersion",
    "Notification",
    "NotificationTemplate",
    "Organization",
    "Quote",
    "QuoteItem",
    "QuoteStatusHistory",
    "Requirement",
    "Role",
    "Shipment",
    "SLAInstance",
    "Supplier",
    "TaxRule",
    "User",
    "user_roles",
]
