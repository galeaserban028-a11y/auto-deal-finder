"""
Model Scanner - Targeted Liquid Model Arbitrage Scanner
======================================================
Scaneaza direct modelele cele mai cautate si lichide din Romania,
sortate pe pret crescator (cele mai ieftine masini active de pe piata).
Aceasta este metoda prin care gasim chilipiruri reale, nu anunturi oarecare.
"""

import re
import json
import requests
from bs4 import BeautifulSoup
from typing import List, Dict
from scrapers.autovit import AutovitScraper, HEADERS
from config.settings import MIN_LISTING_PRICE_EUR, MAX_LISTING_PRICE_EUR, MAX_MILEAGE_KM

# Modelele cu cea mai mare cerere din Romania (se vand cel mai repede)
TARGET_MODELS = [
    ("volkswagen", "golf"),
    ("volkswagen", "passat"),
    ("volkswagen", "tiguan"),
    ("skoda", "octavia"),
    ("skoda", "superb"),
    ("dacia", "duster"),
    ("dacia", "logan"),
    ("ford", "focus"),
    ("ford", "kuga"),
    ("bmw", "seria-3"),
    ("bmw", "seria-5"),
    ("audi", "a4"),
    ("renault", "megane"),
    ("hyundai", "tucson"),
    ("kia", "sportage"),
]


class ModelScanner:
    """
    Scaneaza cele mai ieftine masini active pentru fiecare model de top.
    """

    @classmethod
    def scan_liquid_bargains(cls, max_per_model: int = 3, min_year: int = 2010) -> List[Dict]:
        all_candidates = []

        for make, model in TARGET_MODELS:
            url = (
                f"https://www.autovit.ro/autoturisme/{make}/{model}?"
                f"search[order]=filter_float_price:asc"
                f"&search[filter_float_year:from]={min_year}"
                f"&search[filter_float_price:from]={int(MIN_LISTING_PRICE_EUR)}"
                f"&search[filter_float_price:to]={int(MAX_LISTING_PRICE_EUR)}"
                f"&search[filter_float_mileage:to]={int(MAX_MILEAGE_KM)}"
                f"&search[filter_enum_damaged]=0"
            )
            try:
                r = requests.get(url, headers=HEADERS, timeout=10)
                if r.status_code != 200 or "__NEXT_DATA__" not in r.text:
                    continue

                data_str = None
                m = re.search(r'<script\s+id="__NEXT_DATA__"[^>]*>(.*?)</script>', r.text, re.DOTALL)
                if m:
                    data_str = m.group(1)
                else:
                    soup = BeautifulSoup(r.text, "html.parser")
                    script_tag = soup.find("script", id="__NEXT_DATA__")
                    if script_tag and script_tag.string:
                        data_str = script_tag.string

                if not data_str:
                    continue

                json_data = json.loads(data_str)
                urql_state = json_data.get("props", {}).get("pageProps", {}).get("urqlState", {})

                model_items = []
                for _, val in urql_state.items():
                    data_str = val.get("data")
                    if not data_str:
                        continue
                    parsed = json.loads(data_str)
                    if "advertSearch" not in parsed:
                        continue

                    for edge in parsed["advertSearch"].get("edges", []):
                        node = edge.get("node", {})
                        item = AutovitScraper._parse_node(node)
                        if item and item.get("price_eur", 0) >= 1500:
                            model_items.append(item)
                            if len(model_items) >= max_per_model:
                                break
                    if model_items:
                        break

                all_candidates.extend(model_items)

            except Exception as e:
                print(f"[ModelScanner] Eroare scanare {make} {model}: {e}")

        return all_candidates
