"""
AutoScout24 Scraper (Germania & Europa)
=======================================
Extrage anunturi auto proaspete din Germania si Europa de pe AutoScout24.
Permite gasirea oportunitatilor de import auto cu preturi mult sub piata din Romania.
"""

import sys
import re
import subprocess
from bs4 import BeautifulSoup
from typing import List, Dict
from config.settings import MIN_LISTING_PRICE_EUR, MAX_LISTING_PRICE_EUR, MAX_MILEAGE_KM
from core.utils import img_src

CURL_BIN = "curl.exe" if sys.platform == "win32" else "curl"


class AutoScout24Scraper:
    BASE_URL = "https://www.autoscout24.ro/lst"

    @classmethod
    def fetch_latest_listings(cls, max_items: int = 25, country_code: str = "D") -> List[Dict]:
        """
        Extrage ultimele anunturi auto din Germania (cy=D) sau din toata Europa.
        """
        listings = []
        try:
            url = (
                f"{cls.BASE_URL}?sort=age&desc=1"
                f"&pricefrom={int(MIN_LISTING_PRICE_EUR)}"
                f"&priceto={int(MAX_LISTING_PRICE_EUR)}"
                f"&kmto={int(MAX_MILEAGE_KM)}"
                f"&cy={country_code}"
                f"&ustate=N%2CU"
            )

            cmd = [
                CURL_BIN, "-s", "-L", "-A",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "-H", "Accept-Language: ro-RO,ro;q=0.9,de-DE,de;q=0.8,en;q=0.7",
                url
            ]

            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
            if res.returncode != 0 or not res.stdout:
                return listings

            html = res.stdout.decode("utf-8", errors="ignore")
            soup = BeautifulSoup(html, "html.parser")
            articles = soup.find_all("article")

            for article in articles:
                if len(listings) >= max_items:
                    break

                guid = article.get("data-guid") or article.get("id")
                if not guid:
                    continue

                make = (article.get("data-make") or "").strip().lower()
                model = (article.get("data-model") or "").strip().lower()

                # Pret
                raw_price = article.get("data-price", "0")
                try:
                    price_eur = float(raw_price)
                except ValueError:
                    continue

                if price_eur < MIN_LISTING_PRICE_EUR or price_eur > MAX_LISTING_PRICE_EUR:
                    continue

                # Kilometraj
                raw_km = article.get("data-mileage", "0")
                try:
                    mileage = int(raw_km)
                except ValueError:
                    mileage = 0
                if mileage > MAX_MILEAGE_KM:
                    continue

                # An fabricatie din data-first-registration (ex: "04-2017")
                reg_date = article.get("data-first-registration", "")
                year = 0
                year_match = re.search(r"\b(19\d\d|20\d\d)\b", reg_date)
                if year_match:
                    year = int(year_match.group(1))

                # Combustibil
                raw_fuel = (article.get("data-fuel-type") or "").strip().lower()
                fuel_map = {
                    "d": "Diesel",
                    "b": "Benzina",
                    "e": "Electric",
                    "h": "Hybrid",
                    "l": "GPL",
                    "c": "GPL",
                }
                fuel = fuel_map.get(raw_fuel, "Necunoscut")

                # Titlu complet din h2
                h2_el = article.find("h2")
                title = h2_el.get_text(" ", strip=True) if h2_el else f"{make.capitalize()} {model.capitalize()}"
                if year and str(year) not in title:
                    title = f"{title} ({year})"

                # Imagine
                img_el = article.find("img")
                photo_url = img_src(img_el)

                # Direct link
                offer_url = f"https://www.autoscout24.ro/oferte/-{guid}"
                if country_code == "D":
                    country_label = "Germania 🇩🇪"
                elif country_code == "A":
                    country_label = "Austria 🇦🇹"
                else:
                    country_label = "Europa 🇪🇺"

                external_id = f"as24_{guid.replace('-', '_')}"

                listings.append({
                    "external_id": external_id,
                    "source": f"AutoScout24 ({country_label})",
                    "title": title,
                    "url": offer_url,
                    "price_eur": price_eur,
                    "make": make,
                    "model": model,
                    "year": year,
                    "mileage": mileage,
                    "fuel": fuel,
                    "transmission": "Manuala",
                    "city": country_label,
                    "seller_type": "dealer" if article.get("data-seller-type") == "d" else "private",
                    "seller_phone": "",
                    "photo_url": photo_url,
                    "description": f"{title} - Import {country_label}",
                })

        except Exception as e:
            print(f"[AutoScout24 Scraper Error] {e}")

        return listings
