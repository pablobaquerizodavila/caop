"""Tests de limpieza de descripciones del arancel."""

from app.services.tariff_parser import clean_description


def test_clean_removes_dot_leaders():
    assert clean_description("Cereales ......................") == "Cereales"


def test_clean_removes_page_header():
    assert clean_description("Los demás 24 Tarifa Arancelaria Silurus spp.") == "Los demás Silurus spp"
    assert clean_description("Partes destinadas Arancel del Ecuador 152") == "Partes destinadas"


def test_clean_spaces_after_comma():
    assert clean_description("Convertidores,cucharones,palas") == "Convertidores, cucharones, palas"


def test_clean_collapses_whitespace_and_keeps_content():
    assert clean_description("De  níquel-cadmio   y  otros") == "De níquel-cadmio y otros"


def test_clean_keeps_original_when_would_empty():
    # Solo puntos/encabezado → conserva algo, no vacío.
    assert clean_description("....") == "...."
    assert clean_description(None) is None
