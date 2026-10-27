import requests, json
from bs4 import BeautifulSoup

url = 'https://www.autovit.ro/autoturisme/volkswagen/golf?search[filter_float_year:from]=2015&search[filter_float_year:to]=2019&search[filter_enum_fuel_type][0]=diesel&search[order]=filter_float_price:asc'
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
r = requests.get(url, headers=headers)
soup = BeautifulSoup(r.text, 'html.parser')
script = soup.find('script', id='__NEXT_DATA__')
data = json.loads(script.string)
urql = data['props']['pageProps']['urqlState']
for k, v in urql.items():
    ds = v.get('data')
    if ds and 'advertSearch' in ds:
        parsed = json.loads(ds)
        edges = parsed['advertSearch']['edges']
        print('Total edges returned:', len(edges))
        for edge in edges[:10]:
            node = edge['node']
            title = node.get('title')
            price = node.get('price', {}).get('amount', {}).get('units')
            params = {p['key']: p['value'] for p in node.get('parameters', [])}
            print(f"Year: {params.get('year')} | Price: {price} | Title: {title[:40]}")
        break
