import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # ruleaza din orice folder
import sys
sys.path.insert(0, ".")
from core.title_parser import TitleParser

cases = [
    ("Volkswagen Golf 6/1.6 Mpi /220000 km", 2010),
    ("BMW F10 520d Luxury Line", 2013),
    ("Passat B7 2.0 TDI DSG", 2012),
    ("Passat B8 2.0 TDI Highline", 2016),
    ("Golf 7 1.6 TDI", 2015),
    ("Audi A4 B8 2.0 TDI", 2011),
    ("Skoda Octavia 3 2.0 TDI", 2016),
    ("BMW E60 525d", 2006),
]

for title, exp_year in cases:
    res = TitleParser.parse(title)
    print(f"'{title[:30]:30s}' -> Make: {res['make']:12s} Model: {res['model']:10s} Year: {res['year']} (Expected: {exp_year})")
    assert res['year'] == exp_year, f"Failed for {title}: got {res['year']}, expected {exp_year}"

print("\nALL GENERATION TESTS PASSED!")
