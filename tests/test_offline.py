"""
Teste OFFLINE pentru AutoDealHunter (nu acceseaza internetul, nu ating car_deals.db).

Rulare:  python -m unittest tests.test_offline -v
"""

import os
import sys
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Configurare izolata INAINTE de orice import din proiect
_TMP_DIR = tempfile.mkdtemp(prefix="adh_test_")
os.environ["DATABASE_PATH"] = os.path.join(_TMP_DIR, "test.db")
os.environ["TELEGRAM_BOT_TOKEN"] = ""
os.environ["TELEGRAM_CHAT_ID"] = ""
os.environ["GEMINI_API_KEY"] = ""
os.environ["OPENAI_API_KEY"] = ""
os.environ["MIN_NET_PROFIT_EUR"] = "1200"
os.environ["MIN_DISCOUNT_PERCENT"] = "15"
os.environ["MIN_LISTING_PRICE_EUR"] = "1800"
os.environ["MAX_LISTING_PRICE_EUR"] = "15000"
os.environ["MAX_MILEAGE_KM"] = "260000"
os.environ["EUR_RON_RATE"] = "5.0"

from core.utils import parse_price_eur, parse_km, img_src  # noqa: E402
from core.anti_fraud import AntiFraudShield  # noqa: E402
from core import live_market  # noqa: E402
from core.live_market import PreciseMarketEngine, normalize_make_model  # noqa: E402
from core import db  # noqa: E402
from core.ai_inspector import _normalize_ai_result  # noqa: E402
from alerts import telegram_bot  # noqa: E402
from alerts.telegram_bot import TelegramNotifier, normalize_phone  # noqa: E402


def _comparables(prices, mileage=150000, prefix="cmp"):
    return [
        {"price": float(p), "year": 2016, "mileage": mileage, "fuel": "Diesel",
         "url": f"https://www.autovit.ro/{prefix}-{i}", "external_id": f"autovit_{prefix}{i}"}
        for i, p in enumerate(sorted(prices))
    ]


class TestTitleParser(unittest.TestCase):
    def test_no_make_guessing_from_numbers(self):
        from core.title_parser import TitleParser
        r = TitleParser.parse("Abarth 595 Turismo 1.4 T-Jet 160 CP Automat MTA 2016 89.000 km")
        self.assertNotEqual(r["make"], "bmw")  # inainte: BMW Seria 1
        self.assertEqual(TitleParser.parse("BMW 320d 2014")["model"], "seria-3")
        self.assertEqual(TitleParser.parse("Golf 7 1.6 TDI 2016")["make"], "volkswagen")


class TestParsing(unittest.TestCase):
    def test_price_formats(self):
        self.assertEqual(parse_price_eur("10 500 EUR"), 10500.0)   # bug-ul Publi24
        self.assertEqual(parse_price_eur("10.500 €"), 10500.0)
        self.assertEqual(parse_price_eur("3 490 €"), 3490.0)
        self.assertEqual(parse_price_eur("12 990 €"), 12990.0)
        self.assertEqual(parse_price_eur("25 000 lei"), 5000.0)
        self.assertIsNone(parse_price_eur("Negociabil"))
        self.assertIsNone(parse_price_eur(""))

    def test_km_formats(self):
        self.assertEqual(parse_km("2011 210 651 km"), 210651)
        self.assertEqual(parse_km("98.000 Km"), 98000)
        self.assertEqual(parse_km("150000km"), 150000)
        self.assertEqual(parse_km("fara rulaj"), 0)

    def test_img_src_none(self):
        self.assertEqual(img_src(None), "")


class TestAntiFraud(unittest.TestCase):
    def ok(self, title, desc="", price=6000, **kw):
        kw.setdefault("make", "volkswagen")
        kw.setdefault("model", "golf")
        kw.setdefault("year", 2016)
        kw.setdefault("mileage", 150000)
        return AntiFraudShield.inspect(title, desc, price, **kw)[0]

    def test_rejects_real_problems(self):
        self.assertFalse(self.ok("Golf 7", "Pret avans 3500 euro restul in rate"))
        self.assertFalse(self.ok("Golf 7", "Posibilitate finantare rate fixe"))
        self.assertFalse(self.ok("Golf 7 lovit in aripa"))
        self.assertFalse(self.ok("Golf 7", "masina este lovită usor"))
        self.assertFalse(self.ok("Golf 7", "vand pentru piese"))
        self.assertFalse(self.ok("Golf 7", "motorul nu porneste"))
        self.assertFalse(self.ok("Golf 7", "accept schimb cu auto"))
        self.assertFalse(self.ok("Golf 7", "fara avans, aprobare rapida"))
        self.assertFalse(self.ok("Golf 7", "are un defect la cutie"))
        self.assertFalse(self.ok("Golf 7", "volan pe dreapta"))
        self.assertFalse(self.ok("Golf 7", "", price=900))
        self.assertFalse(self.ok("Golf 7", "", mileage=300000))
        self.assertFalse(self.ok("Fiat Punto", "", make="fiat", model="punto"))

    def test_accepts_honest_negations(self):
        # Toate acestea erau respinse gresit inainte (pierdeam ponturi bune)
        self.assertTrue(self.ok("Golf 7", "Nu accept rate sau leasing, nu accept schimburi."))
        self.assertTrue(self.ok("Golf 7", "Fara rugina, nu are niciun defect, nelovita."))
        self.assertTrue(self.ok("Golf 7", "Masina nu e lovita, fara accidente."))
        self.assertTrue(self.ok("Golf 7", "Piese originale, distributie schimbata, garnitura chiuloasa schimbata."))
        self.assertTrue(self.ok("Golf 7", "Fara defecte, service la zi."))


class TestMarketEngine(unittest.TestCase):
    def setUp(self):
        live_market._MARKET_CACHE.clear()
        PreciseMarketEngine._last_query_failed = False

    def test_normalization(self):
        self.assertEqual(normalize_make_model("mercedes", "c-klasse"), ("mercedes-benz", "clasa-c"))
        self.assertEqual(normalize_make_model("bmw", "320d"), ("bmw", "seria-3"))
        self.assertEqual(normalize_make_model("vw", "Golf"), ("volkswagen", "golf"))

    def test_excludes_itself_from_comparables(self):
        # Anuntul evaluat (5000€) este primul in lista Autovit. Inainte era comparat cu el insusi.
        self_url = "https://www.autovit.ro/anunt-golf-ID123"
        market = [{"price": 5000.0, "year": 2016, "mileage": 150000, "fuel": "Diesel",
                   "url": self_url + "?tracking=1", "external_id": "autovit_123"}] + _comparables(
            [9000, 9200, 9400, 9600, 9800, 10000, 10200, 10400], prefix="x")
        with mock.patch.object(PreciseMarketEngine, "query_autovit_precise", return_value=market):
            r = PreciseMarketEngine.evaluate(5000, "volkswagen", "golf", "diesel", 2016, 150000,
                                             source="Autovit.ro", url=self_url, external_id="autovit_123")
        self.assertEqual(r["cheapest_on_market"], 9000.0)
        self.assertEqual(r["total_comparable"], 8)

    def test_uses_env_thresholds(self):
        market = _comparables([7000, 7100, 7200, 7300, 7400, 7500, 7600, 7700])
        with mock.patch.object(PreciseMarketEngine, "query_autovit_precise", return_value=market):
            # vanzare rapida = 7100*0.95 = 6745; la 5000€ -> profit 6745-5000-1050 = 695 < 1200 -> NU e pont
            r = PreciseMarketEngine.evaluate(5000, "volkswagen", "golf", "diesel", 2016, 150000)
            self.assertFalse(r["is_deal"])
            # la 4200€ -> profit 1495 si reducere 37.7% -> pont
            r = PreciseMarketEngine.evaluate(4200, "volkswagen", "golf", "diesel", 2016, 150000)
            self.assertTrue(r["is_deal"])

    def test_import_costs_added(self):
        market = _comparables([7000, 7100, 7200, 7300, 7400, 7500, 7600, 7700])
        with mock.patch.object(PreciseMarketEngine, "query_autovit_precise", return_value=market):
            ro = PreciseMarketEngine.evaluate(4500, "volkswagen", "golf", "diesel", 2016, 150000, source="OLX.ro")
            imp = PreciseMarketEngine.evaluate(4500, "volkswagen", "golf", "diesel", 2016, 150000, source="Willhaben (Austria)")
        self.assertAlmostEqual(ro["net_profit"] - imp["net_profit"], 850.0)

    def test_mileage_matching(self):
        low_km = _comparables([9000, 9100, 9200, 9300, 9400, 9500], mileage=90000, prefix="low")
        high_km = _comparables([6000, 6100, 6200, 6300, 6400, 6500], mileage=240000, prefix="high")
        with mock.patch.object(PreciseMarketEngine, "query_autovit_precise", return_value=sorted(low_km + high_km, key=lambda n: n["price"])):
            r = PreciseMarketEngine.evaluate(5000, "volkswagen", "golf", "diesel", 2016, 245000)
        # Masina cu 245.000 km se compara doar cu cele cu rulaj mare
        self.assertLess(r["safe_sell_price"], 7000)

    def test_prefers_near_year_comparables(self):
        calls = []

        def fake_query(make, model, fuel, y1, y2):
            calls.append((fuel, y1, y2))
            # anii apropiati au masini mai scumpe decat bucla ieftina din 2013
            return _comparables([9000, 9100, 9200, 9300, 9400, 9500]) if (y1, y2) == (2016, 2018) else _comparables([3000, 3100, 3200, 3300, 3400, 3500])

        with mock.patch.object(PreciseMarketEngine, "query_autovit_precise", side_effect=fake_query):
            r = PreciseMarketEngine.evaluate(6000, "volkswagen", "golf", "diesel", 2017, 150000)
        self.assertEqual(calls[0], ("diesel", 2016, 2018))
        self.assertEqual(len(calls), 1)
        self.assertGreater(r["safe_sell_price"], 8000)

    def test_impossible_price_rejected(self):
        r = PreciseMarketEngine.evaluate(1900, "bmw", "seria-5", "diesel", 2013, 200000)
        self.assertEqual(r["deal_rating"], "SUSPECT FRAUDA")

    def test_market_unavailable_flag(self):
        with mock.patch("core.live_market.requests.get", side_effect=OSError("network down")):
            r = PreciseMarketEngine.evaluate(6000, "volkswagen", "golf", "diesel", 2016, 150000)
        self.assertTrue(r.get("market_unavailable"))

    def test_ron_comparables_converted(self):
        nodes = []
        for i, (val, cur) in enumerate([(40000, "RON"), (8100, "EUR"), (8200, "EUR"), (8300, "EUR"), (8400, "EUR"), (8500, "EUR")]):
            nodes.append({"node": {
                "id": str(i), "title": "VW Golf", "url": f"https://www.autovit.ro/a{i}",
                "price": {"amount": {"value": str(val), "currencyCode": cur}},
                "parameters": [{"key": "year", "value": "2016"}, {"key": "mileage", "value": "150000"}],
            }})
        next_data = {"props": {"pageProps": {"urqlState": {"k": {"data": json.dumps({"advertSearch": {"edges": nodes}})}}}}}
        html = f'<script id="__NEXT_DATA__" type="application/json">{json.dumps(next_data)}</script>'
        resp = mock.Mock(status_code=200, text=html)
        with mock.patch("core.live_market.requests.get", return_value=resp):
            res = PreciseMarketEngine.query_autovit_precise("volkswagen", "golf", "", 2013, 2019)
        self.assertEqual(res[0]["price"], 8000.0)  # 40.000 lei / 5 = 8.000 €, nu 40.000 €


class TestDatabase(unittest.TestCase):
    def _listing(self, ext, price=5000):
        return {"external_id": ext, "source": "OLX.ro", "title": "VW Golf 7", "url": f"https://x/{ext}",
                "price_eur": price, "make": "volkswagen", "model": "golf", "year": 2016, "mileage": 150000}

    def test_price_drop_triggers_reevaluation(self):
        db.save_listing_and_deal(self._listing("t_drop", 6000), {"is_deal": False})
        self.assertTrue(db.should_skip_seen("t_drop", 6000))
        self.assertTrue(db.should_skip_seen("t_drop", 5900))   # -1.7%: ignorat
        self.assertFalse(db.should_skip_seen("t_drop", 5500))  # -8%: re-evaluat
        self.assertFalse(db.should_skip_seen("t_new", 5000))

    def test_deal_details_roundtrip(self):
        details = {"ai_score": 91, "ai_summary": "Ok", "generation": "golf-7", "total_comparable": 12}
        deal_id = db.save_listing_and_deal(self._listing("t_deal"), {
            "is_deal": True, "median_price": 7000, "floor_price": 6800, "discount_pct": 25,
            "net_profit": 1300, "deal_rating": "PONT REAL", "details": details})
        self.assertIsNotNone(deal_id)
        pending = {d["deal_id"]: d for d in db.get_unalerted_deals()}
        self.assertEqual(pending[deal_id]["ai_score"], 91)
        self.assertEqual(pending[deal_id]["generation"], "golf-7")
        db.mark_as_alerted(deal_id)
        self.assertNotIn(deal_id, {d["deal_id"] for d in db.get_unalerted_deals()})
        # Re-salvarea aceluiasi pont deja trimis nu produce o alerta noua
        again = db.save_listing_and_deal(self._listing("t_deal", 4800), {
            "is_deal": True, "net_profit": 1500, "deal_rating": "PONT REAL", "details": details})
        self.assertIsNone(again)


class TestTelegram(unittest.TestCase):
    DEAL = {"deal_id": 1, "title": "Golf <7> & Co", "url": "https://www.olx.ro/d/oferta/x?a=1&b=2",
            "price_eur": 5000, "net_profit": 1300, "year": 2016, "mileage": 150000, "fuel": "Diesel",
            "city": "Cluj", "source": "OLX.ro", "deal_rating": "PONT REAL", "seller_phone": "0722 123 456"}

    def test_not_configured_does_not_mark_sent(self):
        with mock.patch.object(telegram_bot, "TELEGRAM_BOT_TOKEN", ""):
            self.assertFalse(TelegramNotifier.send_deal_alert(dict(self.DEAL)))

    def test_html_is_escaped_and_no_fake_ai_score(self):
        captured = {}

        def fake_post(url, json=None, timeout=None):
            captured.update(json)
            return mock.Mock(status_code=200, json=lambda: {"ok": True})

        with mock.patch.object(telegram_bot, "TELEGRAM_BOT_TOKEN", "123:abc"), \
                mock.patch.object(telegram_bot, "TELEGRAM_CHAT_ID", "111"), \
                mock.patch("alerts.telegram_bot.requests.post", side_effect=fake_post):
            self.assertTrue(TelegramNotifier.send_deal_alert(dict(self.DEAL)))
        text = captured["text"]
        self.assertIn("Golf &lt;7&gt; &amp; Co", text)
        self.assertNotIn("<7>", text)
        self.assertNotIn("85/100", text)
        self.assertIn("a=1&amp;b=2", text)
        buttons = [b[0]["url"] for b in captured["reply_markup"]["inline_keyboard"]]
        self.assertTrue(any(u.startswith("https://wa.me/40722123456") for u in buttons))

    def test_phone_normalization(self):
        self.assertEqual(normalize_phone("0722 123 456"), "40722123456")
        self.assertEqual(normalize_phone("+40 722 123 456"), "40722123456")
        self.assertEqual(normalize_phone("0040722123456"), "40722123456")
        self.assertEqual(normalize_phone("123"), "")


class TestAIResult(unittest.TestCase):
    def test_malformed_ai_output(self):
        r = _normalize_ai_result({"approved": "true", "confidence_score": "90", "risk_flags": "rugina"}, "X", "d")
        self.assertTrue(r["approved"])
        self.assertEqual(r["risk_flags"], ["rugina"])
        r = _normalize_ai_result({"approved": True, "confidence_score": 40}, "X", "d")
        self.assertFalse(r["approved"])  # sub pragul AI_MIN_CONFIDENCE_SCORE
        r = _normalize_ai_result({"approved": True, "confidence_score": "abc"}, "X", "d")
        self.assertEqual(r["ai_score"], 50)


class TestScrapers(unittest.TestCase):
    def test_olx_card_sample(self):
        from scrapers.olx import OLXScraper
        html = (ROOT / "tests" / "card_sample.html").read_bytes()
        fake = mock.Mock(returncode=0, stdout=html)
        with mock.patch("scrapers.olx.subprocess.run", return_value=fake):
            items = OLXScraper.fetch_latest_listings()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["price_eur"], 3490.0)

    def test_olx_card_without_image_does_not_crash(self):
        from scrapers.olx import OLXScraper
        html = ('<div data-cy="l-card"><a href="/d/oferta/vw-golf-7-ID1.html"><h4>Volkswagen Golf 7 2016</h4></a>'
                '<p data-testid="ad-price">8 500 €</p><p>2016 - 150 000 km</p></div>'
                '<div data-cy="l-card"><a href="/d/oferta/skoda-octavia-ID2.html"><h4>Skoda Octavia 2015</h4></a>'
                '<p data-testid="ad-price">7 900 €</p><img src="https://img/x.jpg"><p>2015 - 180 000 km</p></div>').encode()
        with mock.patch("scrapers.olx.subprocess.run", return_value=mock.Mock(returncode=0, stdout=html)):
            items = OLXScraper.fetch_latest_listings()
        self.assertEqual(len(items), 2)  # inainte: crash pe primul card -> 0 anunturi
        self.assertEqual(items[0]["price_eur"], 8500.0)
        self.assertEqual(items[0]["mileage"], 150000)
        self.assertEqual(items[1]["photo_url"], "https://img/x.jpg")

    def test_publi24_nbsp_price(self):
        from scrapers.publi24 import Publi24Scraper
        html = ('<div class="article-content-wrap"><a href="/anunturi/auto/anunt/vw-golf-7.html">Volkswagen Golf 7 2016</a>'
                '<span class="article-price">10 500 EUR</span><p>2016</p><p>diesel</p><p>150000 km</p></div>')
        with mock.patch("scrapers.publi24.requests.get", return_value=mock.Mock(status_code=200, text=html)):
            items = Publi24Scraper.fetch_latest_listings()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["price_eur"], 10500.0)  # inainte: 10 €
        self.assertEqual(items[0]["year"], 2016)
        self.assertEqual(items[0]["mileage"], 150000)


class TestHub(unittest.TestCase):
    def _patch_sources(self, items):
        from scrapers import hub
        empty = mock.Mock(return_value=[])
        return [
            mock.patch.object(hub.ModelScanner, "scan_liquid_bargains", empty),
            mock.patch.object(hub.OLXScraper, "fetch_latest_listings", mock.Mock(return_value=items)),
            mock.patch.object(hub.AutovitScraper, "fetch_latest_listings", empty),
            mock.patch.object(hub.Publi24Scraper, "fetch_latest_listings", empty),
            mock.patch.object(hub.CarZZScraper, "fetch_latest_listings", empty),
            mock.patch.object(hub.AutoScout24Scraper, "fetch_latest_listings", empty),
            mock.patch.object(hub.WillhabenScraper, "fetch_latest_listings", empty),
        ]

    def _item(self, ext):
        return {"external_id": ext, "source": "OLX.ro", "title": "Volkswagen Golf 7 1.6 TDI 2016",
                "url": f"https://www.olx.ro/d/oferta/{ext}", "price_eur": 4200.0, "make": "volkswagen",
                "model": "golf", "year": 2016, "mileage": 150000, "fuel": "Diesel", "description": "Golf 7"}

    def _run(self, items, **patches):
        from scrapers import hub
        ps = self._patch_sources(items) + [mock.patch.object(*k) for k in patches.get("extra", [])]
        for p in ps:
            p.start()
        try:
            return hub.ScraperHub.scan_all(max_pages=1)
        finally:
            for p in ps:
                p.stop()

    def test_full_pipeline_creates_deal_with_details(self):
        from scrapers import hub
        market = _comparables([7000, 7100, 7200, 7300, 7400, 7500, 7600, 7700])
        res = self._run([self._item("olx_pipe1")], extra=[
            (hub.PreciseMarketEngine, "query_autovit_precise", mock.Mock(return_value=market)),
            (hub, "fetch_full_description", mock.Mock(return_value="Golf 7 impecabil, service la zi, fara rugina, nu accept rate.")),
        ])
        self.assertEqual(res["new_deals_found"], 1)
        deal = [d for d in db.get_unalerted_deals() if d["external_id"] == "olx_pipe1"][0]
        self.assertEqual(deal["generation"], "golf-7")
        self.assertEqual(deal["total_comparable"], 8)
        self.assertIn("ai_model", deal)

    def test_network_failure_does_not_lose_listing(self):
        from scrapers import hub
        market = _comparables([7000, 7100, 7200, 7300, 7400, 7500, 7600, 7700])
        res = self._run([self._item("olx_retry1")], extra=[
            (hub.PreciseMarketEngine, "query_autovit_precise", mock.Mock(return_value=market)),
            (hub, "fetch_full_description", mock.Mock(return_value="")),
        ])
        self.assertEqual(res["retry_later"], 1)
        self.assertFalse(db.is_already_seen("olx_retry1"))  # va fi reincercat la ciclul urmator

    def test_duplicate_items_in_same_cycle(self):
        from scrapers import hub
        res = self._run([self._item("olx_dup"), self._item("olx_dup")], extra=[
            (hub.PreciseMarketEngine, "query_autovit_precise", mock.Mock(return_value=[])),
        ])
        self.assertEqual(res["already_seen"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
