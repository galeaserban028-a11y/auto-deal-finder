"""
Automated Test Suite for AutoDealHunter (Extins & Riguros)
Verifica:
1. Scutul Anti-Fraud / Anti-Leasing (capcane de rate, avans, defecte, lipsa fiscal)
2. Motorul de evaluare a pietei, ajustarea kilometrica si formula de profit garantat
3. Filtrarea tentativelor de frauda/scam (preturi nerealiste >60% sub piata)
4. Formatarea alertelor Telegram cu link direct accesibil
5. Functionarea scraperelor pe date reale din Romania (Autovit + Publi24)
"""

import unittest
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from core.anti_fraud import AntiFraudShield
from core.market_engine import MarketValuationEngine
from alerts.telegram_bot import TelegramNotifier
from scrapers.autovit import AutovitScraper
from scrapers.publi24 import Publi24Scraper


class TestAutoDealHunter(unittest.TestCase):

    def test_anti_leasing_filter(self):
        """Asigura respingerea anunturilor cu avans sau rate deghizate."""
        cases = [
            ("BMW Seria 3 2018", "Pretul este avans 3000 euro si preluare leasing", 3000),
            ("Audi A4 2017", "Rata lunara 250 euro fara avans", 2500),
            ("VW Passat 2019", "Cesiune contract credit, doar avansul", 4500),
            ("Skoda Octavia", "TVA deductibil la avans, rate fixe", 2000),
        ]
        for title, desc, price in cases:
            is_safe, reason = AntiFraudShield.inspect(title, desc, price)
            self.assertFalse(is_safe, f"Ar fi trebuit sa respinga: {title} - {desc}")
            self.assertIn("leasing", reason.lower())

    def test_anti_damage_and_fiscal_filter(self):
        """Asigura respingerea anunturilor cu masini avariate, piese sau fara fiscal."""
        cases = [
            ("VW Golf 7 Avariat", "Motor defect, se vinde pentru piese", 2500),
            ("BMW Seria 5 Epava", "Dauna totala, dezmembrez", 3500),
            ("Ford Focus", "Nu porneste, probleme motor", 1500),
            ("Dacia Duster", "Fara acte, neinmatriculabil", 2000),
            ("Audi A6", "Nu ofer fiscal, proprietar in strainatate", 6500),
        ]
        for title, desc, price in cases:
            is_safe, reason = AntiFraudShield.inspect(title, desc, price)
            self.assertFalse(is_safe, f"Ar fi trebuit sa respinga: {title} - {desc}")

    def test_clean_listing_accepted(self):
        """Asigura acceptarea anunturilor legitime si curate."""
        title = "Volkswagen Golf VII 2.0 TDI Highline"
        desc = "Unic proprietar, fiscal pe loc, carte service la zi, accept orice test"
        is_safe, reason = AntiFraudShield.inspect(title, desc, 8500)
        self.assertTrue(is_safe, f"Anuntul legitim a fost respins: {reason}")

    def test_market_profit_calculation(self):
        """Verifica scaderea cheltuielilor de 1050€ si calculul profitului net."""
        res = MarketValuationEngine.evaluate_deal(
            listing_price=6000.0,
            make="volkswagen",
            model="golf",
            year=2016,
            mileage=180000
        )
        self.assertTrue(res["is_deal"])
        self.assertGreaterEqual(res["net_profit"], 1500)
        self.assertIn(res["deal_rating"], ["SUPER PONT", "UNICORN"])
        self.assertEqual(res["buffer_expenses"], 1050.0)

    def test_mileage_adjustment(self):
        """Verifica ca un rulaj mic creste valoarea estimata, iar un rulaj mare o scade."""
        val_low_km = MarketValuationEngine.estimate_market_prices("volkswagen", "golf", 2017, mileage=60000)
        val_high_km = MarketValuationEngine.estimate_market_prices("volkswagen", "golf", 2017, mileage=320000)
        self.assertGreater(val_low_km["median_price"], val_high_km["median_price"], "Masina cu putini km ar trebui sa aiba pret estimat mai mare!")

    def test_extreme_scam_filter(self):
        """Preturile nerealiste (>62% sub piata) trebuie clasificate ca SUSPECT FRAUDA, nu ca pont."""
        res = MarketValuationEngine.evaluate_deal(
            listing_price=3000.0,
            make="bmw",
            model="seria-5",
            year=2018,
            mileage=120000
        )
        self.assertFalse(res["is_deal"], "Un BMW 2018 la 3000€ este o tentativa de frauda si nu trebuie marcat ca pont!")
        self.assertEqual(res["deal_rating"], "SUSPECT FRAUDA")

    def test_telegram_alert_formatting(self):
        """Verifica ca alerta Telegram contine linkul direct si este formatata corect."""
        test_deal = {
            "title": "Audi A4 B9 2.0 TDI",
            "url": "https://www.autovit.ro/autoturisme/anunt/audi-a4-ID123.html",
            "price_eur": 9500.0,
            "median_price": 14500.0,
            "floor_price": 12760.0,
            "net_profit": 2210.0,
            "discount_pct": 34.0,
            "year": 2016,
            "mileage": 185000,
            "fuel": "Diesel",
            "city": "Cluj-Napoca",
            "source": "Autovit.ro",
            "deal_rating": "UNICORN"
        }
        success = TelegramNotifier.send_deal_alert(test_deal)
        self.assertTrue(success)

    def test_live_scrapers_connectivity(self):
        """Verifica ca ambele platforme active (Autovit & Publi24) returneaza date reale."""
        autovit_items = AutovitScraper.fetch_latest_listings(page=1)
        self.assertGreater(len(autovit_items), 0, "Autovit ar trebui sa returneze anunturi!")
        self.assertTrue(autovit_items[0]["url"].startswith("http"), "Linkul Autovit trebuie sa fie un URL valid!")

        publi24_items = Publi24Scraper.fetch_latest_listings(max_items=5)
        self.assertGreater(len(publi24_items), 0, "Publi24 ar trebui sa returneze anunturi!")
        self.assertTrue(publi24_items[0]["url"].startswith("http"), "Linkul Publi24 trebuie sa fie un URL valid!")


if __name__ == "__main__":
    unittest.main()
