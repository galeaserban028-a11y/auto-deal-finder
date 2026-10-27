"""
Ultra-Precise Market Comparison Engine v4 — Hardcore Samsar Edition
==================================================================
Gandit ca un samsar profesionist de top din Romania:
1. Mapare STRICTA pe Generatii (Golf 6 nu se compara niciodata cu Golf 7!).
2. Filtru Anti-Km-Fraud (Nu umfla pretul de revanzare pentru km putini la masini vechi!).
3. Floor Price realist de lichidare rapida in 24-48 ore (Percentila 15 - reducere stradala cash).
4. Calcul profit net dupa scaderea cheltuielilor (BUFFER_EXPENSES_EUR din .env).
"""

import re
import json
import time
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Tuple, Optional

from config.settings import (
    BUFFER_EXPENSES_EUR,
    IMPORT_EXTRA_COST_EUR,
    MIN_NET_PROFIT_EUR,
    MIN_DISCOUNT_PERCENT,
    CURRENT_YEAR,
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ro-RO,ro;q=0.9",
}

_MARKET_CACHE: Dict[str, Dict] = {}
_CACHE_TTL = 1800  # 30 min

# ============================================================================
# BAZA DE DATE DE GENERATII PENTRU CELE MAI LICHIDE MODELE (EVITA ERORILE DE AN)
# ============================================================================
GENERATION_MAP = {
    # Volkswagen
    ("volkswagen", "golf"): [
        ("golf-5", 2004, 2008, 1400),
        ("golf-6", 2009, 2012, 2600),
        ("golf-7", 2013, 2019, 4800),
        ("golf-8", 2020, 2026, 11000),
    ],
    ("volkswagen", "passat"): [
        ("passat-b6", 2005, 2010, 1500),
        ("passat-b7", 2011, 2014, 3500),
        ("passat-b8", 2015, 2023, 6800),
    ],
    ("volkswagen", "tiguan"): [
        ("tiguan-1", 2007, 2015, 3500),
        ("tiguan-2", 2016, 2023, 9800),
    ],
    ("volkswagen", "polo"): [
        ("polo-4", 2002, 2008, 900),
        ("polo-5", 2009, 2017, 2500),
        ("polo-6", 2018, 2026, 6200),
    ],
    ("volkswagen", "touran"): [
        ("touran-1", 2003, 2015, 1500),
        ("touran-2", 2016, 2024, 6800),
    ],

    # Skoda
    ("skoda", "octavia"): [
        ("octavia-2", 2004, 2012, 1500),
        ("octavia-3", 2013, 2019, 4400),
        ("octavia-4", 2020, 2026, 10500),
    ],
    ("skoda", "superb"): [
        ("superb-2", 2008, 2015, 3000),
        ("superb-3", 2016, 2023, 7800),
    ],
    ("skoda", "rapid"): [
        ("rapid", 2012, 2019, 3200),
    ],
    ("skoda", "fabia"): [
        ("fabia-2", 2007, 2014, 1400),
        ("fabia-3", 2015, 2021, 3800),
    ],

    # Audi
    ("audi", "a4"): [
        ("a4-b7", 2004, 2007, 1600),
        ("a4-b8", 2008, 2015, 3600),
        ("a4-b9", 2016, 2023, 9000),
    ],
    ("audi", "a3"): [
        ("a3-8p", 2004, 2012, 1600),
        ("a3-8v", 2013, 2019, 6200),
        ("a3-8y", 2020, 2026, 12500),
    ],
    ("audi", "a6"): [
        ("a6-c6", 2005, 2010, 2000),
        ("a6-c7", 2011, 2017, 6500),
        ("a6-c8", 2018, 2024, 15000),
    ],
    ("audi", "q5"): [
        ("q5-8r", 2008, 2016, 5500),
        ("q5-fy", 2017, 2024, 14000),
    ],

    # BMW
    ("bmw", "seria-3"): [
        ("seria-3-e90", 2005, 2011, 2000),
        ("seria-3-f30", 2012, 2018, 5800),
        ("seria-3-g20", 2019, 2026, 14000),
    ],
    ("bmw", "seria-5"): [
        ("seria-5-e60", 2004, 2009, 2200),
        ("seria-5-f10", 2010, 2016, 6000),
        ("seria-5-g30", 2017, 2023, 15000),
    ],
    ("bmw", "seria-1"): [
        ("seria-1-e87", 2004, 2011, 1600),
        ("seria-1-f20", 2012, 2018, 4800),
        ("seria-1-f40", 2019, 2025, 12000),
    ],
    ("bmw", "x3"): [
        ("x3-e83", 2004, 2010, 2200),
        ("x3-f25", 2011, 2017, 6000),
        ("x3-g01", 2018, 2024, 15000),
    ],

    # Mercedes-Benz
    ("mercedes-benz", "clasa-c"): [
        ("clasa-c-w203", 2004, 2007, 1800),
        ("clasa-c-w204", 2008, 2014, 4500),
        ("clasa-c-w205", 2015, 2021, 10500),
    ],
    ("mercedes-benz", "c-klasse"): [
        ("clasa-c-w203", 2004, 2007, 1800),
        ("clasa-c-w204", 2008, 2014, 4500),
        ("clasa-c-w205", 2015, 2021, 10500),
    ],
    ("mercedes-benz", "clasa-e"): [
        ("clasa-e-w211", 2004, 2009, 2500),
        ("clasa-e-w212", 2010, 2016, 6800),
        ("clasa-e-w213", 2017, 2023, 15500),
    ],
    ("mercedes-benz", "e-klasse"): [
        ("clasa-e-w211", 2004, 2009, 2500),
        ("clasa-e-w212", 2010, 2016, 6800),
        ("clasa-e-w213", 2017, 2023, 15500),
    ],
    ("mercedes-benz", "clasa-a"): [
        ("clasa-a-w169", 2004, 2012, 1600),
        ("clasa-a-w176", 2013, 2018, 6500),
        ("clasa-a-w177", 2019, 2025, 14000),
    ],
    ("mercedes-benz", "a-klasse"): [
        ("clasa-a-w169", 2004, 2012, 1600),
        ("clasa-a-w176", 2013, 2018, 6500),
        ("clasa-a-w177", 2019, 2025, 14000),
    ],

    # Dacia
    ("dacia", "duster"): [
        ("duster-1", 2010, 2017, 2800),
        ("duster-2", 2018, 2023, 6500),
    ],
    ("dacia", "logan"): [
        ("logan-1", 2004, 2012, 800),
        ("logan-2", 2013, 2020, 2200),
        ("logan-3", 2021, 2026, 5500),
    ],
    ("dacia", "sandero"): [
        ("sandero-1", 2008, 2012, 900),
        ("sandero-2", 2013, 2020, 2400),
        ("sandero-3", 2021, 2026, 5800),
    ],

    # Ford
    ("ford", "focus"): [
        ("focus-2", 2005, 2010, 1100),
        ("focus-3", 2011, 2018, 2800),
        ("focus-4", 2019, 2026, 7000),
    ],
    ("ford", "mondeo"): [
        ("mondeo-4", 2007, 2014, 1800),
        ("mondeo-5", 2015, 2022, 5400),
    ],
    ("ford", "kuga"): [
        ("kuga-1", 2008, 2012, 3200),
        ("kuga-2", 2013, 2019, 5800),
        ("kuga-3", 2020, 2025, 11500),
    ],

    # Renault
    ("renault", "megane"): [
        ("megane-2", 2003, 2008, 900),
        ("megane-3", 2009, 2015, 2100),
        ("megane-4", 2016, 2023, 5200),
    ],
    ("renault", "clio"): [
        ("clio-3", 2005, 2012, 1100),
        ("clio-4", 2013, 2019, 3000),
        ("clio-5", 2020, 2026, 6800),
    ],

    # Opel
    ("opel", "astra"): [
        ("astra-h", 2004, 2009, 1000),
        ("astra-j", 2010, 2015, 2400),
        ("astra-k", 2016, 2021, 4600),
    ],
    ("opel", "insignia"): [
        ("insignia-a", 2009, 2016, 2500),
        ("insignia-b", 2017, 2022, 6800),
    ],

    # Hyundai & Kia
    ("hyundai", "tucson"): [
        ("tucson-1", 2005, 2009, 2000),
        ("tucson-ix35", 2010, 2015, 4400),
        ("tucson-3", 2016, 2020, 8800),
        ("tucson-4", 2021, 2026, 15000),
    ],
    ("kia", "sportage"): [
        ("sportage-2", 2005, 2009, 2000),
        ("sportage-3", 2010, 2015, 4400),
        ("sportage-4", 2016, 2021, 8800),
        ("sportage-5", 2022, 2026, 16000),
    ],
    ("kia", "ceed"): [
        ("ceed-1", 2006, 2012, 1400),
        ("ceed-2", 2013, 2018, 3600),
        ("ceed-3", 2019, 2025, 8200),
    ],
}


def normalize_make_model(make: str, model: str) -> Tuple[str, str]:
    """Aduce marca/modelul la forma folosita de Autovit si de GENERATION_MAP."""
    make = (make or "").lower().strip()
    model = (model or "").lower().strip()
    if make in ("vw", "volks"):
        make = "volkswagen"
    elif make in ("mercedes", "mercedes benz", "mercedes-benz", "merc"):
        make = "mercedes-benz"
        for letter in ("a", "b", "c", "e"):
            if model in (letter, f"{letter}-klasse", f"clasa {letter}", f"{letter} class", f"{letter}-class", f"{letter} klasse"):
                model = f"clasa-{letter}"
    elif make == "bmw":
        m = re.fullmatch(r"(?:seria|series)[\s-]*([1-8])|([1-8])-series|([1-8])er", model)
        if m:
            model = f"seria-{next(g for g in m.groups() if g)}"
        elif re.fullmatch(r"[1-8]\d{2}[a-z]{0,2}", model):  # 320d, 520, 118i -> seria-X
            model = f"seria-{model[0]}"
    model = model.replace(" ", "-")
    return make, model


def get_generation_boundary(make: str, model: str, year: int) -> Tuple[str, int, int, float]:
    """
    Gaseste generatia exacta a masinii, limitele ei de ani si pragul minim absolut de pret (EUR).
    Daca nu este in baza de date, foloseste o fereastra stransa (an-1 la an+1)
    si un prag minim de siguranta bazat pe vechime.
    """
    clean_make = make.lower().strip()
    clean_model = model.lower().strip()

    generations = GENERATION_MAP.get((clean_make, clean_model))
    if generations:
        for entry in generations:
            gen_name, y_start, y_end = entry[0], entry[1], entry[2]
            min_floor = float(entry[3]) if len(entry) > 3 else 1500.0
            if y_start <= year <= y_end:
                return gen_name, y_start, y_end, min_floor
        # Daca e in afara limitelor cunoscute, gasim cea mai apropiata
        closest = min(generations, key=lambda g: min(abs(year - g[1]), abs(year - g[2])))
        min_floor = float(closest[3]) if len(closest) > 3 else 1500.0
        return closest[0], closest[1], closest[2], min_floor

    # Fallback conservator bazat pe varsta
    if year >= CURRENT_YEAR - 3:
        default_floor = 10000.0
    elif year >= 2020:
        default_floor = 7500.0
    elif year >= 2016:
        default_floor = 5000.0
    elif year >= 2012:
        default_floor = 3000.0
    elif year >= 2008:
        default_floor = 2000.0
    else:
        default_floor = 1200.0

    return f"{clean_model}-{year}", max(2005, year - 1), min(CURRENT_YEAR, year + 1), default_floor


class PreciseMarketEngine:
    # True daca ultima interogare a pietei a esuat din motive temporare (retea, blocare, 5xx)
    _last_query_failed = False

    @classmethod
    def query_autovit_precise(cls, make: str, model: str, fuel: str, year_from: int, year_to: int) -> List[Dict]:
        """
        Returneaza masinile comparabile active pe Autovit (aceeasi marca/model/generatie, fara daune),
        sortate crescator dupa pret, cu pretul convertit corect in EUR (anunturile in LEI erau
        luate inainte ca EUR, ceea ce umfla pretul pietei de ~5 ori).
        """
        # Import local ca sa evitam importul circular scrapers <-> core
        from scrapers.autovit import AutovitScraper

        make, model = normalize_make_model(make, model)
        fuel = (fuel or "").lower().strip()

        fuel_code = ''
        if 'diesel' in fuel:
            fuel_code = 'diesel'
        elif 'benzin' in fuel or 'petrol' in fuel:
            fuel_code = 'petrol'
        elif 'electric' in fuel:
            fuel_code = 'electric'

        cache_key = f"{make}_{model}_{fuel_code}_{year_from}_{year_to}"
        now = time.time()

        cls._last_query_failed = False
        if cache_key in _MARKET_CACHE:
            entry = _MARKET_CACHE[cache_key]
            if now - entry['timestamp'] < _CACHE_TTL:
                return entry['data']

        url = (
            f"https://www.autovit.ro/autoturisme/{make}/{model}?"
            f"search[order]=filter_float_price:asc&"
            f"search[filter_float_year:from]={year_from}&"
            f"search[filter_float_year:to]={year_to}&"
            f"search[filter_enum_damaged]=0"
        )
        if fuel_code:
            url += f"&search[filter_enum_fuel_type][0]={fuel_code}"

        try:
            response = requests.get(url, headers=HEADERS, timeout=12)
            if response.status_code == 404:
                # Model inexistent pe Autovit: memoram rezultatul gol ca sa nu reinterogam la fiecare ciclu
                _MARKET_CACHE[cache_key] = {'timestamp': now, 'data': []}
                return []
            if response.status_code != 200:
                cls._last_query_failed = True
                return []

            data_str = None
            m = re.search(r'<script\s+id="__NEXT_DATA__"[^>]*>(.*?)</script>', response.text, re.DOTALL)
            if m:
                data_str = m.group(1)
            else:
                soup = BeautifulSoup(response.text, 'html.parser')
                next_data_tag = soup.find('script', id='__NEXT_DATA__')
                if next_data_tag and next_data_tag.string:
                    data_str = next_data_tag.string

            if not data_str:
                cls._last_query_failed = True
                return []

            data = json.loads(data_str)
            urql_state = data.get('props', {}).get('pageProps', {}).get('urqlState', {})

            nodes = []
            for _, value in urql_state.items():
                raw = value.get('data') if isinstance(value, dict) else None
                if not raw:
                    continue
                try:
                    parsed_data = json.loads(raw)
                except (TypeError, ValueError):
                    continue
                search = parsed_data.get('advertSearch') or {}
                for edge in search.get('edges', []):
                    item = AutovitScraper._parse_node(edge.get('node') or {})
                    if not item or item.get('price_eur', 0) <= 0:
                        continue
                    nodes.append({
                        'price': float(item['price_eur']),
                        'year': item.get('year'),
                        'mileage': item.get('mileage') or 0,
                        'fuel': item.get('fuel'),
                        'url': item.get('url'),
                        'external_id': item.get('external_id'),
                    })
                if nodes:
                    break

            sorted_nodes = sorted(nodes, key=lambda x: x['price'])
            _MARKET_CACHE[cache_key] = {'timestamp': now, 'data': sorted_nodes}
            return sorted_nodes

        except Exception as e:
            cls._last_query_failed = True
            print(f"[LiveMarket Autovit Error] {type(e).__name__}: {e}")
            return []

    @staticmethod
    def _exclude_self(listings: List[Dict], url: str, external_id: str) -> List[Dict]:
        """Scoate anuntul evaluat din lista de comparabile (altfel se compara cu el insusi)."""
        clean_url = (url or "").split("?")[0].rstrip("/")
        out = []
        for n in listings:
            n_url = (n.get('url') or "").split("?")[0].rstrip("/")
            if clean_url and n_url == clean_url:
                continue
            if external_id and n.get('external_id') == external_id:
                continue
            out.append(n)
        return out

    @staticmethod
    def _mileage_matched(listings: List[Dict], mileage: int) -> List[Dict]:
        """
        Pastreaza doar comparabilele cu rulaj similar sau MAI MARE (cel mult cu 40.000 km sub).
        Astfel o masina cu 250.000 km nu este evaluata la pretul uneia cu 120.000 km.
        Daca raman prea putine (<5), se foloseste toata generatia (comportamentul vechi).
        """
        if not mileage or mileage <= 0:
            return listings
        matched = [n for n in listings if (n.get('mileage') or 0) >= mileage - 40000]
        return matched if len(matched) >= 5 else listings

    @classmethod
    def evaluate(cls, listing_price: float, make: str, model: str, fuel: str = "", year: int = 0,
                 mileage: int = 0, source: str = "", url: str = "", external_id: str = "") -> Dict:
        """
        Evalueaza pontul ca un flipper profesionist:
        - Determina generatia exacta a masinii
        - Compara doar cu masini din aceeasi generatie, cu rulaj similar sau mai mare
        - Exclude anuntul insusi din comparatie
        - Calculeaza marja neta (include transport platforma pt import)
        - Respecta pragurile MIN_NET_PROFIT_EUR / MIN_DISCOUNT_PERCENT din .env
        """
        make, model = normalize_make_model(make, model)
        fuel = (fuel or "").strip().lower()
        try:
            listing_price = float(listing_price or 0)
        except (TypeError, ValueError):
            listing_price = 0.0

        if not make or make in ("necunoscut", "") or not model or model in ("necunoscut", "auto", ""):
            return {'listing_price': listing_price, 'is_deal': False, 'deal_rating': 'MODEL NECUNOSCUT', 'total_comparable': 0}

        if not year or year < 2000:
            return {'listing_price': listing_price, 'is_deal': False, 'deal_rating': 'AN NECUNOSCUT', 'total_comparable': 0}

        if listing_price <= 0:
            return {'listing_price': listing_price, 'is_deal': False, 'deal_rating': 'PRET INVALID', 'total_comparable': 0}

        # 1. Izolare pe Generatie Exacta (Fara poluare cross-generation!)
        gen_name, year_from, year_to, min_floor_eur = get_generation_boundary(make, model, year)

        # 1b. FILTRU HARD FLOOR (elimina erorile de valuta RON/EUR si avansurile deghizate)
        if listing_price < (min_floor_eur * 0.70):
            return {
                'listing_price': listing_price,
                'is_deal': False,
                'deal_rating': 'SUSPECT FRAUDA',
                'generation': gen_name,
                'total_comparable': 0,
                'net_profit': 0.0,
                'reason': f'Pret imposibil ({listing_price:.0f}€ sub 70% din minimul generatiei {min_floor_eur:.0f}€)'
            }

        # 2. Interogare masini comparabile (fara anuntul insusi).
        # Comparam intai cu masini de AN APROPIAT (±1 an, in aceeasi generatie): pe Autovit cele mai ieftine
        # masini dintr-o generatie sunt aproape mereu cele mai vechi (ex: Golf 7 din 2013 cu 250.000 km),
        # iar un Golf 7 din 2017 comparat cu ele parea "la pret de piata" desi era un pont.
        # Daca nu sunt destule, largim treptat: fara filtru de combustibil, apoi toata generatia.
        near_from, near_to = max(year_from, year - 1), min(year_to, year + 1)
        attempts = [(fuel, near_from, near_to), ("", near_from, near_to), (fuel, year_from, year_to), ("", year_from, year_to)]
        listings: List[Dict] = []
        any_failed = False
        for q_fuel, q_from, q_to in attempts:
            listings = cls._exclude_self(cls.query_autovit_precise(make, model, q_fuel, q_from, q_to), url, external_id)
            any_failed = any_failed or cls._last_query_failed
            if len(listings) >= 5:
                break
        cls._last_query_failed = any_failed and not listings

        market_unavailable = not listings and cls._last_query_failed
        listings = cls._mileage_matched(listings, int(mileage or 0))

        if len(listings) < 3:
            return {
                'listing_price': listing_price,
                'is_deal': False,
                'deal_rating': 'PIATA INDISPONIBILA' if market_unavailable else 'INSUFICIENTE DATE',
                'market_unavailable': market_unavailable,
                'generation': gen_name,
                'total_comparable': len(listings)
            }

        sorted_prices = sorted(n['price'] for n in listings)
        cheapest_price = sorted_prices[0]

        # 3. Safe Sell Price (Lichidare Rapida 48h) = Percentila 15 a pietei din aceeasi generatie
        idx = max(1, int(len(sorted_prices) * 0.15))
        base_floor_price = sorted_prices[idx]

        # Pe Autovit preturile sunt in mare parte de dealer; vanzarea rapida cash e cu ~5% sub.
        street_safe_sell_price = round(base_floor_price * 0.95, 2)

        # 4. Calcul Profit Net Realist
        is_import = any(x in (source or "").lower() for x in ["austria", "willhaben", "autoscout", "germania"])
        total_expenses = BUFFER_EXPENSES_EUR + (IMPORT_EXTRA_COST_EUR if is_import else 0.0)

        price_gap = round(street_safe_sell_price - listing_price, 2)
        net_profit = round(price_gap - total_expenses, 2)

        pct_below = round((price_gap / street_safe_sell_price) * 100, 1) if street_safe_sell_price > 0 else 0.0
        pct_below_cheapest = round(((cheapest_price - listing_price) / cheapest_price) * 100, 1) if cheapest_price > 0 else 0.0

        # 5. Rating de Deal
        # Peste ~35% (import) / 45% (Romania) sub piata = aproape sigur teapa sau dauna ascunsa.
        max_discount_threshold = 35.0 if is_import else 45.0
        unicorn_profit = max(1500.0, MIN_NET_PROFIT_EUR * 1.5)
        unicorn_pct = max(18.0, MIN_DISCOUNT_PERCENT * 1.5)

        is_deal = False
        if pct_below > max_discount_threshold:
            deal_rating = "SUSPECT FRAUDA"
        elif net_profit >= unicorn_profit and pct_below >= unicorn_pct:
            is_deal = True
            deal_rating = "UNICORN"
        elif net_profit >= MIN_NET_PROFIT_EUR and pct_below >= MIN_DISCOUNT_PERCENT:
            is_deal = True
            deal_rating = "PONT REAL"
        elif net_profit >= MIN_NET_PROFIT_EUR * 0.5 and pct_below >= MIN_DISCOUNT_PERCENT * 0.5:
            deal_rating = "MARGINAL (Marja Prea Mica)"
        else:
            deal_rating = "FARA MARJA"

        return {
            'listing_price': listing_price,
            'generation': gen_name,
            'cheapest_on_market': cheapest_price,
            'safe_sell_price': street_safe_sell_price,
            'total_comparable': len(listings),
            'market_prices_sample': sorted_prices[:8],
            'price_gap': price_gap,
            'pct_below_cheapest': pct_below_cheapest,
            'pct_below_safe_sell': pct_below,
            'buffer_expenses': BUFFER_EXPENSES_EUR,
            'total_expenses': total_expenses,
            'is_import': is_import,
            'net_profit': net_profit,
            'is_deal': is_deal,
            'deal_rating': deal_rating
        }


# Alias for backward compatibility
UltraStrictProfitEngine = PreciseMarketEngine
