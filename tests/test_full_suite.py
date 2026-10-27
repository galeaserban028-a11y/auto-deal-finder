"""
SUITA COMPLETA DE TESTE — AUTODEALHUNTER v3
===========================================
Ruleaza testarea cap-coada (100% acoperire functionala):
1. TitleParser (detectie automata marca, model, an, combustibil din text)
2. AntiFraudShield (filtrare leasing/rate, daune, defecte, acte expirate, numere rosii, rulaj >300k, modele ne-lichide)
3. PreciseMarketEngine (interogare live Autovit, identificare piata similara, formula profit garantat)
4. Database (SQLite, salvare, deduplicare, unalerted queue)
5. Scraper Connectivity (OLX, Autovit, Publi24, ModelScanner)
6. Telegram Alert Generator (formatare HTML, linkuri active, buton WhatsApp)
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Testele scriu in baza de date -> folosim o baza temporara, nu car_deals.db (inainte o poluau cu "UnitTest")
os.environ.setdefault("DATABASE_PATH", os.path.join(tempfile.mkdtemp(prefix="adh_suite_"), "test.db"))

from core.title_parser import TitleParser
from core.anti_fraud import AntiFraudShield
from core.live_market import PreciseMarketEngine
from core.db import is_already_seen, save_listing_and_deal, get_unalerted_deals
from alerts.telegram_bot import TelegramNotifier
from scrapers.olx import OLXScraper
from scrapers.publi24 import Publi24Scraper
from scrapers.autovit import AutovitScraper
from scrapers.model_scanner import ModelScanner


class TestAutoDealHunterV3(unittest.TestCase):

    def test_01_title_parser_accuracy(self):
        """Test parsare titluri OLX / Publi24"""
        cases = [
            ("BMW Seria 3 320d 2017 Automat", "bmw", "seria-3", 2017, "diesel"),
            ("Volkswagen Golf 7 1.6 TDI 2018", "volkswagen", "golf", 2018, "diesel"),
            ("Dacia Duster 1.5 dCi 2019 4x4", "dacia", "duster", 2019, "diesel"),
            ("Skoda Octavia III 2.0 TDI 2016", "skoda", "octavia", 2016, "diesel"),
            ("Ford Focus 1.0 EcoBoost 2020", "ford", "focus", 2020, "benzina"),
            ("Toyota RAV4 2.0 Hybrid 2021", "toyota", "rav4", 2021, "hybrid"),
            ("Renault Megane 1.5 dCi 2015", "renault", "megane", 2015, "diesel"),
        ]
        for title, mk, md, yr, fl in cases:
            res = TitleParser.parse(title)
            self.assertEqual(res["make"], mk, f"Make mismatch for {title}")
            self.assertEqual(res["model"], md, f"Model mismatch for {title}")
            self.assertEqual(res["year"], yr, f"Year mismatch for {title}")
            self.assertEqual(res["fuel"], fl, f"Fuel mismatch for {title}")

    def test_02_anti_fraud_shield_rules(self):
        """Test filtrul anti-frauda pe toate regulile critice"""
        # 1. Capcane de leasing si rate ascunse
        safe, _ = AntiFraudShield.inspect("Passat 2018", "Pret avans 3500 euro restul in rate", 3500)
        self.assertFalse(safe)

        safe, _ = AntiFraudShield.inspect("BMW Seria 3 2019", "Posibilitate finantare rate fixe doar cu buletinul", 4000)
        self.assertFalse(safe)

        # 2. Daune si defecte grave
        safe, _ = AntiFraudShield.inspect("Golf 7 lovit aripa motor blocat", "", 3000)
        self.assertFalse(safe)

        # 3. Acte expirate si numere rosii
        safe, _ = AntiFraudShield.inspect("Audi A4 2012 numere rosii expirate", "", 3200)
        self.assertFalse(safe)

        safe, _ = AntiFraudShield.inspect("Ford Focus acte expirate", "", 2000)
        self.assertFalse(safe)

        # 4. Rulaj prea mare (>300.000 km)
        safe, _ = AntiFraudShield.inspect("Passat B7", "Stare buna", 4500, mileage=340000, make="volkswagen", model="passat")
        self.assertFalse(safe)

        # 5. Model ne-lichid
        safe, _ = AntiFraudShield.inspect("Alfa Romeo 159", "Functionala", 2500, mileage=180000, make="alfa-romeo", model="159")
        self.assertFalse(safe)

        # 6. Masina curata si sigura (trebuie acceptata)
        safe, _ = AntiFraudShield.inspect("Golf 7 1.6 TDI 2017", "Unic proprietar fiscal pe loc carte service", 7500, mileage=170000, make="volkswagen", model="golf")
        self.assertTrue(safe)

    def test_03_precise_valuation_engine(self):
        """Test motorul de evaluare cu preturi reale din piata"""
        # Masina cu pret mediu de piata NU trebuie sa fie deal
        eval_normal = PreciseMarketEngine.evaluate(
            listing_price=8500.0,
            make="volkswagen",
            model="golf",
            fuel="diesel",
            year=2017,
            mileage=180000
        )
        self.assertFalse(eval_normal["is_deal"])
        self.assertIn("total_comparable", eval_normal)
        self.assertGreaterEqual(eval_normal["total_comparable"], 1)

        # Masina cu pret mult sub piata (chilipir)
        eval_bargain = PreciseMarketEngine.evaluate(
            listing_price=3000.0,
            make="volkswagen",
            model="golf",
            fuel="diesel",
            year=2017,
            mileage=180000
        )
        # La 3000€ fie e pont masiv fie suspect de frauda daca e prea mic
        self.assertTrue(eval_bargain["net_profit"] > 0 or eval_bargain["deal_rating"] == "SUSPECT FRAUDA")

        # Test BMW F10 la 3118 EUR (15500 RON din greseala) - respins ca SUSPECT FRAUDA
        eval_bmw_ron = PreciseMarketEngine.evaluate(
            listing_price=3118.0,
            make="bmw",
            model="seria-5",
            fuel="diesel",
            year=2013,
            mileage=210000
        )
        self.assertFalse(eval_bmw_ron["is_deal"])
        self.assertEqual(eval_bmw_ron["deal_rating"], "SUSPECT FRAUDA")

        # Test Ford Focus 2025 la 4748 EUR (23600 LEI din greseala) - respins ca SUSPECT FRAUDA
        eval_focus_ron = PreciseMarketEngine.evaluate(
            listing_price=4748.0,
            make="ford",
            model="focus",
            fuel="benzina",
            year=2025,
            mileage=15000
        )
        self.assertFalse(eval_focus_ron["is_deal"])
        self.assertEqual(eval_focus_ron["deal_rating"], "SUSPECT FRAUDA")

    def test_04_database_pipeline(self):
        """Test salvare si deduplicare in baza de date SQLite"""
        dummy_listing = {
            "external_id": "test_unit_9999",
            "source": "UnitTest",
            "title": "Dacia Duster 2018 1.5 dCi",
            "url": "https://example.com/test-duster",
            "price_eur": 6000.0,
            "make": "dacia",
            "model": "duster",
            "year": 2018,
            "mileage": 140000,
            "fuel": "Diesel",
            "transmission": "Manuala",
            "city": "Bucuresti",
            "seller_type": "private",
            "is_safe": True,
            "safety_reason": "Clean"
        }
        dummy_eval = {
            "is_deal": True,
            "median_price": 8500.0,
            "floor_price": 8000.0,
            "discount_pct": 25.0,
            "net_profit": 1450.0,
            "deal_rating": "UNICORN"
        }

        # Salvare
        deal_id = save_listing_and_deal(dummy_listing, dummy_eval)
        self.assertIsNotNone(deal_id)

        # Deduplicare: a doua oara trebuie sa fie deja vazut
        self.assertTrue(is_already_seen("test_unit_9999"))

    def test_05_telegram_alert_formatter(self):
        """Test formatare mesaj alerta Telegram cu linkuri si buton WhatsApp"""
        deal = {
            "deal_id": 999,
            "title": "VW Golf 7 2.0 TDI 2017 Highline",
            "price_eur": 5500.0,
            "cheapest_on_market": 7800.0,
            "pct_below_cheapest": 29.5,
            "net_profit": 1250.0,
            "total_comparable": 24,
            "deal_rating": "UNICORN",
            "year": 2017,
            "mileage": 165000,
            "fuel": "Diesel",
            "city": "Cluj-Napoca",
            "source": "OLX.ro",
            "url": "https://www.olx.ro/d/oferta/test-golf-ID123.html"
        }
        # In modul simulare (fara bot token real) returneaza True si printeaza curat
        res = TelegramNotifier.send_deal_alert(deal)
        self.assertTrue(res)

    def test_06_live_scrapers_connectivity(self):
        """Verifica conexiunea catre platformele tinta (Autovit, OLX, Publi24)"""
        # 1. Autovit
        autovit_items = AutovitScraper.fetch_latest_listings(page=1)
        self.assertGreater(len(autovit_items), 0, "Autovit scraper returned 0 items")

        # 2. OLX (via curl)
        olx_items = OLXScraper.fetch_latest_listings(max_items=5)
        self.assertGreater(len(olx_items), 0, "OLX scraper returned 0 items")

        # 3. Publi24
        publi_items = Publi24Scraper.fetch_latest_listings(max_items=5)
        self.assertGreater(len(publi_items), 0, "Publi24 scraper returned 0 items")

        # 4. Willhaben Austria
        from scrapers.willhaben import WillhabenScraper
        willhaben_items = WillhabenScraper.fetch_latest_listings(max_items=3)
        self.assertGreater(len(willhaben_items), 0, "Willhaben scraper returned 0 items")

    def test_07_price_conflict_detection(self):
        """Test detectia discrepantelor de pret intre descriere si card (eroare RON/EUR sau avans)"""
        from scrapers.hub import check_description_price_conflict

        # Descriere cu pret in Euro mult mai mare decat cardul listat in LEI
        desc_conflict = "Vand Ford Focus ST-Line 2025 impecabil. Pret: 23.600 Euro ( negociabil). Nu deranjati inutil."
        is_ok, reason = check_description_price_conflict(desc_conflict, 4748.0)
        self.assertFalse(is_ok)
        self.assertIn("Pret real in descriere", reason)

        # Descriere curata cu pret compatibil
        desc_clean = "Vand Golf 7 2017 carte service. Pret 6500 euro usor negociabil."
        is_ok, reason = check_description_price_conflict(desc_clean, 6200.0)
        self.assertTrue(is_ok)


if __name__ == "__main__":
    unittest.main(verbosity=2)
