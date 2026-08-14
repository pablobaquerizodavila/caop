"""Conector VUE (Ventanilla Única): contrato común + SIMULADOR.

El adapter real (cuando exista documentación/credenciales oficiales) implementará
el mismo Protocol `VueConnector`. El simulador NO inventa endpoints ni formatos
reales: produce estados EXTERNOS ficticios claramente marcados, que se normalizan
a estados internos vía `map_vue_external`.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Protocol

EXTERNAL_TO_INTERNAL: dict[str, str] = {
    "PERMIT_GRANTED": "APPROVED",
    "PERMIT_DENIED": "REJECTED",
    "PENDING_REVIEW": "REQUESTED",
}


def map_vue_external(external_status: str) -> str:
    return EXTERNAL_TO_INTERNAL.get(external_status, external_status)


class VueUnavailableError(Exception):
    """La VUE no está disponible (para probar resiliencia/retry)."""


@dataclass
class VueResult:
    external_status: str
    external_ref: str | None = None
    permit_number: str | None = None
    valid_until: str | None = None  # ISO date
    error_code: str | None = None
    error_description: str | None = None
    payload: dict = field(default_factory=dict)


class VueConnector(Protocol):
    @property
    def is_simulator(self) -> bool: ...
    def request_permit(self, permit: dict, scenario: str) -> VueResult: ...
    def check_status(self, external_ref: str) -> VueResult: ...


class VueSimulator:
    """Simulador determinista y parametrizable por escenario."""

    is_simulator = True

    def request_permit(self, permit: dict, scenario: str = "APPROVE") -> VueResult:
        scenario = (scenario or "APPROVE").upper()
        if scenario == "UNAVAILABLE":
            raise VueUnavailableError("SIMULADO: VUE no disponible")

        ref = "VUE-SIM-" + uuid.uuid4().hex[:10].upper()
        if scenario == "REJECT":
            return VueResult(
                external_status="PERMIT_DENIED",
                external_ref=ref,
                error_code="SIM-VUE-001",
                error_description="SIMULADO: requisito de control previo no cumplido.",
                payload={"simulated": True, "scenario": "REJECT"},
            )
        if scenario == "PENDING":
            return VueResult(
                external_status="PENDING_REVIEW",
                external_ref=ref,
                payload={"simulated": True, "scenario": "PENDING"},
            )

        # APPROVE (por defecto)
        valid_until = (date.today() + timedelta(days=365)).isoformat()
        number = "SIM-" + str(permit.get("document_code", "PERMIT")) + "-" + uuid.uuid4().hex[:6].upper()
        return VueResult(
            external_status="PERMIT_GRANTED",
            external_ref=ref,
            permit_number=number,
            valid_until=valid_until,
            payload={"simulated": True, "granted": True, "ref": ref},
        )

    def check_status(self, external_ref: str) -> VueResult:
        # El simulador asume que un trámite en revisión termina aprobado.
        return VueResult(
            external_status="PERMIT_GRANTED",
            external_ref=external_ref,
            valid_until=(date.today() + timedelta(days=365)).isoformat(),
            payload={"simulated": True, "ref": external_ref},
        )


_connector: VueConnector | None = None


def get_vue_connector() -> VueConnector:
    global _connector
    if _connector is None:
        _connector = VueSimulator()
    return _connector


def set_vue_connector(c: VueConnector) -> None:
    global _connector
    _connector = c
