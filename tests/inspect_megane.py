import requests, json
from bs4 import BeautifulSoup

url = "https://www.autovit.ro/autoturisme/anunt/renault-megane-ver-1-4-tce-gt-line-ID7HQIAM.html"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
r = requests.get(url, headers=headers)
soup = BeautifulSoup(r.text, "html.parser")
script = soup.find("script", id="__NEXT_DATA__")
if script:
    data = json.loads(script.string)
    adv = data['props']['pageProps']['advert']
    print("Title:", adv.get('title'))
    print("Price:", adv.get('price'))
    desc = adv.get('description', '')
    safe_desc = desc.encode('ascii', errors='replace').decode('ascii')
    print("Description:\n", safe_desc)
