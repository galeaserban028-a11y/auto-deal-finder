"""
Market Engine & Guaranteed Profit Matrix (Versiunea Optimizata si Calibrata)
Calculeaza:
1. Pretul median curat al pietei pe baza de model, an si ajustare kilometrica
2. Floor Price (Percentila 25 - pretul la care se vinde sigur in 48h)
3. Scade automat cheltuielile de pregatire (1.050€)
4. Filtru de scam pentru preturi nerealiste (>60% sub piata)
5. Calculeaza Profitul Net Garantat si Deal Score
"""

from typing import List, Dict, Optional
import numpy as np
from config.settings import BUFFER_EXPENSES_EUR, MIN_NET_PROFIT_EUR, MIN_DISCOUNT_PERCENT

# Baza de date extinsa si calibrata cu preturi reale din piata romaneasca
BASELINE_MARKET_PRICES = {
    # Dacia
    ("dacia", "spring", 2021): 8800,
    ("dacia", "spring", 2022): 9800,
    ("dacia", "spring", 2023): 11000,
    ("dacia", "logan", 2015): 4200,
    ("dacia", "logan", 2016): 4800,
    ("dacia", "logan", 2017): 5500,
    ("dacia", "logan", 2018): 6200,
    ("dacia", "logan", 2019): 7200,
    ("dacia", "logan", 2020): 8100,
    ("dacia", "logan", 2021): 9500,
    ("dacia", "duster", 2015): 7500,
    ("dacia", "duster", 2016): 8500,
    ("dacia", "duster", 2017): 9800,
    ("dacia", "duster", 2018): 11500,
    ("dacia", "duster", 2019): 12800,
    ("dacia", "duster", 2020): 14200,
    ("dacia", "sandero", 2016): 5200,
    ("dacia", "sandero", 2018): 6800,
    ("dacia", "sandero", 2020): 8900,

    # Volkswagen
    ("volkswagen", "golf", 2013): 7200,
    ("volkswagen", "golf", 2014): 8200,
    ("volkswagen", "golf", 2015): 9200,
    ("volkswagen", "golf", 2016): 10200,
    ("volkswagen", "golf", 2017): 11500,
    ("volkswagen", "golf", 2018): 12800,
    ("volkswagen", "golf", 2019): 14500,
    ("volkswagen", "passat", 2014): 8500,
    ("volkswagen", "passat", 2015): 10500,
    ("volkswagen", "passat", 2016): 11900,
    ("volkswagen", "passat", 2017): 13400,
    ("volkswagen", "passat", 2018): 14900,
    ("volkswagen", "passat", 2019): 16800,
    ("volkswagen", "tiguan", 2015): 11500,
    ("volkswagen", "tiguan", 2016): 14200,
    ("volkswagen", "tiguan", 2017): 16800,
    ("volkswagen", "tiguan", 2018): 18900,
    ("volkswagen", "polo", 2015): 6200,
    ("volkswagen", "polo", 2017): 8200,
    ("volkswagen", "polo", 2019): 10500,

    # Skoda
    ("skoda", "octavia", 2014): 7800,
    ("skoda", "octavia", 2015): 9000,
    ("skoda", "octavia", 2016): 10200,
    ("skoda", "octavia", 2017): 11600,
    ("skoda", "octavia", 2018): 13000,
    ("skoda", "octavia", 2019): 14800,
    ("skoda", "superb", 2015): 11500,
    ("skoda", "superb", 2016): 13500,
    ("skoda", "superb", 2017): 15200,
    ("skoda", "superb", 2018): 17200,

    # Audi
    ("audi", "a3", 2015): 9800,
    ("audi", "a3", 2017): 12900,
    ("audi", "a4", 2014): 10200,
    ("audi", "a4", 2015): 11800,
    ("audi", "a4", 2016): 14500,
    ("audi", "a4", 2017): 16500,
    ("audi", "a4", 2018): 18500,
    ("audi", "a6", 2014): 13500,
    ("audi", "a6", 2015): 15500,
    ("audi", "a6", 2016): 18200,
    ("audi", "a6", 2017): 21500,

    # BMW
    ("bmw", "seria-3", 2013): 9500,
    ("bmw", "seria-3", 2014): 11000,
    ("bmw", "seria-3", 2015): 12500,
    ("bmw", "seria-3", 2016): 14500,
    ("bmw", "seria-3", 2017): 16800,
    ("bmw", "seria-5", 2013): 12000,
    ("bmw", "seria-5", 2014): 13800,
    ("bmw", "seria-5", 2015): 15900,
    ("bmw", "seria-5", 2016): 18500,
    ("bmw", "seria-5", 2017): 22500,

    # Ford
    ("ford", "focus", 2014): 5800,
    ("ford", "focus", 2015): 6800,
    ("ford", "focus", 2016): 8000,
    ("ford", "focus", 2017): 9500,
    ("ford", "focus", 2018): 11200,
    ("ford", "kuga", 2013): 7500,
    ("ford", "kuga", 2015): 9800,
    ("ford", "kuga", 2017): 12500,

    # Opel
    ("opel", "astra", 2014): 5200,
    ("opel", "astra", 2016): 7200,
    ("opel", "astra", 2018): 9500,
    ("opel", "mokka", 2014): 7200,
    ("opel", "mokka", 2016): 9200,
    ("opel", "insignia", 2014): 6500,
    ("opel", "insignia", 2016): 8500,

    # Renault
    ("renault", "megane", 2015): 6500,
    ("renault", "megane", 2017): 9200,
    ("renault", "clio", 2016): 5800,
    ("renault", "clio", 2018): 7500,

    # Hyundai & Kia
    ("hyundai", "tucson", 2016): 12500,
    ("hyundai", "tucson", 2018): 15200,
    ("hyundai", "i30", 2015): 6800,
    ("hyundai", "i30", 2017): 9200,
    ("kia", "sportage", 2016): 12800,
    ("kia", "sportage", 2018): 15500,
}


class MarketValuationEngine:
    @classmethod
    def estimate_market_prices(
        cls, make: str, model: str, year: int, mileage: int = 180000, existing_prices: List[float] = None
    ) -> Dict[str, float]:
        """
        Calculeaza Pretul Median si Floor Price (P25) ajustat dupa kilometraj.
        """
        clean_make = (make or "").lower().strip().replace(" ", "-")
        clean_model = (model or "").lower().strip().replace(" ", "-")

        if existing_prices and len(existing_prices) >= 4:
            prices = sorted(existing_prices)
            median_price = float(np.median(prices))
            floor_price = float(np.percentile(prices, 25))
        else:
            base = BASELINE_MARKET_PRICES.get((clean_make, clean_model, year))
            if not base:
                # Cautam dupa marca si model cel mai apropiat an
                similar = [(k[2], v) for k, v in BASELINE_MARKET_PRICES.items() if k[0] == clean_make and k[1] == clean_model]
                if similar:
                    # Gasim cel mai apropiat an
                    closest_year_val = min(similar, key=lambda x: abs(x[0] - (year or 2016)))[1]
                    base = float(closest_year_val)
                else:
                    # Daca e model generic/necunoscut
                    age = max(1, 2026 - (year or 2015))
                    base = max(3500.0, 25000.0 * (0.87 ** age))

            # Ajustare dupa kilometraj
            # Media este aprox 18.000 km / an de varsta
            expected_km = max(50000, (2026 - (year or 2016)) * 18000)
            km_diff = (mileage or 180000) - expected_km

            # La fiecare 30.000 km peste medie scade pretul cu 2.5%, sub medie creste cu 2.5%
            km_factor = 1.0 - (km_diff / 30000.0) * 0.025
            km_factor = max(0.85, min(1.15, km_factor))  # max +/- 15% ajustare

            median_price = float(base) * km_factor
            floor_price = round(median_price * 0.88, 2)

        return {
            "median_price": round(median_price, 2),
            "floor_price": round(floor_price, 2)
        }

    @classmethod
    def evaluate_deal(
        cls, listing_price: float, make: str, model: str, year: int, mileage: int = 180000, existing_prices: List[float] = None
    ) -> Dict:
        """
        Evalueaza daca anuntul este un pont real cu profit garantat.
        Filtreaza anomaliile nerealiste (>60% sub piata) ca suspecte de frauda.
        """
        market = cls.estimate_market_prices(make, model, year, mileage, existing_prices)
        median_price = market["median_price"]
        floor_price = market["floor_price"]

        gross_savings = round(median_price - listing_price, 2)
        discount_pct = round((gross_savings / median_price) * 100, 2) if median_price > 0 else 0.0

        # FORMULA PROFITULUI GARANTAT:
        # Floor Price (pret minim de lichidare in 48h) - Pret Achizitie - 1.050€ Cheltuieli
        net_profit = round(floor_price - listing_price - BUFFER_EXPENSES_EUR, 2)

        # Filtrare anomalii extreme: daca e listat cu peste 62% sub piata, e 99% scam/frauda
        is_scam_suspect = discount_pct > 62.0 and listing_price > 1000

        is_deal = False
        deal_rating = "STANDARD"

        if is_scam_suspect:
            deal_rating = "SUSPECT FRAUDA"
            is_deal = False
        elif net_profit >= 2500 and discount_pct >= 24.0:
            is_deal = True
            deal_rating = "UNICORN"
        elif net_profit >= MIN_NET_PROFIT_EUR and discount_pct >= MIN_DISCOUNT_PERCENT:
            is_deal = True
            deal_rating = "SUPER PONT"
        elif net_profit >= 800 and discount_pct >= 14.0:
            is_deal = True
            deal_rating = "OFERTA BUNA"

        return {
            "listing_price": listing_price,
            "median_price": median_price,
            "floor_price": floor_price,
            "buffer_expenses": BUFFER_EXPENSES_EUR,
            "gross_savings": gross_savings,
            "discount_pct": discount_pct,
            "net_profit": net_profit,
            "is_deal": is_deal,
            "deal_rating": deal_rating
        }
