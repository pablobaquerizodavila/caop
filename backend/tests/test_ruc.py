"""Tests del validador de RUC ecuatoriano."""

import pytest

from app.services.ruc import RUCValidationError, validate_ruc


def test_valid_natural_person_ruc():
    assert validate_ruc("1712345675001") == "1712345675001"


@pytest.mark.parametrize(
    "ruc",
    [
        "123",  # muy corto
        "17123456750011",  # muy largo
        "17123A5675001",  # no numérico
        "9912345675001",  # provincia inválida (99)
        "1712345675000",  # establecimiento 000
        "1712345670001",  # dígito verificador incorrecto (pos. 10 != 5)
    ],
)
def test_invalid_rucs(ruc):
    with pytest.raises(RUCValidationError):
        validate_ruc(ruc)
