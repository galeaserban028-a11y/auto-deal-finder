import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # ruleaza din orice folder
"""
Investigatie: de ce motorul crede ca un Mercedes C-Class 2022 la 19.550 EUR
are profit de 8.061 EUR? Sa vedem ce date primeste.
De asemenea, verific cateva din celelalte "dealuri" suspecte.
"""
import sys, json
sys.path.insert(0, ".")
from core.live_market import UltraStrictProfitEngine, _MARKET_CACHE

_MARKET_CACHE.clear()

# 1. Mercedes C-Class 2022 la 19.550 EUR - "profit 8.061 EUR" (SUSPECT)
print("=" * 70)
print("INVESTIGATIE: Mercedes C-Class 2022 la 19.550 EUR")
print("=" * 70)
market1 = UltraStrictProfitEngine.get_cheapest_on_market("mercedes-benz", "c-class", year=2022)
print(f"  Masini C-Class 2020-2024 gasite: {market1['total_listings']}")
print(f"  Cel mai ieftin: {market1['cheapest_price']} EUR")
print(f"  Primele 10 preturi: {market1['all_prices_sorted']}")
r1 = UltraStrictProfitEngine.evaluate(19550, "mercedes-benz", "c-class", year=2022)
print(f"  Verdictul motorului: is_deal={r1['is_deal']}, profit={r1['net_profit']}, rating={r1['deal_rating']}")
print()

# 2. BMW E60 525d la 4.500 EUR - "profit 3.140 EUR" 
print("=" * 70)
print("INVESTIGATIE: BMW E60 525d la 4.500 EUR")
print("=" * 70)
# E60 e din 2003-2010 deci anul ar fi ~2007
market2 = UltraStrictProfitEngine.get_cheapest_on_market("bmw", "seria-5", year=2007)
print(f"  Masini BMW Seria 5 2005-2009 gasite: {market2['total_listings']}")
print(f"  Cel mai ieftin: {market2['cheapest_price']} EUR")
print(f"  Primele 10 preturi: {market2['all_prices_sorted']}")
r2 = UltraStrictProfitEngine.evaluate(4500, "bmw", "seria-5", year=2007)
print(f"  Verdictul motorului: is_deal={r2['is_deal']}, profit={r2['net_profit']}, rating={r2['deal_rating']}")
print()

# 3. Mazda 5 cu ACTE EXPIRATE la 1.890 EUR - "profit 1.050 EUR" (ACTE EXPIRATE!!)
print("=" * 70)
print("INVESTIGATIE: Mazda 5 2010 cu ACTE EXPIRATE la 1.890 EUR")
print("=" * 70)
print("  PROBLEMA: Are 'Acte Expirate' in titlu - asta e un red flag major!")
print("  O masina cu acte expirate nu se poate revinde legal rapid!")
print()

# 4. Volvo XC90 D5 la 7.700 EUR - "profit 6.655 EUR"
print("=" * 70)
print("INVESTIGATIE: Volvo XC90 la 7.700 EUR")
print("=" * 70)
market4 = UltraStrictProfitEngine.get_cheapest_on_market("volvo", "xc90", year=2008)
print(f"  Masini Volvo XC90 2006-2010 gasite: {market4['total_listings']}")
print(f"  Cel mai ieftin: {market4['cheapest_price']} EUR")
print(f"  Primele 10 preturi: {market4['all_prices_sorted']}")
r4 = UltraStrictProfitEngine.evaluate(7700, "volvo", "xc90", year=2008)
print(f"  Verdictul motorului: is_deal={r4['is_deal']}, profit={r4['net_profit']}, rating={r4['deal_rating']}")
print()

# 5. Logan MCV la 5.999 EUR - "profit 1.941 EUR"
print("=" * 70)
print("INVESTIGATIE: Logan MCV la 5.999 EUR")
print("=" * 70)
market5 = UltraStrictProfitEngine.get_cheapest_on_market("dacia", "logan-mcv", year=2018)
print(f"  Masini Logan MCV 2016-2020 gasite: {market5['total_listings']}")
print(f"  Cel mai ieftin: {market5['cheapest_price']} EUR")
print(f"  Primele 10 preturi: {market5['all_prices_sorted']}")
r5 = UltraStrictProfitEngine.evaluate(5999, "dacia", "logan-mcv", year=2018)
print(f"  Verdictul motorului: is_deal={r5['is_deal']}, profit={r5['net_profit']}, rating={r5['deal_rating']}")
