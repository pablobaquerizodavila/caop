"""Conector SRI (facturación electrónica): contrato común + SIMULADOR.

El adapter real firmará con el certificado .p12 (XAdES-BES) y llamará a los web
services del SRI (recepción + autorización). El SIMULADOR NO firma ni transmite:
marca el comprobante como firmado/autorizado con datos ficticios claramente
identificados, para poder ejercitar el flujo completo sin certificado.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


class SriUnavailableError(Exception):
    """El SRI no está disponible (para probar resiliencia/retry)."""


@dataclass
class SriAuthResult:
    estado: str  # AUTHORIZED / REJECTED
    authorization_number: str | None = None
    message: str | None = None
    payload: dict = field(default_factory=dict)


class SriConnector(Protocol):
    @property
    def is_simulator(self) -> bool: ...
    def sign(self, xml: str) -> str: ...
    def authorize(self, access_key: str, signed_xml: str, scenario: str) -> SriAuthResult: ...


class SriSimulator:
    """Simulador determinista: no firma ni transmite; marca autorizado por defecto."""

    is_simulator = True

    def sign(self, xml: str) -> str:
        # No hay firma real (requiere .p12). Se deja constancia en el XML.
        marker = "<!-- SIMULADO: firma XAdES-BES pendiente (requiere certificado .p12) -->"
        return f"{xml}\n{marker}"

    def authorize(self, access_key: str, signed_xml: str, scenario: str = "AUTHORIZE") -> SriAuthResult:
        scenario = (scenario or "AUTHORIZE").upper()
        if scenario == "UNAVAILABLE":
            raise SriUnavailableError("SIMULADO: SRI no disponible")
        if scenario == "REJECT":
            return SriAuthResult(
                estado="REJECTED",
                message="SIMULADO: comprobante no autorizado (validación del SRI).",
                payload={"simulated": True, "scenario": "REJECT"},
            )
        # AUTHORIZE: desde 2022 el número de autorización es la propia clave de acceso.
        return SriAuthResult(
            estado="AUTHORIZED",
            authorization_number=access_key,
            message="SIMULADO: autorizado (sin transmisión real al SRI).",
            payload={"simulated": True, "authorized": True},
        )


_connector: SriConnector | None = None


def get_sri_connector() -> SriConnector:
    global _connector
    if _connector is None:
        _connector = SriSimulator()
    return _connector


def set_sri_connector(c: SriConnector) -> None:
    global _connector
    _connector = c
