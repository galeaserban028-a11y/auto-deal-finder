import sys
import subprocess
from bs4 import BeautifulSoup

cmd = ['curl.exe', '-s', '-A', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36', 'https://www.olx.ro/auto-masini-moto-ambarcatiuni/autoturisme/']
res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
html = res.stdout.decode('utf-8', errors='ignore')
soup = BeautifulSoup(html, 'html.parser')
cards = soup.find_all('div', {'data-cy': 'l-card'})
print(f'Total cards: {len(cards)}')
for i, card in enumerate(cards[:10]):
    text = card.get_text(" | ", strip=True)
    safe_text = text.encode('ascii', errors='replace').decode('ascii')
    print(f"Card {i}: {safe_text}")
    print("-" * 80)
