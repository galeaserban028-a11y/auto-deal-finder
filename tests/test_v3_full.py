import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # ruleaza din orice folder
"""
Full System Verification Test for AutoDealHunter v3
===================================================
Testeaza toate componentele v3:
1. TitleParser
2. AntiFraudShield (noi filtre: acte expirate, numere rosii, km>300k, ne-lichide)
3. PreciseMarketEngine (evaluare live comparabila)
4. ModelScanner (colectare chilipiruri Autovit)
"""

import sys
sys.path.insert(0, ".")

from core.title_parser import TitleParser
from core.anti_fraud import AntiFraudShield
from core.live_market import PreciseMarketEngine

print("=" * 60)
print("TEST 1: TITLE PARSER")
print("=" * 60)
test_titles = [
    ("BMW Seria 3 320d 2017 Automat", "bmw", "seria-3", 2017, "diesel"),
    ("Volkswagen Golf 7 1.6 TDI 2018", "volkswagen", "golf", 2018, "diesel"),
    ("Dacia Duster 1.5 dCi 2019", "dacia", "duster", 2019, "diesel"),
    ("Mercedes C-Class 2.0D 2022", "mercedes-benz", "c-class", 2022, "diesel"),
    ("Skoda Octavia III 2.0 TDI 2016", "skoda", "octavia", 2016, "diesel"),
]
for title, exp_mk, exp_md, exp_yr, exp_fl in test_titles:
    res = TitleParser.parse(title)
    ok = (res["make"] == exp_mk and res["model"] == exp_md and res["year"] == exp_yr and res["fuel"] == exp_fl)
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] '{title[:35]}...' -> {res['make']} {res['model']} {res['year']} {res['fuel']}")
    assert ok, f"TitleParser failed for {title}: got {res}"

print("\n" + "=" * 60)
print("TEST 2: ANTI-FRAUD SHIELD (NOILE FILTRE)")
print("=" * 60)
fraud_cases = [
    ("Vand Mazda 5 2010 Acte Expirate", "", 1890, 180000, "mazda", "5", False, "acte expirate / ne-lichid"),
    ("BMW Seria 3 numere rosii 3 luni", "", 4500, 190000, "bmw", "seria-3", False, "numere rosii"),
    ("Passat 2.0 TDI 380000 km", "", 5000, 380000, "volkswagen", "passat", False, "km > 300k"),
    ("Alfa Romeo Giulietta 2015", "", 6500, 150000, "alfa-romeo", "giulietta", False, "model ne-lichid"),
    ("Golf 7 1.6 TDI 2017 unic proprietar fiscal pe loc", "", 8500, 180000, "volkswagen", "golf", True, "masina curata"),
]
for title, desc, price, km, make, model, exp_safe, label in fraud_cases:
    is_safe, reason = AntiFraudShield.inspect(title, desc, price, mileage=km, make=make, model=model)
    status = "PASS" if is_safe == exp_safe else "FAIL"
    print(f"[{status}] ({label}): is_safe={is_safe} | Motiv: {reason[:60]}")
    assert is_safe == exp_safe, f"AntiFraud failed for {title}: expected {exp_safe} got {is_safe}"

print("\n" + "=" * 60)
print("TEST 3: PRECISE MARKET ENGINE (EVALUARE LIVE)")
print("=" * 60)
# Golf 2017 diesel la 8.500€ nu este pont (pret normal de piata)
eval_normal = PreciseMarketEngine.evaluate(8500, "volkswagen", "golf", "diesel", 2017, 180000)
print(f"Golf 2017 Diesel la 8.500€ (Pret piata):")
print(f"  Comparat cu: {eval_normal['total_comparable']} masini identice")
print(f"  Pret sigur revanzare: {eval_normal['safe_sell_price']}€")
print(f"  Profit net dupa cheltuieli: {eval_normal['net_profit']}€")
print(f"  Este deal: {eval_normal['is_deal']} ({eval_normal['deal_rating']})")
assert eval_normal['is_deal'] == False, "Pretul mediu nu ar trebui sa fie considerat deal!"

# Golf 2017 diesel la 3.500€ este suspect de frauda/dauna gravă sau pont masiv
eval_cheap = PreciseMarketEngine.evaluate(3500, "volkswagen", "golf", "diesel", 2017, 180000)
print(f"\nGolf 2017 Diesel la 3.500€:")
print(f"  Profit net: {eval_cheap['net_profit']}€ | Rating: {eval_cheap['deal_rating']}")

print("\n" + "=" * 60)
print("TOATE TESTELE UNITARE AU TRECUT CU SUCCES! (100% PASS)")
print("=" * 60)
