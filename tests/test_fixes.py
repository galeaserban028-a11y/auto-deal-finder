import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # ruleaza din orice folder
"""Test complet pentru toate fix-urile critice."""
import sys
sys.stdout.reconfigure(encoding="utf-8")

from core.anti_fraud import AntiFraudShield

print("=" * 60)
print("TEST 1: Diacritice romanesti - LOVITA vs LOVITĂ")
print("=" * 60)

tests = [
    # (titlu, descriere, pret, year, expected_safe, label)
    ("BMW 320d lovita", "", 5000, 2015, False, "lovita fara diacritice"),
    ("BMW 320d lovită", "", 5000, 2015, False, "lovită CU diacritice"),
    ("VW Golf fără ITP", "", 5000, 2015, False, "fără ITP cu diacritice"),
    ("Audi A4 avariată grav", "", 5000, 2016, False, "avariată cu diacritice"),
    ("Skoda Octavia defectă", "", 5000, 2017, False, "defectă cu diacritice"),
    ("BMW X3 epavă", "", 5000, 2015, False, "epavă cu diacritice"),
    ("BMW X3 necesită atenție", "", 5000, 2015, False, "necesită atenție"),
    ("Masina buna stare perfecta", "", 5000, 2015, True, "masina buna (trebuie sa treaca)"),
    ("VW Golf 6 2012 Diesel", "", 5000, 2012, True, "golf normal (trebuie sa treaca)"),
]

all_pass = True
for title, desc, price, year, expected_safe, label in tests:
    ok, reason = AntiFraudShield.inspect(title=title, description=desc, price_eur=price, year=year)
    status = "PASS" if ok == expected_safe else "FAIL"
    if status == "FAIL":
        all_pass = False
    print(f"  [{status}] {label}: safe={ok}, reason={reason}")

print()
print("=" * 60)
print("TEST 2: Verificare an invalid")
print("=" * 60)

year_tests = [
    ("BMW 320d", "", 5000, 2003, False, "an prea vechi 2003"),
    ("BMW 320d", "", 5000, 2030, False, "an prea nou 2030"),
    ("BMW 320d", "", 5000, 2015, True, "an valid 2015"),
    ("BMW 320d", "", 5000, 0, True, "an necunoscut 0 (skip check)"),
]

for title, desc, price, year, expected_safe, label in year_tests:
    ok, reason = AntiFraudShield.inspect(title=title, description=desc, price_eur=price, year=year)
    status = "PASS" if ok == expected_safe else "FAIL"
    if status == "FAIL":
        all_pass = False
    print(f"  [{status}] {label}: safe={ok}, reason={reason}")

print()
print("=" * 60)
print("TEST 3: Pret si Rulaj")
print("=" * 60)

price_tests = [
    ("BMW 320d", "", 99999, 2015, False, "pret > MAX_LISTING_PRICE_EUR"),
    ("BMW 320d", "", 500, 2015, False, "pret < 1800€"),
    ("BMW 320d", "", 5000, 2015, True, "pret OK 5000€"),
]

for title, desc, price, year, expected_safe, label in price_tests:
    ok, reason = AntiFraudShield.inspect(title=title, description=desc, price_eur=price, year=year, mileage=100000)
    status = "PASS" if ok == expected_safe else "FAIL"
    if status == "FAIL":
        all_pass = False
    print(f"  [{status}] {label}: safe={ok}, reason={reason}")

mileage_tests = [
    ("BMW 320d", "", 5000, 2015, 999999, False, "rulaj > MAX_MILEAGE_KM"),
    ("BMW 320d", "", 5000, 2015, 150000, True, "rulaj OK 150000"),
]

for title, desc, price, year, mileage, expected_safe, label in mileage_tests:
    ok, reason = AntiFraudShield.inspect(title=title, description=desc, price_eur=price, year=year, mileage=mileage)
    status = "PASS" if ok == expected_safe else "FAIL"
    if status == "FAIL":
        all_pass = False
    print(f"  [{status}] {label}: safe={ok}, reason={reason}")

print()
print("=" * 60)
print("TEST 4: Mercedes model aliases")
print("=" * 60)

from config.settings import LIQUID_MODELS

merc_tests = [
    ("mercedes-benz", "c-class", True),
    ("mercedes-benz", "clasa-c", True),
    ("mercedes-benz", "e-class", True),
    ("mercedes", "c200", True),
]

for make, model, expected in merc_tests:
    allowed = LIQUID_MODELS.get(make, [])
    found = any(m in model or model in m for m in allowed)
    status = "PASS" if found == expected else "FAIL"
    if status == "FAIL":
        all_pass = False
    print(f"  [{status}] {make} {model}: liquid={found}")

print()
print("=" * 60)
print("TEST 5: Trust Score (POSITIVE_TRUST_PATTERNS fix)")
print("=" * 60)

try:
    score = AntiFraudShield.get_trust_score("Service la zi, km reali, proprietar unic")
    print(f"  [PASS] Trust score: {score} (no NameError)")
except NameError as e:
    all_pass = False
    print(f"  [FAIL] NameError: {e}")

print()
print("=" * 60)
if all_pass:
    print("TOATE TESTELE AU TRECUT! ✅")
else:
    print("UNELE TESTE AU PICAT! ❌")
print("=" * 60)
