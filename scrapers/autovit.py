"""
Autovit.ro Scraper
Extrage cele mai noi anunturi din Romania direct din starea interna Next.js / GraphQL.
Ofera acces la cele mai complete detalii tehnice si preturi reale.
"""

import re
import json
import time
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from core.utils import ron_to_eur

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ro-RO,ro;q=0.9,en-US;q=0.8,en;q=0.7",
}


class AutovitScraper:
    BASE_URL = "https://www.autovit.ro/autoturisme"

    @classmethod
    def fetch_latest_listings(cls, page: int = 1, max_retries: int = 3) -> List[Dict]:
        """
        Descarca cele mai noi anunturi auto de pe Autovit.
        """
        url = f"{cls.BASE_URL}?search[order]=created_at:desc&page={page}"
        listings = []

        for attempt in range(max_retries):
            try:
                response = requests.get(url, headers=HEADERS, timeout=12)
                if response.status_code != 200:
                    time.sleep(2 * (attempt + 1))
                    continue

                data_str = None
                m = re.search(r'<script\s+id="__NEXT_DATA__"[^>]*>(.*?)</script>', response.text, re.DOTALL)
                if m:
                    data_str = m.group(1)
                else:
                    soup = BeautifulSoup(response.text, "html.parser")
                    script_tag = soup.find("script", id="__NEXT_DATA__")
                    if script_tag and script_tag.string:
                        data_str = script_tag.string

                if not data_str:
                    continue

                json_data = json.loads(data_str)
                urql_state = json_data.get("props", {}).get("pageProps", {}).get("urqlState", {})

                for key, val in urql_state.items():
                    data_str = val.get("data")
                    if not data_str:
                        continue
                    
                    parsed = json.loads(data_str)
                    if "advertSearch" not in parsed:
                        continue

                    edges = parsed["advertSearch"].get("edges", [])
                    for edge in edges:
                        node = edge.get("node", {})
                        item = cls._parse_node(node)
                        if item:
                            listings.append(item)

                if listings:
                    break

            except Exception as e:
                print(f"[Autovit Scraper Error attempt {attempt+1}] {e}")

        return listings

    @classmethod
    def _parse_node(cls, node: Dict) -> Optional[Dict]:
        """Extrage si normalizeaza specificatiile unui anunt Autovit."""
        try:
            external_id = node.get("id") or node.get("url")
            if not external_id:
                return None

            title = node.get("title", "").strip()
            url = node.get("url", "")
            if not url.startswith("http"):
                url = f"https://www.autovit.ro{url}"

            # Pret (Asigura pretul total cu TVA inclus - daca isGross e False, folosim grossPrice)
            price_info = node.get("price") or {}
            amount_info = price_info.get("amount") or {}
            gross_info = price_info.get("grossPrice") or {}
            
            # Daca exista grossPrice, acela este pretul final cu TVA
            if gross_info and gross_info.get("value"):
                currency = gross_info.get("currencyCode", "EUR")
                raw_value = float(gross_info.get("value", 0))
            else:
                currency = amount_info.get("currencyCode", "EUR")
                raw_value = float(amount_info.get("value") or amount_info.get("units") or 0.0)

            price_eur = ron_to_eur(raw_value, currency)

            # Parametrii tehnici
            params = {}
            for p in node.get("parameters", []):
                k = p.get("key")
                v = p.get("value")
                dv = p.get("displayValue") or v
                params[k] = (v, dv)

            make = params.get("make", ("", ""))[0] or params.get("make", ("", ""))[1]
            model = params.get("model", ("", ""))[0] or params.get("model", ("", ""))[1]
            
            # An fabricatie
            year_val = params.get("year", ("0", "0"))[0]
            try:
                year = int(year_val)
            except (TypeError, ValueError):
                year = 0

            # Kilometraj
            km_val = params.get("mileage", ("0", "0"))[0]
            try:
                mileage = int(km_val)
            except (TypeError, ValueError):
                mileage = 0

            # Combustibil & Transmisie
            fuel = params.get("fuel_type", ("", ""))[1]
            transmission = params.get("gearbox", ("", ""))[1]

            # Locatie
            loc_node = node.get("location") or {}
            city = (loc_node.get("city") or {}).get("name", "")
            region = (loc_node.get("region") or {}).get("name", "")
            full_city = f"{city}, {region}".strip(", ")

            # Poza de prezentare
            thumb = node.get("thumbnail", {})
            photo_url = thumb.get("x1") if isinstance(thumb, dict) else (thumb or "")

            # Tip vanzator
            seller = node.get("seller") or {}
            seller_type = "dealer" if "ProfessionalSeller" in seller.get("__typename", "") else "private"

            # Descriere scurta (contine adesea *RATE*, *LEASING*, +TVA)
            short_desc = node.get("shortDescription", "") or ""
            full_description = f"{title} {short_desc}".strip()

            return {
                "external_id": f"autovit_{external_id}",
                "source": "Autovit.ro",
                "title": title,
                "url": url,
                "price_eur": price_eur,
                "make": str(make).lower(),
                "model": str(model).lower(),
                "year": year,
                "mileage": mileage,
                "fuel": str(fuel),
                "transmission": str(transmission),
                "city": full_city,
                "seller_type": seller_type,
                "seller_phone": "",
                "photo_url": photo_url,
                "description": full_description
            }
        except Exception as e:
            print(f"[Autovit Parse Error] {e}")
            return None
