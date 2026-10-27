"""
Utilitare comune pentru scrapere: parsare robusta de pret, kilometraj si poze.

De ce exista: fiecare scraper avea propria parsare de pret, iar Publi24 folosea spatiu
non-breaking (\\xa0) ca separator de mii. Codul vechi elimina doar spatiile normale,
asa ca "10\\xa0500 EUR" devenea 10 € si anuntul era respins ca "pret prea mic".
"""

import re
from typing import Optional

from config.settings import EUR_RON_RATE

# Toate tipurile de spatii folosite ca separator de mii pe site-uri
_SPACE_CHARS = "\u00a0\u202f\u2009\u2007 \t"


def _strip_spaces(text: str) -> str:
    for ch in _SPACE_CHARS:
        text = text.replace(ch, "")
    return text


def detect_currency(text: str) -> str:
    low = (text or "").lower()
    if "lei" in low or "ron" in low:
        return "RON"
    return "EUR"


def parse_price_eur(text: str) -> Optional[float]:
    """
    Transforma un text de pret ("10 500 €", "10.500 EUR", "23\\xa0600 lei", "4,500 €")
    in EUR. Returneaza None daca nu se gaseste un numar plauzibil.
    """
    if not text:
        return None
    compact = _strip_spaces(str(text))
    m = re.search(r"\d[\d.,]*", compact)
    if not m:
        return None
    raw = m.group(0).rstrip(".,")
    # Separatoare de mii: "10.500", "10,500", "1.250.000". Zecimale ("4500,50") le taiem.
    if re.fullmatch(r"\d{1,3}([.,]\d{3})+", raw):
        value = float(re.sub(r"[.,]", "", raw))
    else:
        value = float(re.split(r"[.,]", raw)[0] or 0)
    if value <= 0:
        return None
    if detect_currency(text) == "RON":
        value = value / EUR_RON_RATE
    return round(value, 2)


def parse_km(text: str) -> int:
    """Extrage kilometrajul dintr-un text ("210 651 km", "98.000 Km", "150000km")."""
    if not text:
        return 0
    m = re.search(r"(?<!\d)(\d{1,3}(?:[\s\u00a0\u202f.,]\d{3})+|\d+)\s*km\b", str(text), re.IGNORECASE)
    if not m:
        return 0
    digits = re.sub(r"\D", "", m.group(1))
    return int(digits) if digits else 0


def img_src(img_el) -> str:
    """URL-ul pozei dintr-un tag <img> (sau "" daca lipseste). Nu arunca exceptii pe None."""
    if img_el is None:
        return ""
    return img_el.get("src") or img_el.get("data-src") or ""


def ron_to_eur(value: float, currency: Optional[str]) -> float:
    if (currency or "EUR").upper() in ("RON", "LEI"):
        return round(float(value) / EUR_RON_RATE, 2)
    return float(value)
