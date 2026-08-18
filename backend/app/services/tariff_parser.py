"""Adaptadores de fuente arancelaria + parser del Arancel del Ecuador (PDF).

Arquitectura desacoplada (§ diseño): el resto del sistema consume *registros
normalizados* y no conoce cómo se obtienen. `TariffSourceAdapter` es el contrato;
`ArancelPdfAdapter` lo implementa parseando el PDF oficial del Arancel del Ecuador.

El parseo usa pdfplumber por coordenadas: cada fila del arancel tiene columnas en
posiciones X fijas — Código | Designación | UF | Tarifa (Ad-Valorem %) | Observaciones.
Los guiones iniciales de la designación indican el nivel jerárquico.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Protocol

# Las columnas del PDF se desplazan algunos puntos según la página, por eso la
# detección es RELATIVA (no por umbrales absolutos): el código va a la izquierda;
# la tarifa (Ad-Valorem) es el número más a la derecha en la zona derecha; la UF es
# el token alfabético inmediatamente anterior a la tarifa.
_X_CODE_MAX = 95      # el código ocupa la columna izquierda
_X_RIGHT_MIN = 340    # zona derecha (UF + tarifa) empieza aquí aprox.
_UF_WINDOW = 70       # la UF está a lo sumo ~70pt a la izquierda de la tarifa

_NUM = re.compile(r"^\d+([.,]\d+)?$")
_CODE10 = re.compile(r"^\d{4}\.\d{2}\.\d{2}\.\d{2}$")
# Formatos reales del Arancel del Ecuador:
#   capítulo (2 díg.): 01, 84
#   partida (4 díg., escrita dd.dd): 01.05, 84.71
#   subpartida/nacional (dddd + pares con punto): 0105.11 | 0105.11.00 | 8471.30.00.00
_CODE_ANY = re.compile(r"^(\d{2}|\d{2}\.\d{2}|\d{4}(\.\d{2}){0,3})$")
_LEADING_DASHES = re.compile(r"^(\s*-\s*)+")


@dataclass
class TariffRecord:
    code: str                      # con puntos, p. ej. 0105.11.00.10
    code_normalized: str           # solo dígitos
    level: int                     # nº de dígitos (2/4/6/8/10)
    description: str               # designación propia (sin guiones)
    physical_unit: str | None      # UF: u, Kg, ...
    ad_valorem: Decimal | None     # % tarifa arancelaria (None si la fila no la trae)
    dash_depth: int = 0            # profundidad indicada por guiones
    full_description: str | None = None
    parent_code: str | None = None
    observations: str | None = None


class TariffSourceAdapter(Protocol):
    """Contrato de una fuente arancelaria. Devuelve registros normalizados."""

    name: str

    def parse(self, path: str) -> list[TariffRecord]: ...


def _to_pct(raw: str) -> Decimal | None:
    """Convierte el texto de tarifa a porcentaje Ad-Valorem, o None si no es un % simple.

    Los valores > 100 corresponden a tarifas COMPUESTAS/CONDICIONALES (típicas en
    vehículos: '35% ó 20% de 3001 cc'…) que este parser no puede representar como un
    porcentaje único: se devuelven como None para que el resolvedor las marque como
    'faltante' (metodología propia, fase posterior) y NUNCA como un arancel erróneo.
    """
    raw = (raw or "").strip().replace("%", "").replace(",", ".")
    if not raw:
        return None
    if not re.match(r"^\d+(\.\d+)?$", raw):
        return None
    try:
        val = Decimal(raw)
    except InvalidOperation:
        return None
    return val if 0 <= val <= 100 else None


def _split_columns(tokens: list[tuple[float, str]]) -> tuple[str, str, str, str, str]:
    """Reparte los tokens de una línea (x0, texto) en columnas de forma RELATIVA.

    Código = tokens a la izquierda; Tarifa = número más a la derecha en la zona
    derecha; UF = alfabético justo antes de la tarifa; el resto = designación.
    Robusto al desplazamiento de columnas entre páginas.
    """
    toks = sorted(tokens, key=lambda t: t[0])
    code_parts = [t for x, t in toks if x < _X_CODE_MAX]
    rest = [(x, t) for x, t in toks if x >= _X_CODE_MAX]

    tar = ""
    tar_x: float | None = None
    for x, t in rest:  # rest asc por x → el último numérico en zona derecha gana
        if x >= _X_RIGHT_MIN and _NUM.match(t):
            tar, tar_x = t, x

    uf_parts: list[str] = []
    obs_parts: list[str] = []
    desc_parts: list[str] = []
    for x, t in rest:
        if tar_x is not None and x == tar_x and t == tar:
            continue
        if tar_x is not None and (tar_x - _UF_WINDOW) <= x < tar_x and not _NUM.match(t):
            uf_parts.append(t)
        elif tar_x is not None and x > tar_x:
            obs_parts.append(t)
        else:
            desc_parts.append(t)
    return (
        "".join(code_parts).strip(),
        " ".join(desc_parts).strip(),
        " ".join(uf_parts).strip(),
        tar.strip(),
        " ".join(obs_parts).strip(),
    )


# Limpieza de descripciones extraídas del PDF (encabezados de página colados,
# puntos suspensivos de índice, espaciado tras puntuación). No resuelve el pegado
# genuino todo-minúsculas del origen (requeriría diccionario).
_DESC_HEADER = re.compile(
    r"\s*\d{0,4}\s*(?:Tarifa\s+Arancelaria|Arancel\s+del\s+Ecuador)\s*\d{0,4}", re.I
)
_DESC_DOTLEAD = re.compile(r"\s*\.{2,}\s*")
_DESC_PUNCT_SP = re.compile(
    r"([A-Za-zÁÉÍÓÚÑáéíóúñ0-9])([,;:])(?=[A-Za-zÁÉÍÓÚÑáéíóúñ])"
)


def clean_description(s: str | None) -> str | None:
    """Normaliza una descripción del arancel: quita encabezados de página, puntos
    de índice y añade espacio tras comas/puntos y coma pegados. Conserva el texto
    si al limpiar quedara vacío."""
    if not s:
        return s
    t = _DESC_HEADER.sub(" ", s)
    t = _DESC_DOTLEAD.sub(" ", t)
    t = _DESC_PUNCT_SP.sub(r"\1\2 ", t)
    t = re.sub(r"\s{2,}", " ", t).strip(" .,;:-\t")
    return t or s


def _parse_lines(pdf) -> list[tuple[str, str, str, str, str]]:
    """Devuelve tuplas (code, desc, uf, tar, obs) por línea visual del PDF."""
    from collections import defaultdict

    rows: list[tuple[str, str, str, str, str]] = []
    for page in pdf.pages:
        words = page.extract_words(keep_blank_chars=False)
        lines: dict[int, list] = defaultdict(list)
        for w in words:
            lines[round(w["top"] / 3)].append(w)
        for key in sorted(lines):
            toks = sorted(((w["x0"], w["text"]) for w in lines[key]), key=lambda t: t[0])
            rows.append(_split_columns(toks))
    return rows


def parse_arancel_pdf(path: str) -> list[TariffRecord]:
    """Parsea el PDF del Arancel del Ecuador a registros normalizados.

    Reconstruye jerarquía (parent_code por prefijo) y descripción compuesta
    (full_description) usando la cadena de ancestros.
    """
    import pdfplumber

    with pdfplumber.open(path) as pdf:
        raw_lines = _parse_lines(pdf)

    records: list[TariffRecord] = []
    last: TariffRecord | None = None
    for code, desc, uf, tar, obs in raw_lines:
        code_clean = code.replace(" ", "")
        if _CODE_ANY.match(code_clean):
            norm = code_clean.replace(".", "")
            m = _LEADING_DASHES.match(desc)
            dash_depth = m.group(0).count("-") if m else 0
            clean_desc = _LEADING_DASHES.sub("", desc).strip()
            rec = TariffRecord(
                code=code_clean,
                code_normalized=norm,
                level=len(norm),
                description=clean_desc,
                physical_unit=uf or None,
                ad_valorem=_to_pct(tar),
                dash_depth=dash_depth,
                observations=obs or None,
            )
            records.append(rec)
            last = rec
        elif desc and last is not None and not code_clean and not desc.lstrip().startswith("-"):
            # Continuación real (la designación envuelve): NO empieza con guion.
            # Los encabezados sin código empiezan con guion y se ignoran (no son subpartida).
            last.description = (last.description + " " + desc.strip()).strip()
            if not last.physical_unit and uf:
                last.physical_unit = uf
            if last.ad_valorem is None:
                last.ad_valorem = _to_pct(tar)

    records = _dedup(records)
    _link_hierarchy(records)
    # Limpieza final de descripciones (encabezados, puntos de índice, puntuación).
    for r in records:
        r.description = clean_description(r.description) or r.description
        r.full_description = clean_description(r.full_description)
    return records


def _dedup(records: list[TariffRecord]) -> list[TariffRecord]:
    """Elimina códigos repetidos (artefactos de paginación), conservando el más informativo."""
    best: dict[str, TariffRecord] = {}
    for r in records:
        ex = best.get(r.code_normalized)
        if ex is None:
            best[r.code_normalized] = r
        elif (r.ad_valorem is not None and ex.ad_valorem is None) or (
            len(r.description or "") > len(ex.description or "")
        ):
            best[r.code_normalized] = r
    return list(best.values())


def _link_hierarchy(records: list[TariffRecord]) -> None:
    """Asigna parent_code (prefijo más largo existente) y full_description (cadena de ancestros)."""
    by_norm: dict[str, TariffRecord] = {r.code_normalized: r for r in records}
    for r in records:
        parent = None
        n = r.code_normalized
        for length in range(len(n) - 1, 1, -1):
            cand = n[:length]
            if cand in by_norm:
                parent = cand
                break
        r.parent_code = parent
    for r in records:
        chain: list[str] = []
        cur: TariffRecord | None = r
        seen: set[str] = set()
        while cur is not None and cur.code_normalized not in seen:
            seen.add(cur.code_normalized)
            if cur.description:
                chain.append(cur.description)
            cur = by_norm.get(cur.parent_code) if cur.parent_code else None
        r.full_description = " > ".join(reversed(chain)) if chain else r.description


class ArancelPdfAdapter:
    """Fuente arancelaria: PDF oficial del Arancel del Ecuador."""

    name = "ArancelPdfAdapter"

    def parse(self, path: str) -> list[TariffRecord]:
        return parse_arancel_pdf(path)
