import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # ruleaza din orice folder
import sys
sys.path.insert(0, ".")
from core.live_market import PreciseMarketEngine

print("Evaluating Volkswagen Golf 6 at 3.999 EUR with REAL year 2010:")
r = PreciseMarketEngine.evaluate(
    listing_price=3999.0,
    make="volkswagen",
    model="golf",
    fuel="benzina",
    year=2010,
    mileage=220000
)
print(f"  Total comparable 2008-2012 Golf benzina: {r.get('total_comparable')}")
print(f"  Cheapest on market: {r.get('cheapest_on_market')} EUR")
print(f"  Safe sell price: {r.get('safe_sell_price')} EUR")
print(f"  Net profit: {r.get('net_profit')} EUR")
print(f"  Is deal: {r.get('is_deal')} | Rating: {r.get('deal_rating')}")
print(f"  Market sample: {r.get('market_prices_sample', [])[:5]}")
