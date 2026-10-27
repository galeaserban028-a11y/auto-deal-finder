import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # ruleaza din orice folder
import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")

from scrapers.carzz import CarZZScraper

items = CarZZScraper.fetch_latest_listings(max_items=8)
print(f"Total listings fetched from CarZZ.ro: {len(items)}")
for i in items:
    print(f"  {i['title']} | Make: {i['make']} | Model: {i['model']} | Year: {i['year']} | Price: {i['price_eur']}€ | KM: {i['mileage']} | Fuel: {i['fuel']}")
