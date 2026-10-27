import requests, json
from bs4 import BeautifulSoup

urls = [
    ("Passat 2000 EUR", "https://www.autovit.ro/autoturisme/anunt/volkswagen-passat-ver-1-4-tsi-highline-ID7HQGAC.html"),
    ("Megane 2200 EUR", "https://www.autovit.ro/autoturisme/anunt/renault-megane-ver-1-4-tce-gt-line-ID7HQIAM.html"),
    ("A4 Avant 15550 EUR", "https://www.olx.ro/d/oferta/audi-a4-avant-40-tfsi-quattro-IDkP4CV.html"),
]

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

for name, url in urls:
    print("=" * 60)
    print(name, url)
    print("=" * 60)
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.text, "html.parser")
    # print text
    text = soup.get_text(" ", strip=True)
    # look for red flags
    red_flags = ["dreapta", "anglia", "uk", "defect", "avariat", "lovit", "rate", "tva", "leasing", "motor", "cutie", "probleme"]
    found = [rf for rf in red_flags if rf in text.lower()]
    print("Found red flag words:", found)
    # print description snippet
    desc = soup.find("div", {"data-testid": "ad-description"}) or soup.find(id="textContent") or soup.find("div", {"data-cy": "ad_description"})
    if desc:
        print("Description:", desc.get_text(" ", strip=True)[:400])
    else:
        print("Body snippet:", text[:300])
