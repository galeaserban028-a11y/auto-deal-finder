import sys, re
import requests
from bs4 import BeautifulSoup

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
r = requests.get('https://www.publi24.ro/anunturi/auto-moto/masini-second-hand/', headers=headers)
soup = BeautifulSoup(r.text, 'html.parser')
cards = soup.find_all('div', class_='article-content-wrap')

print(f"Total cards Publi24: {len(cards)}")
for i, card in enumerate(cards[:10]):
    text = card.get_text(" | ", strip=True)
    safe_text = text.encode('ascii', errors='replace').decode('ascii')
    print(f"[{i}] {safe_text}")
    print("-" * 60)
