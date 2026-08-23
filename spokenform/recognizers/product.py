"""Pure policy tables for product and vehicle labels."""

from __future__ import annotations

_PRODUCT_LABEL_WORDS = {
    "sn": "serial number",
    "s/n": "serial number",
    "serial": "serial number",
    "serial number": "serial number",
    "seriennummer": "serial number",
    "sku": "SKU",
    "vin": "VIN",
    "imei": "IMEI",
    "iccid": "ICCID",
    "model": "model",
    "modelo": "modelo",
    "part": "part number",
    "part number": "part number",
    "product": "product code",
    "product code": "product code",
    "barcode": "barcode",
    "bar code": "barcode",
    "license plate": "license plate",
    "license": "license",
    "plate": "plate",
    "kennzeichen": "Kennzeichen",
    "tag": "tag",
    "tax identifier": "tax identifier",
    "identifier": "identifier",
    "id": "I D",
    "firmware": "firmware",
    "matrikelnummer": "Matrikelnummer",
    "registration": "registration",
    "rfc": "RFC",
    "p/n": "P N",
}
_SERIAL_LABEL_KEYS = frozenset(
    {
        "sn",
        "s/n",
        "serial",
        "serial number",
        "seriennummer",
        "pin",
        "barcode",
        "bar code",
        "matrikelnummer",
        "tax identifier",
        "identifier",
        "id",
        "p/n",
        "tag",
    }
)
_LICENSE_LABEL_KEYS = frozenset({"license plate", "license", "plate", "kennzeichen"})
_MODEL_LABEL_KEYS = frozenset({"model", "modelo"})


def product_label_text(label_key: str, fallback: str) -> str:
    """Return the stable spoken label for a typed product value."""
    return _PRODUCT_LABEL_WORDS.get(label_key, fallback)


def product_label_category(label_key: str) -> str:
    """Classify a product label without applying rendering policy."""
    if label_key == "vin":
        return "vin"
    if label_key in _LICENSE_LABEL_KEYS:
        return "license"
    if label_key in _SERIAL_LABEL_KEYS:
        return "serial"
    if label_key in _MODEL_LABEL_KEYS:
        return "model"
    return "product"


__all__ = ["product_label_category", "product_label_text"]
