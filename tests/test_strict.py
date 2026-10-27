import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # ruleaza din orice folder
"""Quick test of the ultra-strict engine with year filtering."""
import sys
sys.path.insert(0, ".")
from core.live_market import UltraStrictProfitEngine

# Clear cache for fresh results
from core.live_market import _MARKET_CACHE
_MARKET_CACHE.clear()

print("=== Test 1: VW Golf 2017 la 8.500 EUR ===")
r1 = UltraStrictProfitEngine.evaluate(8500.0, "volkswagen", "golf", year=2017)
print(f"  Cel mai ieftin Golf 2015-2019 pe piata: {r1['cheapest_on_market']} EUR")
print(f"  Cu {r1['pct_below_cheapest']:.1f}% sub el")
print(f"  Profit net: {r1['net_profit']} EUR")
print(f"  Is deal: {r1['is_deal']} | Rating: {r1['deal_rating']}")
print(f"  Masini similare gasite: {r1['total_comparable']}")
print(f"  Primele 5 preturi: {r1['market_prices_sample'][:5]}")
print()

print("=== Test 2: VW Passat 2018 la 9.000 EUR ===")
r2 = UltraStrictProfitEngine.evaluate(9000.0, "volkswagen", "passat", year=2018)
print(f"  Cel mai ieftin Passat 2016-2020 pe piata: {r2['cheapest_on_market']} EUR")
print(f"  Cu {r2['pct_below_cheapest']:.1f}% sub el")
print(f"  Profit net: {r2['net_profit']} EUR")
print(f"  Is deal: {r2['is_deal']} | Rating: {r2['deal_rating']}")
print(f"  Masini similare gasite: {r2['total_comparable']}")
print(f"  Primele 5 preturi: {r2['market_prices_sample'][:5]}")
print()

print("=== Test 3: Dacia Duster 2018 la 5.000 EUR (ar fi un chilipir real?) ===")
r3 = UltraStrictProfitEngine.evaluate(5000.0, "dacia", "duster", year=2018)
print(f"  Cel mai ieftin Duster 2016-2020 pe piata: {r3['cheapest_on_market']} EUR")
print(f"  Cu {r3['pct_below_cheapest']:.1f}% sub el")
print(f"  Profit net: {r3['net_profit']} EUR")
print(f"  Is deal: {r3['is_deal']} | Rating: {r3['deal_rating']}")
print(f"  Primele 5 preturi: {r3['market_prices_sample'][:5]}")
print()

print("=== Test 4: Skoda Octavia 2019 la 9.500 EUR ===")
r4 = UltraStrictProfitEngine.evaluate(9500.0, "skoda", "octavia", year=2019)
print(f"  Cel mai ieftin Octavia 2017-2021 pe piata: {r4['cheapest_on_market']} EUR")
print(f"  Cu {r4['pct_below_cheapest']:.1f}% sub el")
print(f"  Profit net: {r4['net_profit']} EUR")
print(f"  Is deal: {r4['is_deal']} | Rating: {r4['deal_rating']}")
print(f"  Primele 5 preturi: {r4['market_prices_sample'][:5]}")
