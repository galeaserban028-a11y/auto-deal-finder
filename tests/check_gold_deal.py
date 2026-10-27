import subprocess
from bs4 import BeautifulSoup

url = "https://www.olx.ro/d/oferta/audi-a4-avant-40-tfsi-quattro-IDkP4CV.html"
cmd = ['curl.exe', '-s', '-A', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36', url]
res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
html = res.stdout.decode('utf-8', errors='ignore')
soup = BeautifulSoup(html, 'html.parser')
desc_el = soup.find('div', {'data-cy': 'ad_description'}) or soup.find(id='textContent')
desc_text = desc_el.get_text(" ", strip=True) if desc_el else "N/A"
safe_desc = desc_text.encode('ascii', errors='replace').decode('ascii')
print("Audi A4 Avant 40 TFSI Description:\n", safe_desc[:600])
