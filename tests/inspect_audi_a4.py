import requests, json
from bs4 import BeautifulSoup

url = "https://www.autovit.ro/autoturisme/anunt/audi-a4-ID7HQEQf.html"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
r = requests.get(url, headers=headers)
soup = BeautifulSoup(r.text, "html.parser")
script = soup.find("script", id="__NEXT_DATA__")
if script:
    data = json.loads(script.string)
    # save to json to inspect
    with open("tests/audi_a4_details.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print("Saved audi_a4_details.json")
