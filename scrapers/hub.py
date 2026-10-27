"""
Scraper Hub v3 (Multi-Platform, Targeted Arbitrage & Deep Inspection)
====================================================================
Coordoneaza scanarea inteligenta:
1. ModelScanner: Scaneaza direct cele mai ieftine masini ale celor 15 modele de top din Romania
2. OLX.ro: Extrage anunturi noi de la particulari cu identificare precisa marca/model/an/km
3. Publi24.ro: Extrage anunturi noi cu filtrare precisa
4. Autovit.ro: Ultimele anunturi generale

Sistem de Siguranta pe 2 Niveluri:
- Nivelul 1: Filtru rapid AntiFraudShield pe cardurile din lista
- Nivelul 2 (DEEP INSPECTION): Pentru orice masina calificata ca pont, se descarca
  pagina completa si se inspecteaza descrierea integrala (elimina 100% volan pe dreapta,
  ambreiaj defect, motor defect, necesitati de reparatii ascunse in text).
"""

import re
import sys
import subprocess
import requests
import json
from bs4 import BeautifulSoup
from typing import List, Dict, Tuple

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from scrapers.model_scanner import ModelScanner
from scrapers.autovit import AutovitScraper
from scrapers.olx import OLXScraper
from scrapers.publi24 import Publi24Scraper
from scrapers.carzz import CarZZScraper
from scrapers.autoscout24 import AutoScout24Scraper
from scrapers.willhaben import WillhabenScraper
from core.anti_fraud import AntiFraudShield
from core.live_market import PreciseMarketEngine, GENERATION_MAP, normalize_make_model
from core.ai_inspector import MultiAIInspector
from core.title_parser import TitleParser
from core.db import should_skip_seen, save_listing_and_deal

CURL_BIN = "curl.exe" if sys.platform == "win32" else "curl"


def _normalize_item_model(item: Dict) -> None:
    """
    Unifica marca/modelul intre surse (AutoScout24 trimite 'bmw/320', Autovit 'bmw/seria-3' etc.).
    Daca perechea nu e cunoscuta, incearca sa o deduca din titlu.
    """
    make, model = normalize_make_model(item.get("make", ""), item.get("model", ""))
    if (make, model) not in GENERATION_MAP:
        parsed = TitleParser.parse(item.get("title", ""))
        p_make, p_model = normalize_make_model(parsed.get("make", ""), parsed.get("model", ""))
        if (p_make, p_model) in GENERATION_MAP:
            make, model = p_make, p_model
    if make:
        item["make"] = make
    if model:
        item["model"] = model

def check_description_price_conflict(description: str, card_price_eur: float) -> Tuple[bool, str]:
    """
    Verifica daca in descrierea anuntului exista un pret explicit in EUR mult mai mare decat pretul listat.
    Previne capcanele clasice:
    - Vanzatorul a introdus pretul in RON/LEI din greseala (ex. 23.600 LEI -> 4.748€, dar in text scrie 'Pret: 23.600 Euro')
    - Pretul afisat e doar avansul sau o rata
    """
    if not description or card_price_eur <= 0:
        return True, ""

    patterns = [
        r"(?:pret|preț|pretul|prețul|pret\s*fix|la\s*pretul\s*de)\s*[:=\-]?\s*([0-9]{1,2}(?:[\.\s][0-9]{3})+|[0-9]{4,5})\s*(?:euro|eur|€)",
        r"([0-9]{1,2}(?:[\.\s][0-9]{3})+|[0-9]{4,5})\s*(?:euro|eur|€)\s*(?:negociabil|fix|usor\s*negociabil)",
    ]
    for pat in patterns:
        matches = re.finditer(pat, description, re.IGNORECASE)
        for m in matches:
            raw_val = m.group(1).replace(".", "").replace(" ", "").strip()
            try:
                found_price = float(raw_val)
                if found_price >= 1500 and found_price > (card_price_eur * 1.45):
                    return False, f"Pret real in descriere ({found_price:,.0f}€) vs anunt ({card_price_eur:,.0f}€) - eroare RON/EUR sau avans ascuns"
            except ValueError:
                pass
    return True, ""


def fetch_full_description(url: str, source: str) -> str:
    """Descarca pagina integrala a anuntului pentru inspectie avansata a textului."""
    try:
        if "olx" in source.lower() or "olx.ro" in url:
            cmd = [CURL_BIN, '-s', '-L', '-m', '12', '-A', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36', url]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
            if res.returncode == 0 and res.stdout:
                html = res.stdout.decode('utf-8', errors='ignore')
                soup = BeautifulSoup(html, 'html.parser')
                desc_el = soup.find('div', {'data-cy': 'ad_description'}) or soup.find(id='textContent')
                if desc_el:
                    return desc_el.get_text(" ", strip=True)
                return soup.get_text(" ", strip=True)[:3000]

        elif "autovit" in source.lower() or "autovit.ro" in url:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            r = requests.get(url, headers=headers, timeout=12)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, 'html.parser')
                script = soup.find('script', id='__NEXT_DATA__')
                if script and script.string:
                    data = json.loads(script.string)
                    advert = data.get('props', {}).get('pageProps', {}).get('advert', {})
                    if advert and advert.get('description'):
                        return BeautifulSoup(advert.get('description'), 'html.parser').get_text(" ", strip=True)
                desc_el = soup.find('div', {'data-testid': 'ad-description'})
                if desc_el:
                    return desc_el.get_text(" ", strip=True)
                return soup.get_text(" ", strip=True)[:3000]

        elif "publi24" in source.lower() or "publi24.ro" in url:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            r = requests.get(url, headers=headers, timeout=12)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, 'html.parser')
                desc_el = soup.find('div', class_=lambda c: c and 'article-description' in c) or soup.find(itemprop='description')
                if desc_el:
                    return desc_el.get_text(" ", strip=True)
                return soup.get_text(" ", strip=True)[:3000]

        elif "carzz" in source.lower() or "carzz.ro" in url:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            r = requests.get(url, headers=headers, timeout=12)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, 'html.parser')
                desc_el = soup.find(itemprop='description') or soup.find(id='paragraph') or soup.find('div', class_='description_area_gad')
                if desc_el:
                    return desc_el.get_text(" ", strip=True)
                return soup.get_text(" ", strip=True)[:3000]

        elif "autoscout24" in source.lower() or "autoscout24" in url:
            cmd = [CURL_BIN, '-s', '-L', '-m', '12', '-A', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36', url]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=12)
            if res.returncode == 0 and res.stdout:
                html = res.stdout.decode('utf-8', errors='ignore')
                soup = BeautifulSoup(html, 'html.parser')
                desc_el = soup.find('div', {'data-testid': 'description-container'}) or soup.find('div', class_=lambda c: c and 'description' in str(c).lower())
                if desc_el:
                    return desc_el.get_text(" ", strip=True)
                return soup.get_text(" ", strip=True)[:3000]

        elif "willhaben" in source.lower() or "willhaben.at" in url:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            r = requests.get(url, headers=headers, timeout=12)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, 'html.parser')
                script = soup.find('script', id='__NEXT_DATA__')
                if script and script.string:
                    data = json.loads(script.string)
                    details = data.get('props', {}).get('pageProps', {}).get('advertDetails', {})
                    if details and details.get('description'):
                        return details.get('description')
                desc_el = soup.find('div', {'data-testid': 'ad-detail-description'}) or soup.find('div', class_=lambda c: c and 'description' in str(c).lower())
                if desc_el:
                    return desc_el.get_text(" ", strip=True)
                return soup.get_text(" ", strip=True)[:3000]
    except Exception as e:
        print(f"      [EROARE FETCH DESCRIERE] {url}: {e}")
    return ""


class ScraperHub:
    @classmethod
    def scan_all(cls, max_pages: int = 1) -> Dict:
        raw_listings = []

        # 1. Model Scanner: Targeteaza direct cele mai ieftine masini din modelele lichide
        print("[Hub] 1/8 Scanare TARGETATA pe Modele Lichide (cele mai ieftine de pe piata)...")
        try:
            bargain_items = ModelScanner.scan_liquid_bargains(max_per_model=3, min_year=2010)
            raw_listings.extend(bargain_items)
            print(f"      -> {len(bargain_items)} masini cu potential din modele de top.")
        except Exception as e:
            print(f"      -> Eroare ModelScanner: {e}")

        # 2. OLX.ro (Particulari Romania)
        print("[Hub] 2/8 Scanare OLX.ro (particulari)...")
        try:
            olx_items = OLXScraper.fetch_latest_listings(max_items=35)
            raw_listings.extend(olx_items)
            print(f"      -> {len(olx_items)} anunturi de pe OLX.")
        except Exception as e:
            print(f"      -> Eroare OLX: {e}")

        # 3. Autovit.ro (Ultimele anunturi generale)
        print("[Hub] 3/8 Scanare Autovit.ro (anunturi proaspete)...")
        try:
            autovit_count = 0
            for page in range(1, max_pages + 1):
                autovit_items = AutovitScraper.fetch_latest_listings(page=page)
                raw_listings.extend(autovit_items)
                autovit_count += len(autovit_items)
            print(f"      -> {autovit_count} anunturi noi de pe Autovit.")
        except Exception as e:
            print(f"      -> Eroare Autovit: {e}")

        # 4. Publi24.ro
        print("[Hub] 4/8 Scanare Publi24.ro...")
        try:
            publi24_items = Publi24Scraper.fetch_latest_listings(max_items=25)
            raw_listings.extend(publi24_items)
            print(f"      -> {len(publi24_items)} anunturi de pe Publi24.")
        except Exception as e:
            print(f"      -> Eroare Publi24: {e}")

        # 5. CarZZ.ro (Portal dedicat auto din Romania)
        print("[Hub] 5/8 Scanare CarZZ.ro (chilipiruri de la particulari)...")
        try:
            carzz_items = CarZZScraper.fetch_latest_listings(max_items=35)
            raw_listings.extend(carzz_items)
            print(f"      -> {len(carzz_items)} anunturi noi de pe CarZZ.ro.")
        except Exception as e:
            print(f"      -> Eroare CarZZ: {e}")

        # 6. AutoScout24 (Germania - Import chilipiruri)
        print("[Hub] 6/8 Scanare AutoScout24 (Germania - oportunitati de import)...")
        try:
            as24_items = AutoScout24Scraper.fetch_latest_listings(max_items=25, country_code="D")
            raw_listings.extend(as24_items)
            print(f"      -> {len(as24_items)} anunturi noi de import din Germania.")
        except Exception as e:
            print(f"      -> Eroare AutoScout24 Germania: {e}")

        # 7. Willhaben.at (Austria 🇦🇹 - Platforma #1 de chilipiruri din Austria)
        print("[Hub] 7/8 Scanare Willhaben.at (Austria 🇦🇹 - particulari & chilipiruri locale)...")
        try:
            willhaben_items = WillhabenScraper.fetch_latest_listings(max_items=30)
            raw_listings.extend(willhaben_items)
            print(f"      -> {len(willhaben_items)} anunturi noi din Austria (Willhaben).")
        except Exception as e:
            print(f"      -> Eroare Willhaben Austria: {e}")

        # 8. AutoScout24 (Austria 🇦🇹 - oportunitati de import)
        print("[Hub] 8/8 Scanare AutoScout24 (Austria 🇦🇹 - oportunitati de import)...")
        try:
            as24_at_items = AutoScout24Scraper.fetch_latest_listings(max_items=25, country_code="A")
            raw_listings.extend(as24_at_items)
            print(f"      -> {len(as24_at_items)} anunturi noi din Austria (AutoScout24).")
        except Exception as e:
            print(f"      -> Eroare AutoScout24 Austria: {e}")

        print(f"\n[Hub] Total: {len(raw_listings)} anunturi colectate din 8 surse (Romania + Germania + Austria). Incepe filtrarea de precizie...")

        new_deals = []
        rejected_count = 0
        already_seen_count = 0
        retry_later_count = 0
        processed_ids = set()

        for item in raw_listings:
            ext_id = item.get("external_id")
            # Acelasi anunt poate veni din 2 surse in acelasi ciclu (ex: ModelScanner + Autovit)
            if not ext_id or ext_id in processed_ids:
                already_seen_count += 1
                continue
            processed_ids.add(ext_id)

            price_eur = item.get("price_eur", 0.0) or 0.0
            # Sarim peste anunturile deja procesate, DAR re-evaluam daca pretul a scazut
            if should_skip_seen(ext_id, price_eur):
                already_seen_count += 1
                continue

            _normalize_item_model(item)
            make = item.get("make", "")
            model = item.get("model", "")
            year = item.get("year", 0) or 0
            mileage = item.get("mileage", 0) or 0
            fuel = item.get("fuel", "")

            # 1. Filtru Rapid AntiFraudShield (Scut Nivel 1)
            is_safe, safety_reason = AntiFraudShield.inspect(
                title=item.get("title", ""),
                description=item.get("description", ""),
                price_eur=price_eur,
                mileage=mileage,
                make=make,
                model=model,
                year=year,
            )
            item["is_safe"] = is_safe
            item["safety_reason"] = safety_reason

            if not is_safe:
                rejected_count += 1
                save_listing_and_deal(item, {"is_deal": False})
                continue

            # Verificare rigida: marca, model si an obligatorii
            if not make or make in ("necunoscut", "") or not model or model in ("necunoscut", "auto", ""):
                save_listing_and_deal(item, {"is_deal": False})
                continue

            if not year or year < 2000:
                save_listing_and_deal(item, {"is_deal": False})
                continue

            # 2. Evaluare: compara cu masini din aceeasi generatie (fara anuntul insusi)
            eval_res = PreciseMarketEngine.evaluate(
                listing_price=price_eur,
                make=make,
                model=model,
                fuel=fuel,
                year=year,
                mileage=mileage if mileage > 0 else 180000,
                source=item.get("source", ""),
                url=item.get("url", ""),
                external_id=ext_id,
            )

            if eval_res.get("market_unavailable"):
                # Piata nu a putut fi interogata (Autovit picat / blocat). NU salvam anuntul,
                # ca sa fie re-evaluat la ciclul urmator in loc sa fie pierdut definitiv.
                retry_later_count += 1
                continue

            if not eval_res.get("is_deal"):
                save_listing_and_deal(item, {"is_deal": False})
                continue

            # 3. NIVEL 2: VERIFICARE DETALIATA (Deep Inspection pe pagina integrala)
            full_desc = fetch_full_description(item.get("url", ""), item.get("source", ""))
            if not full_desc:
                # Nu aprobam fara descriere, dar nici nu marcam anuntul ca "vazut":
                # o eroare de retea temporara nu trebuie sa piarda definitiv un pont.
                print(f"      [AMANAT - FARA DESCRIERE] {item.get('title')}: pagina nu s-a putut descarca, se reincearca la ciclul urmator")
                retry_later_count += 1
                continue

            # 3b. Detectie Erori Valuta / Avans ascuns in text
            is_price_ok, price_conflict_reason = check_description_price_conflict(full_desc, price_eur)
            if not is_price_ok:
                print(f"      [RESPINS LA INSPECTIA PAGINII - CONFLICT PRET] {item.get('title')}: {price_conflict_reason}")
                rejected_count += 1
                item["is_safe"], item["safety_reason"] = False, price_conflict_reason
                save_listing_and_deal(item, {"is_deal": False})
                continue

            is_safe_deep, deep_reason = AntiFraudShield.inspect(
                title=item.get("title", ""),
                description=full_desc,
                price_eur=price_eur,
                mileage=mileage,
                make=make,
                model=model,
                year=year,
            )
            if not is_safe_deep:
                print(f"      [RESPINS LA INSPECTIA PAGINII] {item.get('title')}: {deep_reason}")
                rejected_count += 1
                item["is_safe"], item["safety_reason"] = False, deep_reason
                save_listing_and_deal(item, {"is_deal": False})
                continue

            # 4. NIVEL 3: INSPECTIE AI (Gemini / OpenAI) sau verificare locala
            item["description"] = full_desc
            ai_eval = MultiAIInspector.inspect_deal(item)
            if not ai_eval.get("approved"):
                print(f"      [RESPINS DE AI INSPECTOR] {item.get('title')}: {ai_eval.get('ai_summary')} (Scor AI: {ai_eval.get('ai_score')})")
                rejected_count += 1
                item["is_safe"], item["safety_reason"] = False, f"AI: {ai_eval.get('ai_summary')}"
                save_listing_and_deal(item, {"is_deal": False})
                continue

            details = {
                "generation": eval_res.get("generation", ""),
                "cheapest_on_market": eval_res.get("cheapest_on_market", 0),
                "safe_sell_price": eval_res.get("safe_sell_price", 0),
                "market_prices_sample": eval_res.get("market_prices_sample", []),
                "total_comparable": eval_res.get("total_comparable", 0),
                "pct_below_cheapest": eval_res.get("pct_below_cheapest", 0),
                "pct_below_safe_sell": eval_res.get("pct_below_safe_sell", 0),
                "total_expenses": eval_res.get("total_expenses", 0),
                "ai_score": ai_eval.get("ai_score"),
                "ai_summary": ai_eval.get("ai_summary", ""),
                "ai_flags": ai_eval.get("risk_flags", []),
                "ai_model": ai_eval.get("model_used", ""),
            }
            # Semnificatia coloanelor din DB (pastrata compatibila cu baza veche):
            #   median_price = pretul de vanzare rapida (P15 * 0.95)
            #   floor_price  = cel mai ieftin comparabil din piata
            #   discount_pct = % sub pretul de vanzare rapida
            eval_for_db = {
                "is_deal": True,
                "median_price": eval_res.get("safe_sell_price", 0),
                "floor_price": eval_res.get("cheapest_on_market", 0),
                "discount_pct": eval_res.get("pct_below_safe_sell", 0),
                "net_profit": eval_res.get("net_profit", 0),
                "deal_rating": eval_res.get("deal_rating", "STANDARD"),
                "details": details,
            }

            deal_id = save_listing_and_deal(item, eval_for_db)
            if deal_id:
                new_deals.append({**item, **eval_for_db, **details, "deal_id": deal_id})
                print(f"      💎 [PONT CONFIRMAT ({ai_eval.get('model_used')})] {item.get('title')} | Pret: {price_eur} EUR | Profit Net: +{eval_res.get('net_profit')} EUR")

        return {
            "total_scanned": len(raw_listings),
            "already_seen": already_seen_count,
            "rejected_unsafe": rejected_count,
            "new_deals_found": len(new_deals),
            "retry_later": retry_later_count,
            "deals": new_deals
        }
