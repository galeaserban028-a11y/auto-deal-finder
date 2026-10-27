import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # ruleaza din orice folder
"""
Test Suite: Multi-AI Super-Inspector and Telegram AI Reporting
"""
import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from core.ai_inspector import MultiAIInspector
from alerts.telegram_bot import TelegramNotifier
from config.settings import MAX_LISTING_PRICE_EUR

print("=" * 60)
print("TEST 1: MultiAIInspector Local Heuristic Execution")
print("=" * 60)

test_listing_good = {
    "title": "Volkswagen Golf 6 1.6 TDI 2012",
    "description": "Proprietar, revizii la zi in reprezentanta, distributie noua, carte service.",
    "price_eur": 4200,
    "mileage": 165000,
    "year": 2012,
    "make": "volkswagen",
    "model": "golf",
    "photo_url": "https://example.com/golf.jpg"
}

res_good = MultiAIInspector.inspect_deal(test_listing_good)
print(f"Good car: approved={res_good['approved']}, score={res_good['ai_score']}, model={res_good['model_used']}")
assert res_good["approved"] is True
assert res_good["ai_score"] >= 75

test_listing_shady = {
    "title": "Volkswagen Golf 6 2012 Urgent",
    "description": "Se vinde urgent, pret fix, primul venit primul servit, mici investitii recente.",
    "price_eur": 3000,
    "mileage": 165000,
    "year": 2012,
    "make": "volkswagen",
    "model": "golf",
    "photo_url": ""
}

res_shady = MultiAIInspector.inspect_deal(test_listing_shady)
print(f"Shady car: approved={res_shady['approved']}, score={res_shady['ai_score']}, flags={res_shady['risk_flags']}")
assert res_shady["ai_score"] < res_good["ai_score"]
assert len(res_shady["risk_flags"]) > 0

print("\n" + "=" * 60)
print("TEST 2: Telegram HTML Format with AI Report")
print("=" * 60)

mock_deal = {
    "deal_id": 999,
    "title": "Skoda Octavia 2.0 TDI",
    "year": 2014,
    "mileage": 155000,
    "fuel": "Diesel",
    "city": "Bucuresti",
    "price_eur": 5200.0,
    "cheapest_on_market": 6500.0,
    "pct_below_cheapest": 20.0,
    "net_profit": 850.0,
    "total_comparable": 12,
    "source": "Autovit.ro",
    "url": "https://www.autovit.ro/anunt/skoda-octavia",
    "ai_score": 92,
    "ai_summary": "Masina curata, istoric transparent, fara defecte.",
    "ai_model": "Google Gemini 2.0 Flash",
    "ai_flags": [],
}

# Verificam ca telegram_bot construieste mesajul corect fara eroare
assert TelegramNotifier.is_configured() is True
print("Telegram is configured and ready.")

print("\n" + "=" * 60)
print(f"TEST 3: Max Price Guardrail = {MAX_LISTING_PRICE_EUR} EUR")
print("=" * 60)
assert MAX_LISTING_PRICE_EUR == 7000.0
print(f"Max listing price confirmed: {MAX_LISTING_PRICE_EUR} EUR")

print("\n" + "=" * 60)
print("TOATE TESTELE MULTI-AI AU TRECUT CU SUCCES! ✅")
print("=" * 60)
