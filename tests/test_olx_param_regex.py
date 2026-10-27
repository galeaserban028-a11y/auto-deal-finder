import sys, re
import subprocess
from bs4 import BeautifulSoup

cmd = ['curl.exe', '-s', '-A', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36', 'https://www.olx.ro/auto-masini-moto-ambarcatiuni/autoturisme/']
res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
html = res.stdout.decode('utf-8', errors='ignore')
soup = BeautifulSoup(html, 'html.parser')
cards = soup.find_all('div', {'data-cy': 'l-card'})

print(f"Total cards: {len(cards)}")
for i, card in enumerate(cards[:15]):
    title_el = card.find("h4") or card.find("h6")
    title = title_el.text.strip() if title_el else "N/A"

    card_text = card.get_text(" ", strip=True)

    # 1. Cautam iconul sau spanul cu km si an
    # Ex: '2015  145 200 km'
    match_param = re.search(r"\b(19\d\d|20\d\d)\s+(\d+[\s\.]*\d*)\s*km\b", card_text, re.IGNORECASE)
    if match_param:
        year = int(match_param.group(1))
        km_str = match_param.group(2).replace(" ", "").replace(".", "")
        mileage = int(km_str) if km_str.isdigit() else 0
        status = f"PARAM-EXACT: Year={year}, Km={mileage:,}"
    else:
        # Fallback cautare an separat
        year_match = re.search(r"\b(19\d\d|200\d|201\d|202\d)\b", card_text)
        year = int(year_match.group(1)) if year_match else 0
        status = f"YEAR-ONLY: Year={year}"

    safe_title = title.encode('ascii', errors='replace').decode('ascii')
    print(f"[{i:2d}] {status:35s} | {safe_title[:50]}")
