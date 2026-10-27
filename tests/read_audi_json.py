import json

with open('tests/audi_a4_details.json', encoding='utf-8') as f:
    d = json.load(f)

ad = d['props']['pageProps']['advert']
print('Title:', ad.get('title'))
print('Price:', ad.get('price'))
print('\nParameters:')
for p in ad.get('parameters', []):
    print(f"  {p.get('key')}: {p.get('value')} ({p.get('displayValue')})")
print('\nDescription:')
print(ad.get('description', ''))
