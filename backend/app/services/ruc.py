"""Validación de RUC ecuatoriano.

Valida estructura y dígito verificador según el tipo de contribuyente:
- Persona natural   (tercer dígito 0-5): módulo 10 sobre los 9 primeros dígitos.
- Sociedad pública  (tercer dígito 6): módulo 11 (8 primeros + verificador en pos. 9).
- Sociedad privada / extranjero (tercer dígito 9): módulo 11 (9 primeros + verificador).

Además exige 13 dígitos, código de provincia válido y establecimiento distinto de 000.
No sustituye la validación oficial ante SRI/SENAE; es una comprobación de formato robusta.
"""

from __future__ import annotations


class RUCValidationError(ValueError):
    pass


def _valid_province(ruc: str) -> bool:
    province = int(ruc[:2])
    return 1 <= province <= 24 or province in (30, 88)


def _mod(coefficients: list[int], digits: list[int], base: int) -> int:
    total = sum(c * d for c, d in zip(coefficients, digits, strict=True))
    remainder = total % base
    return 0 if remainder == 0 else base - remainder


def _check_natural(ruc: str) -> bool:
    coeffs = [2, 1, 2, 1, 2, 1, 2, 1, 2]
    digits = [int(c) for c in ruc[:9]]
    products = []
    for c, d in zip(coeffs, digits, strict=True):
        p = c * d
        products.append(p - 9 if p >= 10 else p)
    total = sum(products)
    verifier = 0 if total % 10 == 0 else 10 - (total % 10)
    return verifier == int(ruc[9])


def _check_juridical(ruc: str, public: bool) -> bool:
    if public:  # tercer dígito 6: verificador en posición 9 (índice 8), 8 coeficientes
        coeffs = [3, 2, 7, 6, 5, 4, 3, 2]
        digits = [int(c) for c in ruc[:8]]
        return _mod(coeffs, digits, 11) == int(ruc[8])
    # privada/extranjero, tercer dígito 9: verificador en posición 10 (índice 9)
    coeffs = [4, 3, 2, 7, 6, 5, 4, 3, 2]
    digits = [int(c) for c in ruc[:9]]
    return _mod(coeffs, digits, 11) == int(ruc[9])


def validate_ruc(ruc: str) -> str:
    """Devuelve el RUC normalizado o lanza RUCValidationError."""
    ruc = (ruc or "").strip()
    if len(ruc) != 13 or not ruc.isdigit():
        raise RUCValidationError("El RUC debe tener 13 dígitos numéricos.")
    if not _valid_province(ruc):
        raise RUCValidationError("Código de provincia inválido en el RUC.")
    if ruc[10:] == "000":
        raise RUCValidationError("El código de establecimiento no puede ser 000.")

    third = int(ruc[2])
    if third <= 5:
        ok = _check_natural(ruc)
    elif third == 6:
        ok = _check_juridical(ruc, public=True)
    elif third == 9:
        ok = _check_juridical(ruc, public=False)
    else:
        raise RUCValidationError("Tercer dígito del RUC inválido (debe ser 0-6 o 9).")

    if not ok:
        raise RUCValidationError("Dígito verificador del RUC inválido.")
    return ruc
