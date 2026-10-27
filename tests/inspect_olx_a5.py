import subprocess
from bs4 import BeautifulSoup

cmd = ['curl.exe', '-s', '-A', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36', 'https://www.olx.ro/d/oferta/audi-a5-s-line-2016-euro-6-automat-distronic-keyless-led-IDkUaCy.html']
res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
html = res.stdout.decode('utf-8', errors='ignore')
soup = BeautifulSoup(html, 'html.parser')

desc_el = soup.find('div', {'data-cy': 'ad_description'})
if not desc_el:
    desc_el = soup.find('div', class_=lambda c: c and 'css-bgzo2k' in c)
if not desc_el:
    desc_el = soup.find(id='textContent')

print("Title:", soup.find('h4').text if soup.find('h4') else "N/A")
desc_text = desc_el.get_text(" ", strip=True) if desc_el else (soup.get_text(" ", strip=True)[:1000])
with open("tests/audi_a5_olx.txt", "w", encoding="utf-8") as f:
    f.write(desc_text)
print("Saved audi_a5_olx.txt")
