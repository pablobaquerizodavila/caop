"""Modelos ORM. Importar todos aquí para que Alembic los detecte."""

from app.models.audit import AuditEvent
from app.models.customer import ConsentRecord, Contact, Customer
from app.models.document import Document, DocumentExtraction, DocumentVersion
from app.models.organization import Organization
from app.models.quote import CostLine, Quote, QuoteItem, QuoteStatusHistory
from app.models.role import Role, user_roles
from app.models.supplier import Supplier
from app.models.tax import TaxRule
from app.models.user import User

__all__ = [
    "AuditEvent",
    "ConsentRecord",
    "Contact",
    "CostLine",
    "Customer",
    "Document",
    "DocumentExtraction",
    "DocumentVersion",
    "Organization",
    "Quote",
    "QuoteItem",
    "QuoteStatusHistory",
    "Role",
    "Supplier",
    "TaxRule",
    "User",
    "user_roles",
]
