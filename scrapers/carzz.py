"""
CarZZ.ro Scraper (Platforma dedicata auto din Romania - Antena Group)
====================================================================
Extrage anunturi auto de la proprietari particulari din toata tara.
Foarte bogat in chilipiruri locale de la vanzatori care nu platesc taxe mari pe Autovit.
"""

import re
import requests
from bs4 import BeautifulSoup
from typing import List, Dict
from core.title_parser import TitleParser
from config.settings import MAX_LISTING_PRICE_EUR, MIN_LISTING_PRICE_EUR
from core.utils import parse_price_eur, parse_km, img_src
import hashlib

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ro-RO,ro;q=0.9",
}


class CarZZScraper:
    BASE_URL = "https://carzz.ro/autoturisme.html"

    @classmethod
    def fetch_latest_listings(cls, max_items: int = 35) -> List[Dict]:
        listings = []
        try:
            url = f"{cls.BASE_URL}?order=data:descrescator&pret_max={int(MAX_LISTING_PRICE_EUR)}"
            res = requests.get(url, headers=HEADERS, timeout=10)
            if res.status_code != 200:
                return listings

            soup = BeautifulSoup(res.text, "html.parser")
            cards = soup.find_all("a", class_=lambda c: c and "item_cart" in str(c))

            for card in cards:
                if len(listings) >= max_items:
                    break

                href = card.get("href", "")
                if not href or not href.startswith("http"):
                    continue

                clean_url = href.split("?")[0]

                # Titlu
                title_el = card.find("span", class_="title")
                title = title_el.get_text(" ", strip=True) if title_el else ""
                if not title or len(title) < 4:
                    continue

                # Pret
                price_el = card.find("span", class_="price")
                if not price_el:
                    continue

                price_eur = parse_price_eur(price_el.get_text(" ", strip=True))
                if not price_eur:
                    continue

                if price_eur < MIN_LISTING_PRICE_EUR or price_eur > MAX_LISTING_PRICE_EUR:
                    continue

                # Detalii structurate din card: 'Hatchback | 2011 | 265.000 km | 1.400 cmc | benzină'
                info_el = card.find("div", class_="info_details")
                info_text = info_el.get_text(" | ", strip=True) if info_el else ""

                year = 0
                mileage = 0
                fuel = "Necunoscut"

                # Extragere An
                year_match = re.search(r"\b(19\d\d|20\d\d)\b", info_text)
                if year_match:
                    year = int(year_match.group(1))

                # Extragere KM
                mileage = parse_km(info_text)

                # Combustibil din card
                info_lower = info_text.lower()
                if "diesel" in info_lower:
                    fuel = "Diesel"
                elif "benzin" in info_lower:
                    fuel = "Benzina"
                elif "hibrid" in info_lower or "hybrid" in info_lower:
                    fuel = "Hybrid"
                elif "electric" in info_lower:
                    fuel = "Electric"
                elif "gpl" in info_lower:
                    fuel = "GPL"

                # Parsing marca & model via TitleParser
                parsed_meta = TitleParser.parse(title)
                detected_make = parsed_meta["make"]
                detected_model = parsed_meta["model"]

                if year == 0 and parsed_meta["year"] > 0:
                    year = parsed_meta["year"]

                if fuel == "Necunoscut" and parsed_meta["fuel"] != "necunoscut":
                    fuel = parsed_meta["fuel"].capitalize()

                # Locatie
                loc_el = card.find("span", class_="location")
                city = loc_el.get_text(" ", strip=True) if loc_el else "Romania"

                # Poza
                img_el = card.find("img")
                photo_url = img_src(img_el)

                external_id = f"carzz_{hashlib.md5(clean_url.encode('utf-8')).hexdigest()[:16]}"

                listings.append({
                    "external_id": external_id,
                    "source": "CarZZ.ro",
                    "title": title,
                    "url": clean_url,
                    "price_eur": price_eur,
                    "make": detected_make,
                    "model": detected_model,
                    "year": year,
                    "mileage": mileage,
                    "fuel": fuel,
                    "transmission": "Automata" if any(x in title.lower() for x in ["automat", "dsg", "automatic"]) else "Manuala",
                    "city": city,
                    "seller_type": "private",
                    "seller_phone": "",
                    "photo_url": photo_url,
                    "description": title,
                })

        except Exception as e:
            print(f"[CarZZ Scraper Error] {e}")

        return listings
