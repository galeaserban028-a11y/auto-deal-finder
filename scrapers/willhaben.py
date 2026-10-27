"""
Willhaben.at Scraper (Austria 🇦🇹 - Platforma #1 de anunturi din Austria)
========================================================================
Extrage cele mai proaspete anunturi auto de la proprietari din Austria.
Willhaben este echivalentul OLX in Austria, sursa numarul 1 pentru chilipiruri
aduse pe platforma / trailer in Romania.
"""

import json
import hashlib
import requests
from bs4 import BeautifulSoup
from typing import List, Dict
from core.title_parser import TitleParser
from config.settings import MIN_LISTING_PRICE_EUR, MAX_LISTING_PRICE_EUR, MAX_MILEAGE_KM

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "de-AT,de;q=0.9,en;q=0.8",
}


class WillhabenScraper:
    BASE_URL = "https://www.willhaben.at/iad/gebrauchtwagen/auto/gebrauchtwagenboerse"

    @classmethod
    def fetch_latest_listings(cls, max_items: int = 30) -> List[Dict]:
        """
        Extrage ultimele anunturi auto din Austria de pe Willhaben.at.
        """
        listings = []
        try:
            url = (
                f"{cls.BASE_URL}?"
                f"PRICE_FROM={int(MIN_LISTING_PRICE_EUR)}&"
                f"PRICE_TO={int(MAX_LISTING_PRICE_EUR)}&"
                f"rows={max_items}"
            )

            res = requests.get(url, headers=HEADERS, timeout=12)
            if res.status_code != 200:
                return listings

            soup = BeautifulSoup(res.text, "html.parser")
            script_tag = soup.find("script", id="__NEXT_DATA__")
            if not script_tag or not script_tag.string:
                return listings

            data = json.loads(script_tag.string)
            search_result = data.get("props", {}).get("pageProps", {}).get("searchResult", {})
            adverts = search_result.get("advertSummaryList", {}).get("advertSummary", [])

            for ad in adverts:
                if len(listings) >= max_items:
                    break

                ad_id = str(ad.get("id", ""))
                title = (ad.get("description") or "").strip()
                if not ad_id or not title or len(title) < 4:
                    continue

                # Extragere atribute din lista de atribute Willhaben
                attr_dict = {}
                for attr in ad.get("attributes", {}).get("attribute", []):
                    name = attr.get("name")
                    values = attr.get("values", [])
                    if name and values:
                        attr_dict[name] = values[0]

                # Pret
                raw_price = attr_dict.get("PRICE") or attr_dict.get("PRICE/AMOUNT") or "0"
                try:
                    price_eur = float(str(raw_price).replace(",", ".").replace(" ", ""))
                except ValueError:
                    continue

                if price_eur < MIN_LISTING_PRICE_EUR or price_eur > MAX_LISTING_PRICE_EUR:
                    continue

                # Kilometraj
                raw_km = attr_dict.get("MILEAGE", "0")
                try:
                    mileage = int(str(raw_km).replace(".", "").replace(" ", ""))
                except ValueError:
                    mileage = 0

                if mileage > MAX_MILEAGE_KM:
                    continue

                # An fabricatie
                raw_year = attr_dict.get("YEAR_MODEL", "0")
                try:
                    year = int(raw_year)
                except ValueError:
                    year = 0

                # Combustibil
                raw_fuel = (attr_dict.get("ENGINE/FUEL_TYPE") or "").lower()
                fuel_map = {
                    "diesel": "Diesel",
                    "benzin": "Benzina",
                    "petrol": "Benzina",
                    "hybrid": "Hybrid",
                    "elektro": "Electric",
                    "electric": "Electric",
                    "erdgas": "GPL",
                    "autogas": "GPL",
                }
                fuel = "Necunoscut"
                for k, v in fuel_map.items():
                    if k in raw_fuel:
                        fuel = v
                        break

                # Locatie din Austria
                location = attr_dict.get("LOCATION") or attr_dict.get("POSTCODE") or "Austria"
                city = f"{location}, Austria 🇦🇹"

                # Link public Willhaben
                offer_url = f"https://www.willhaben.at/iad/object?adId={ad_id}"

                # Poza principala
                images = ad.get("advertImageList", {}).get("advertImage", [])
                photo_url = images[0].get("mainImageUrl", "") if images else ""

                # TitleParser pentru normalizarea marcii si modelului
                parsed_meta = TitleParser.parse(title)
                detected_make = parsed_meta["make"]
                detected_model = parsed_meta["model"]

                if year == 0 and parsed_meta["year"] > 0:
                    year = parsed_meta["year"]

                if fuel == "Necunoscut" and parsed_meta["fuel"] != "necunoscut":
                    fuel = parsed_meta["fuel"].capitalize()

                # Deduplicare persistenta pe baza ID-ului unic Willhaben
                external_id = f"willhaben_{ad_id}"

                # Tip vanzator
                advertiser_info = ad.get("advertiserInfo", {})
                is_dealer = advertiser_info.get("organisationId") is not None
                seller_type = "dealer" if is_dealer else "private"

                listings.append({
                    "external_id": external_id,
                    "source": "Willhaben (Austria 🇦🇹)",
                    "title": title,
                    "url": offer_url,
                    "price_eur": price_eur,
                    "make": detected_make,
                    "model": detected_model,
                    "year": year,
                    "mileage": mileage,
                    "fuel": fuel,
                    "transmission": "Automata" if any(x in title.lower() for x in ["automatik", "automat", "dsg"]) else "Manuala",
                    "city": city,
                    "seller_type": seller_type,
                    "seller_phone": "",
                    "photo_url": photo_url,
                    "description": f"{title} - Import Austria ({location})",
                })

        except Exception as e:
            print(f"[Willhaben Scraper Error] {e}")

        return listings
