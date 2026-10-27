"""
Publi24.ro Scraper (Actualizat si Testat pe structura HTML curenta)
Extrage anunturi auto proaspete de la proprietari particulari din Romania.
"""

import re
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import hashlib
from core.utils import parse_price_eur, parse_km, img_src
from core.title_parser import TitleParser

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ro-RO,ro;q=0.9",
}


class Publi24Scraper:
    BASE_URL = "https://www.publi24.ro/anunturi/auto-moto/masini-second-hand/"

    @classmethod
    def fetch_latest_listings(cls, max_items: int = 30) -> List[Dict]:
        listings = []
        try:
            response = requests.get(cls.BASE_URL, headers=HEADERS, timeout=12)
            if response.status_code != 200:
                return listings

            soup = BeautifulSoup(response.text, "html.parser")
            cards = soup.find_all("div", class_="article-content-wrap")

            for card in cards:
                if len(listings) >= max_items:
                    break

                # Cautam linkul cu titlu
                title_a = None
                for a in card.find_all("a", href=True):
                    href = a["href"]
                    text = a.text.strip()
                    if "/anunt/" in href and text:
                        title_a = a
                        break

                if not title_a:
                    continue

                url = title_a["href"]
                if not url.startswith("http"):
                    url = f"https://www.publi24.ro{url}"

                title = title_a.text.strip()

                # Extragere Pret din span.article-price
                price_el = card.find("span", class_="article-price")
                if not price_el:
                    price_el = card.find(class_=lambda c: c and "price" in str(c).lower())

                if not price_el:
                    continue

                price_eur = parse_price_eur(price_el.get_text(" ", strip=True))
                if not price_eur:
                    continue

                # Extragere exacta An, Combustibil si KM din structura cardului Publi24
                # (Ex: '| 2010 | diesel | 279508 km |')
                card_text = card.get_text(" | ", strip=True)
                year = 0
                mileage = 0
                card_fuel = ""

                p24_match = re.search(r"\|\s*(19\d\d|20\d\d)\s*\|\s*([a-zăîșț+ ]+?)\s*\|\s*(\d{1,3}(?:[\.\s]\d{3})+|\d+)\s*km\b", card_text, re.IGNORECASE)
                if p24_match:
                    year = int(p24_match.group(1))
                    card_fuel = p24_match.group(2).strip().lower()
                    clean_km = re.sub(r"\D", "", p24_match.group(3))
                    if clean_km.isdigit():
                        mileage = int(clean_km)
                else:
                    # Fallback: extragere KM separat (fara an - anul se ia DOAR din TitleParser)
                    mileage = parse_km(f"{title} {card_text}")

                # Identificare inteligenta marca, model, an, combustibil via TitleParser
                url_and_title = f"{url} {title}".lower()
                parsed_meta = TitleParser.parse(title)

                detected_make = parsed_meta["make"]
                detected_model = parsed_meta["model"]
                if year == 0 and parsed_meta["year"] > 0:
                    year = parsed_meta["year"]

                if card_fuel and "diesel" in card_fuel:
                    detected_fuel = "Diesel"
                elif card_fuel and ("benzin" in card_fuel or "petrol" in card_fuel):
                    detected_fuel = "Benzina"
                elif card_fuel and ("hibrid" in card_fuel or "hybrid" in card_fuel):
                    detected_fuel = "Hybrid"
                elif card_fuel and "electric" in card_fuel:
                    detected_fuel = "Electric"
                elif parsed_meta["fuel"] != "necunoscut":
                    detected_fuel = parsed_meta["fuel"].capitalize()
                else:
                    detected_fuel = "Diesel" if any(x in url_and_title for x in ["diesel", "tdi", "dci", "cdti"]) else "Benzina"

                img_el = card.find("img")
                photo_url = img_src(img_el)

                external_id = f"publi24_{hashlib.md5(url.encode('utf-8')).hexdigest()[:16]}"

                listings.append({
                    "external_id": external_id,
                    "source": "Publi24.ro",
                    "title": title,
                    "url": url,
                    "price_eur": price_eur,
                    "make": detected_make,
                    "model": detected_model,
                    "year": year,
                    "mileage": mileage,
                    "fuel": detected_fuel,
                    "transmission": "Automata" if any(x in url_and_title for x in ["automat", "automatic", "dsg"]) else "Manuala",
                    "city": "Romania",
                    "seller_type": "private",
                    "seller_phone": "",
                    "photo_url": photo_url,
                    "description": f"{title} - Anunt Publi24 proprietar"
                })

        except Exception as e:
            print(f"[Publi24 Scraper Error] {e}")

        return listings
