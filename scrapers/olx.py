"""
OLX.ro Scraper (folosind conexiune securizata prin curl)
Extrage anunturi auto proaspete direct de la particulari de pe OLX Romania.
"""

import sys
import re
import subprocess
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from core.utils import parse_price_eur, parse_km, img_src
from core.title_parser import TitleParser
import hashlib

CURL_BIN = "curl.exe" if sys.platform == "win32" else "curl"


class OLXScraper:
    BASE_URL = "https://www.olx.ro/auto-masini-moto-ambarcatiuni/autoturisme/"

    @classmethod
    def fetch_latest_listings(cls, max_items: int = 40) -> List[Dict]:
        listings = []
        try:
            cmd = [
                CURL_BIN, "-s", "-A",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                cls.BASE_URL
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
            if res.returncode != 0 or not res.stdout:
                return listings

            html = res.stdout.decode("utf-8", errors="ignore")
            soup = BeautifulSoup(html, "html.parser")
            cards = soup.find_all("div", {"data-cy": "l-card"})

            for card in cards:
                if len(listings) >= max_items:
                    break

                # Link si Titlu
                link_el = card.find("a", href=True)
                if not link_el or "/d/oferta/" not in link_el["href"]:
                    continue

                href = link_el["href"]
                url = href if href.startswith("http") else f"https://www.olx.ro{href}"
                # Curatare parametri de tracking din URL
                clean_url = url.split("?")[0]

                title_el = card.find("h4") or card.find("h6")
                title = title_el.text.strip() if title_el else ""
                if not title or len(title) < 5:
                    continue

                # Pret
                price_el = card.find("p", {"data-testid": "ad-price"})
                if not price_el:
                    price_el = card.find(string=re.compile(r"€|lei|EUR", re.I))
                    if price_el:
                        price_el = price_el.parent

                if not price_el:
                    continue

                price_eur = parse_price_eur(price_el.get_text(" ", strip=True))
                if not price_eur:
                    continue

                # Extragere exacta An si KM din textul cardului OLX (ex: "2011  210 651 km")
                card_text = card.get_text(" ", strip=True)
                year = 0
                mileage = 0

                param_match = re.search(r"\b(19\d\d|20\d\d)\s*(?:-\s*)?(\d{1,3}(?:[\s\.]\d{3})+|\d+)\s*km\b", card_text, re.IGNORECASE)
                if param_match:
                    year = int(param_match.group(1))
                    clean_km = re.sub(r"\D", "", param_match.group(2))
                    if clean_km.isdigit():
                        mileage = int(clean_km)

                # Fallback: extragere KM separat (fara an - anul se ia DOAR din TitleParser)
                if mileage == 0:
                    mileage = parse_km(card_text)

                # Fallback: DOAR TitleParser (elimina regex-ul naiv care prindea preturi/date/modele ca an)
                # Identificare inteligenta marca, model, combustibil via TitleParser
                parsed_meta = TitleParser.parse(title)

                detected_make = parsed_meta["make"]
                detected_model = parsed_meta["model"]
                if year == 0 and parsed_meta["year"] > 0:
                    year = parsed_meta["year"]

                detected_fuel = parsed_meta["fuel"].capitalize() if parsed_meta["fuel"] != "necunoscut" else ("Diesel" if any(x in title.lower() for x in ["diesel", "tdi", "dci", "cdti"]) else "Benzina")

                img_el = card.find("img")
                photo_url = img_src(img_el)

                external_id = f"olx_{hashlib.md5(clean_url.encode('utf-8')).hexdigest()[:16]}"

                listings.append({
                    "external_id": external_id,
                    "source": "OLX.ro",
                    "title": title,
                    "url": clean_url,
                    "price_eur": price_eur,
                    "make": detected_make,
                    "model": detected_model,
                    "year": year,
                    "mileage": mileage,
                    "fuel": detected_fuel,
                    "transmission": "Automata" if any(x in title.lower() for x in ["automat", "automatic", "dsg"]) else "Manuala",
                    "city": "Romania",
                    "seller_type": "private",
                    "seller_phone": "",
                    "photo_url": photo_url,
                    "description": title
                })

        except Exception as e:
            print(f"[OLX Scraper Error] {e}")

        return listings
