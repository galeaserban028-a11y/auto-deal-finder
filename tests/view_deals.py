import sqlite3

conn = sqlite3.connect("car_deals.db")
conn.row_factory = sqlite3.Row
c = conn.cursor()
c.execute("""
    SELECT l.id, l.title, l.make, l.model, l.year, l.fuel, l.price_eur, 
           d.floor_price, d.median_price, d.discount_pct, d.net_profit, d.deal_rating, l.url, l.source
    FROM deals d 
    JOIN listings l ON d.listing_id = l.id
    ORDER BY d.net_profit DESC
""")
rows = c.fetchall()
print(f"Total deals gasite: {len(rows)}\n")
for r in rows:
    print(f"[{r['deal_rating']}] {r['make'].upper()} {r['model'].upper()} ({r['year']}) - {r['fuel']}")
    print(f"  Pret cerut: {r['price_eur']:,.0f} EUR")
    print(f"  Pret piata comparabila: {r['median_price']:,.0f} EUR (-{r['discount_pct']:.1f}%)")
    print(f"  PROFIT NET (dupa 1050 EUR cheltuieli): +{r['net_profit']:,.0f} EUR")
    print(f"  Sursa: {r['source']} | URL: {r['url']}")
    print("-" * 60)
conn.close()
