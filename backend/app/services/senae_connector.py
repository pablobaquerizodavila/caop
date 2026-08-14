"""Conector SENAE/ECUAPASS: contrato común + SIMULADOR.

El adapter real (cuando exista documentación oficial) implementará el mismo
Protocol `SenaeConnector`. El simulador NO inventa endpoints ni XML reales:
produce respuestas con estados EXTERNOS ficticios claramente marcados, que luego
se normalizan a estados internos vía `map_external`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

# Mapeo estado EXTERNO (del proveedor) -> estado INTERNO normalizado.
# Los nombres externos aquí son del SIMULADOR; con el adapter real se ajustan
# a los estados oficiales de ECUAPASS tras validar la documentación.
EXTERNAL_TO_INTERNAL: dict[str, str] = {
    "RECEIVED_OK": "ACCEPTED",
    "VALIDATION_ERROR": "REJECTED",
    "LIQUIDATED": "LIQUIDATED",
    "PAYMENT_OK": "PAID",
    "AFORO_ASSIGNED": "AFORO_ASSIGNED",
    "OBSERVATION": "OBSERVED",
    "OBSERVATION_CLEARED": "OBSERVATION_RESOLVED",
    "RELEASE_OK": "RELEASED",
}


def map_external(external_status: str) -> str:
    return EXTERNAL_TO_INTERNAL.get(external_status, external_status)


class SenaeUnavailableError(Exception):
    """El servicio externo no está disponible (para probar resiliencia/retry)."""


@dataclass
class SenaeResult:
    external_status: str
    external_ref: str | None = None
    error_code: str | None = None
    error_description: str | None = None
    payload: dict = field(default_factory=dict)


class SenaeConnector(Protocol):
    @property
    def is_simulator(self) -> bool: ...
    def transmit(self, declaration: dict, scenario: str) -> SenaeResult: ...
    def next_event(self, external_ref: str, step: str, options: dict) -> SenaeResult: ...


class SenaeSimulator:
    """Simulador determinista y parametrizable por escenario."""

    is_simulator = True

    def transmit(self, declaration: dict, scenario: str = "ACCEPT") -> SenaeResult:
        scenario = (scenario or "ACCEPT").upper()
        if scenario == "UNAVAILABLE":
            raise SenaeUnavailableError("SIMULADO: SENAE/ECUAPASS no disponible")
        if scenario == "REJECT":
            return SenaeResult(
                external_status="VALIDATION_ERROR",
                error_code="SIM-VAL-001",
                error_description="SIMULADO: error de validación (dato inconsistente en la DAI).",
                payload={"simulated": True, "scenario": "REJECT"},
            )
        ref = "SIM-" + str(declaration.get("declaration_number", "DAI")).replace("-", "")[-10:]
        return SenaeResult(
            external_status="RECEIVED_OK",
            external_ref=ref,
            payload={"simulated": True, "received": True, "ref": ref},
        )

    def next_event(self, external_ref: str, step: str, options: dict | None = None) -> SenaeResult:
        options = options or {}
        if step == "LIQUIDATE":
            return SenaeResult("LIQUIDATED", external_ref, payload={"simulated": True})
        if step == "PAY":
            return SenaeResult("PAYMENT_OK", external_ref, payload={"simulated": True})
        if step == "AFORO":
            channel = (options.get("aforo_channel") or "AUTOMATICO").upper()
            status = "OBSERVATION" if options.get("observation") else "AFORO_ASSIGNED"
            return SenaeResult(
                status, external_ref,
                payload={"simulated": True, "aforo_channel": channel,
                         "observation": bool(options.get("observation"))},
            )
        if step == "RESOLVE_OBSERVATION":
            return SenaeResult("OBSERVATION_CLEARED", external_ref, payload={"simulated": True})
        if step == "RELEASE":
            return SenaeResult("RELEASE_OK", external_ref, payload={"simulated": True})
        return SenaeResult("UNKNOWN", external_ref, error_code="SIM-STEP",
                           error_description=f"Paso no soportado: {step}")


_connector: SenaeConnector | None = None


def get_senae_connector() -> SenaeConnector:
    global _connector
    if _connector is None:
        _connector = SenaeSimulator()
    return _connector


def set_senae_connector(c: SenaeConnector) -> None:
    global _connector
    _connector = c
