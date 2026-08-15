"""Tests del pipeline de extracción de proforma (extractor heurístico de texto)."""

import pytest

from app.services.extraction import (
    _parse_number,
    extract_line_items_from_text,
)

PROFORMA = (
    b"SHENZHEN TECH CO LTD\n"
    b"PROFORMA INVOICE No: PI-2024-0088\n"
    b"Date: 2024-11-05\n"
    b"Incoterm: FOB Shenzhen\n"
    b"Currency: USD\n"
    b"1 x Laptop stand   12500.00 USD\n"
    b"Total Amount: 12,500.00\n"
)


@pytest.mark.asyncio
async def test_extract_proforma_fields(client):
    up = await client.post(
        "/api/v1/documents",
        files={"file": ("proforma.txt", PROFORMA, "text/plain")},
        data={"doc_type": "INVOICE"},
    )
    doc_id = up.json()["id"]

    resp = await client.post(f"/api/v1/documents/{doc_id}/versions/1/extract")
    assert resp.status_code == 201, resp.text
    fields = {f["field_name"]: f for f in resp.json()}

    assert fields["invoice_number"]["extracted_value"] == "PI-2024-0088"
    assert fields["incoterm"]["extracted_value"] == "FOB"
    assert fields["currency"]["extracted_value"] == "USD"
    assert fields["total_amount"]["extracted_value"] == "12500.00"
    # Cada dato lleva confianza
    assert 0 < fields["invoice_number"]["confidence_score"] <= 1


# --------------------------------------------------------------------------- #
#  Extracción de ítems línea por línea
# --------------------------------------------------------------------------- #
def test_parse_number_us_and_eu():
    assert _parse_number("1,234.56") == 1234.56   # US
    assert _parse_number("1.234,56") == 1234.56   # EU
    assert _parse_number("1,000") == 1000          # miles (coma, 3 dígitos)
    assert _parse_number("0,25") == 0.25           # decimal EU
    assert _parse_number("250.00") == 250.0
    assert _parse_number("1.000.000") == 1000000   # miles con puntos
    assert _parse_number("abc") is None


def test_line_items_us_header_with_hs():
    text = (
        "No  Description       HS Code       Qty     Unit Price    Amount\n"
        "1   Steel bolts M8    7318.15.00    1000    0.25          250.00\n"
        "2   Flat washers      7318.22.00     500    0.10           50.00\n"
        "Subtotal                                                  300.00\n"
        "Total Amount                                              300.00\n"
    )
    items = extract_line_items_from_text(text)
    assert len(items) == 2
    assert items[0].description == "Steel bolts M8"
    assert items[0].hs_code == "7318.15.00"
    assert items[0].quantity == "1000"
    assert items[0].unit_price == "0.25"
    assert items[0].amount == "250"
    assert items[0].confidence >= 0.7           # cantidad×precio = importe
    assert items[1].quantity == "500"


def test_line_items_header_reordered_columns():
    # Orden distinto: Precio unitario ANTES que cantidad.
    text = (
        "Item            Unit Price   Qty   Amount\n"
        "Widget azul     2.50         4     10.00\n"
    )
    items = extract_line_items_from_text(text)
    assert len(items) == 1
    assert items[0].quantity == "4"
    assert items[0].unit_price == "2.5"
    assert items[0].amount == "10"


def test_line_items_no_header_validated():
    text = (
        "Gadget A   3   5.00   15.00\n"
        "Gadget B   2   7.50   15.00\n"
    )
    items = extract_line_items_from_text(text)
    assert len(items) == 2
    assert items[0].description == "Gadget A"
    assert items[0].quantity == "3"
    assert items[0].unit_price == "5"


def test_line_items_eu_decimals():
    text = (
        "Producto   Cantidad   Precio Unitario   Total\n"
        "Tuerca     500        0,25              125,00\n"
    )
    items = extract_line_items_from_text(text)
    assert len(items) == 1
    assert items[0].quantity == "500"
    assert items[0].unit_price == "0.25"


def test_line_items_column_matching_with_model_es():
    # Layout en español con columna Modelo; alineado por ancho de columna.
    header = "Modelo".ljust(12) + "Descripción".ljust(22) + "Cantidad".ljust(11) + "P. Unitario".ljust(14) + "Total"
    row1 = "PV33-6048".ljust(12) + "Transformador 33kV".ljust(22) + "4".ljust(11) + "525.00".ljust(14) + "2100.00"
    row2 = "SM300W".ljust(12) + "Medidor smart".ljust(22) + "50".ljust(11) + "83.00".ljust(14) + "4150.00"
    items = extract_line_items_from_text(header + "\n" + row1 + "\n" + row2 + "\n")
    assert len(items) == 2
    assert items[0].model == "PV33-6048"
    assert items[0].description == "Transformador 33kV"
    assert items[0].quantity == "4"
    assert items[0].unit_price == "525"
    assert items[1].model == "SM300W"
    assert items[1].quantity == "50"


def test_line_items_column_matching_partno_en():
    # Layout distinto en inglés: "Part No" y "Price".
    header = "Part No".ljust(14) + "Description".ljust(24) + "Qty".ljust(8) + "Price".ljust(12) + "Amount"
    row = "ABC-100".ljust(14) + "Widget blue".ljust(24) + "3".ljust(8) + "5.00".ljust(12) + "15.00"
    items = extract_line_items_from_text(header + "\n" + row + "\n")
    assert len(items) == 1
    assert items[0].model == "ABC-100"
    assert items[0].description == "Widget blue"
    assert items[0].quantity == "3"
    assert items[0].unit_price == "5"


def test_line_items_money_anchored_collapsed_table():
    # Factura real cuyo PDF colapsa la tabla: "Nº Modelo Cant $PU $Importe",
    # el modelo trae números y la descripción va en otro bloque (no asociable).
    text = (
        "NO. Model QTY\n"
        "(pcs) Unit Price AMOUNT\n"
        "1 PV33-6048 TLV 4 $525,00 $2.100,00\n"
        "2 PH50-6000M 4 $405,00 $1.620,00\n"
        "3 SM300W 50 $83,00 $4.150,00\n"
        "74 SUBTOTAL $11.454,00\n"
    )
    items = extract_line_items_from_text(text)
    assert len(items) == 3
    assert items[0].model == "PV33-6048 TLV"
    assert items[0].quantity == "4"
    assert items[0].unit_price == "525"
    assert items[0].amount == "2100"
    assert items[2].model == "SM300W"
    assert items[2].quantity == "50"
    assert items[2].unit_price == "83"


def test_line_items_ignores_header_and_footer_noise():
    # Fechas, folios y direcciones NO deben convertirse en ítems.
    text = (
        "SHENZHEN TECH CO LTD\n"
        "PROFORMA INVOICE No: PI-2024-0088\n"
        "Date: 2024-11-05\n"
        "Address: 123 Main St, Floor 4\n"
        "Item        Qty   Unit Price   Amount\n"
        "Cable USB   10    1.20         12.00\n"
        "Tax 12%                        1.44\n"
    )
    items = extract_line_items_from_text(text)
    assert len(items) == 1
    assert items[0].description == "Cable USB"
    assert items[0].quantity == "10"


@pytest.mark.asyncio
async def test_extract_preview_returns_line_items(client):
    proforma = (
        b"Description   Qty   Unit Price   Amount\n"
        b"Monitor 24in  5     95.00        475.00\n"
        b"Keyboard      5     12.00         60.00\n"
    )
    resp = await client.post(
        "/api/v1/documents/extract-preview",
        files={"file": ("proforma.txt", proforma, "text/plain")},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "line_items" in body
    assert len(body["line_items"]) == 2
    assert body["line_items"][0]["description"] == "Monitor 24in"
    assert body["line_items"][0]["quantity"] == "5"
    assert body["line_items"][0]["unit_price"] == "95"


@pytest.mark.asyncio
async def test_list_extractions(client):
    up = await client.post(
        "/api/v1/documents", files={"file": ("p.txt", PROFORMA, "text/plain")}
    )
    doc_id = up.json()["id"]
    await client.post(f"/api/v1/documents/{doc_id}/versions/1/extract")
    listed = await client.get(f"/api/v1/documents/{doc_id}/versions/1/extractions")
    assert listed.status_code == 200
    assert len(listed.json()) >= 4
