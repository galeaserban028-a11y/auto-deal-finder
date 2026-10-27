import sys
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from core.live_market import PreciseMarketEngine

print('Testing Golf diesel 2017...')
r = PreciseMarketEngine.evaluate(6500, 'volkswagen', 'golf', 'diesel', 2017, 150000)
print(f'Comparable: {r.get("total_comparable")} | Safe sell: {r.get("safe_sell_price")} | Profit: {r.get("net_profit")} | Deal: {r.get("is_deal")} | Rating: {r.get("deal_rating")}')
if "market_prices_sample" in r:
    print(f'Market sample: {r["market_prices_sample"][:5]}')
