"""
Modul de parsare al titlurilor pentru anunturi auto (OLX.ro, Publi24.ro etc.)
Extrage marca (make), modelul (model), anul de fabricatie (year) si combustibilul (fuel)
dintr-un titlu brut in limba romana.
"""

import re
from typing import Dict, Any, Optional, List, Tuple


class TitleParser:
    """
    Parser robust pentru titluri de anunturi auto romanesti.
    Normalizeaza marci, modele si detecteaza combustibilul si anul.
    """

    # 1. Mapare de tipare pentru identificarea marcilor (Make detection)
    MAKE_PATTERNS: List[Tuple[str, str]] = [
        (r"\b(?:volkswagen|vw)\b", "volkswagen"),
        (r"\b(?:mercedes[- ]benz|mercedes|merc)\b", "mercedes-benz"),
        (r"\bbmw\b", "bmw"),
        (r"\baudi\b", "audi"),
        (r"\b(?:skoda|škoda)\b", "skoda"),
        (r"\bdacia\b", "dacia"),
        (r"\bford\b", "ford"),
        (r"\brenault\b", "renault"),
        (r"\bopel\b", "opel"),
        (r"\bhyundai\b", "hyundai"),
        (r"\bkia\b", "kia"),
        (r"\btoyota\b", "toyota"),
        (r"\bpeugeot\b", "peugeot"),
        (r"\bseat\b", "seat"),
        (r"\bvolvo\b", "volvo"),
        (r"\bnissan\b", "nissan"),
        (r"\bmazda\b", "mazda"),
        (r"\bhonda\b", "honda"),
        (r"\bsuzuki\b", "suzuki"),
        (r"\bmitsubishi\b", "mitsubishi"),
        (r"\babarth\b", "abarth"),
        (r"\bsmart\b", "smart"),
        (r"\bcupra\b", "cupra"),
        (r"\bfiat\b", "fiat"),
        (r"\b(?:alfa[- ]romeo|alfa)\b", "alfa-romeo"),
        (r"\b(?:citroen|citroën)\b", "citroen"),
        (r"\b(?:land[- ]rover|range[- ]rover)\b", "land-rover"),
        (r"\bjeep\b", "jeep"),
        (r"\bmini\b", "mini"),
        (r"\bporsche\b", "porsche"),
        (r"\bjaguar\b", "jaguar"),
        (r"\bsubaru\b", "subaru"),
        (r"\blexus\b", "lexus"),
        (r"\b(?:chevrolet|chevy)\b", "chevrolet"),
    ]

    # 2. Mapare modele per marca (Patterns ordonate de la specific la general)
    MODEL_PATTERNS: Dict[str, List[Tuple[str, Any]]] = {
        "volkswagen": [
            (r"\bt[- ]?cross\b", "t-cross"),
            (r"\bt[- ]?roc\b", "t-roc"),
            (r"\bpassat(?:\s+cc)?\b", "passat"),
            (r"\bgolf(?:\s+(?:plus|sportsvan|[1-8]|v?i{1,3}|iv|v|vi|vii|viii))?\b", "golf"),
            (r"\btiguan\b", "tiguan"),
            (r"\bpolo\b", "polo"),
            (r"\btouran\b", "touran"),
            (r"\barteon\b", "arteon"),
            (r"\bcaddy\b", "caddy"),
            (r"\bup!?\b", "up"),
            (r"\btouareg\b", "touareg"),
            (r"\bsharan\b", "sharan"),
            (r"\bscirocco\b", "scirocco"),
            (r"\bjetta\b", "jetta"),
            (r"\btaigo\b", "taigo"),
            (r"\bamarok\b", "amarok"),
            (r"\btransporter\b", "transporter"),
            (r"\bmultivan\b", "multivan"),
            (r"\bcaravelle\b", "caravelle"),
        ],
        "bmw": [
            # 'seria 3', 'seria-3', 'series 3', 'ser 3', 'ser. 3'
            (r"\b(?:seria|series|ser\.?)\s*[-]?\s*([1-8])\b", lambda m: f"seria-{m.group(1)}"),
            # X1 - X7
            (r"\bx\s*[-]?\s*([1-7])\b", lambda m: f"x{m.group(1)}"),
            # Modele cu 3 cifre: 320d, 520, 118d, 730d -> seria-X
            (r"\b([1-8])(?:1[4-9]|2[0-9]|3[0-9]|4[0-9]|5[0-9]|6[0-9])[a-z]?\b", lambda m: f"seria-{m.group(1)}"),
            # i3, i4, i8, ix
            (r"\bi([348])\b", lambda m: f"i{m.group(1)}"),
            (r"\bix\s*([1-3])?\b", lambda m: f"ix{m.group(1)}" if m.group(1) else "ix"),
            # M2, M3, M4, M5, M6
            (r"\bm([2-6])\b", lambda m: f"seria-{m.group(1)}"),
        ],
        "mercedes-benz": [
            # Modele compuse intai (GLA, GLB, GLC, GLE, GLS, CLA, CLS, ML)
            (r"\b(?:clasa[- ]?gla|gla[- ]?class|gla)\s*[-]?\s*(?:180|200|220|250|35|45)?\b", "gla"),
            (r"\b(?:clasa[- ]?glb|glb[- ]?class|glb)\s*[-]?\s*(?:180|200|220|250|35)?\b", "glb"),
            (r"\b(?:clasa[- ]?glc|glc[- ]?class|glc)\s*[-]?\s*(?:200|220|250|300|350|400|43|63)?\b", "glc"),
            (r"\b(?:clasa[- ]?gle|gle[- ]?class|gle)\s*[-]?\s*(?:250|300|350|400|450|500|53|63)?\b", "gle"),
            (r"\b(?:clasa[- ]?gls|gls[- ]?class|gls)\s*[-]?\s*(?:350|400|450|500|580|63)?\b", "gls"),
            (r"\b(?:clasa[- ]?cla|cla[- ]?class|cla)\s*[-]?\s*(?:180|200|220|250|35|45)?\b", "cla"),
            (r"\b(?:clasa[- ]?cls|cls[- ]?class|cls)\s*[-]?\s*(?:220|250|300|320|350|400|450|500|53|63)?\b", "cls"),
            (r"\b(?:clasa[- ]?ml|ml[- ]?class|ml)\s*[-]?\s*(?:250|270|280|300|320|350|400|500)?\b", "ml"),
            # C-Class: clasa c, c-class, c class, c200, c220, etc.
            (r"\b(?:clasa[- ]?c|c[- ]?class|c[- ]?klasse|c\s*[-]?\s*(?:160|180|200|220|230|240|250|270|280|300|320|350|400|43|63)[a-z]?)\b", "c-class"),
            # E-Class: clasa e, e-class, e class, e200, e220, etc.
            (r"\b(?:clasa[- ]?e|e[- ]?class|e[- ]?klasse|e\s*[-]?\s*(?:200|220|240|250|270|280|300|320|350|400|420|450|500|43|53|63)[a-z]?)\b", "e-class"),
            # A-Class: clasa a, a-class, a class, a180, a200, etc.
            (r"\b(?:clasa[- ]?a|a[- ]?class|a[- ]?klasse|a\s*[-]?\s*(?:140|150|160|170|180|190|200|210|220|250|35|45)[a-z]?)\b", "a-class"),
            # B-Class: clasa b, b-class, b class, b180, b200, etc.
            (r"\b(?:clasa[- ]?b|b[- ]?class|b[- ]?klasse|b\s*[-]?\s*(?:150|160|170|180|200|220|250)[a-z]?)\b", "b-class"),
            # S-Class: clasa s, s-class, s class, s320, s350, s500, etc.
            (r"\b(?:clasa[- ]?s|s[- ]?class|s[- ]?klasse|s\s*[-]?\s*(?:300|320|350|400|420|450|500|550|560|580|600|63|65)[a-z]?)\b", "s-class"),
            # Utilitare & Altele
            (r"\bvito\b", "vito"),
            (r"\bsprinter\b", "sprinter"),
            (r"\bv[- ]?class\b", "v-class"),
            (r"\bg[- ]?class\b", "g-class"),
        ],
        "audi": [
            (r"\be[- ]?tron\b", "e-tron"),
            (r"\ba[- ]?([1-8])\b", lambda m: f"a{m.group(1)}"),
            (r"\bq[- ]?([2-8])\b", lambda m: f"q{m.group(1)}"),
            (r"\brs[- ]?([3-7])\b", lambda m: f"rs{m.group(1)}"),
            (r"\bs[- ]?([3-8])\b", lambda m: f"s{m.group(1)}"),
            (r"\btt\b", "tt"),
        ],
        "skoda": [
            (r"\boctavia\b", "octavia"),
            (r"\bsuperb\b", "superb"),
            (r"\bfabia\b", "fabia"),
            (r"\brapid\b", "rapid"),
            (r"\bscala\b", "scala"),
            (r"\bkodiaq\b", "kodiaq"),
            (r"\bkaroq\b", "karoq"),
            (r"\bkamiq\b", "kamiq"),
            (r"\bcitigo\b", "citigo"),
            (r"\byeti\b", "yeti"),
            (r"\broomster\b", "roomster"),
        ],
        "dacia": [
            (r"\bduster\b", "duster"),
            (r"\blogan\b", "logan"),
            (r"\bsandero\b", "sandero"),
            (r"\bjogger\b", "jogger"),
            (r"\bdokker\b", "dokker"),
            (r"\bspring\b", "spring"),
            (r"\blodgy\b", "lodgy"),
        ],
        "ford": [
            (r"\beco[- ]?sport\b", "ecosport"),
            (r"\bc[- ]?max\b", "c-max"),
            (r"\bs[- ]?max\b", "s-max"),
            (r"\bfocus\b", "focus"),
            (r"\bmondeo\b", "mondeo"),
            (r"\bkuga\b", "kuga"),
            (r"\bfiesta\b", "fiesta"),
            (r"\bpuma\b", "puma"),
            (r"\bgalaxy\b", "galaxy"),
            (r"\branger\b", "ranger"),
            (r"\btransit\b", "transit"),
            (r"\bedge\b", "edge"),
            (r"\bka\+?\b", "ka"),
        ],
        "renault": [
            (r"\bgrand\s+scenic\b", "grand-scenic"),
            (r"\bmegane\b", "megane"),
            (r"\bclio\b", "clio"),
            (r"\bkadjar\b", "kadjar"),
            (r"\btalisman\b", "talisman"),
            (r"\bcaptur\b", "captur"),
            (r"\bscenic\b", "scenic"),
            (r"\bkoleos\b", "koleos"),
            (r"\bzoe\b", "zoe"),
            (r"\blaguna\b", "laguna"),
            (r"\bsymbol\b", "symbol"),
            (r"\barkana\b", "arkana"),
            (r"\baustral\b", "austral"),
        ],
        "hyundai": [
            (r"\bsanta[- ]?fe\b", "santa-fe"),
            (r"\btucson\b", "tucson"),
            (r"\bi30\b", "i30"),
            (r"\bi20\b", "i20"),
            (r"\bi10\b", "i10"),
            (r"\bi40\b", "i40"),
            (r"\bix35\b", "ix35"),
            (r"\bix20\b", "ix20"),
            (r"\bkona\b", "kona"),
            (r"\belantra\b", "elantra"),
            (r"\bioniq\b", "ioniq"),
            (r"\bbayon\b", "bayon"),
        ],
        "kia": [
            (r"\bpro[- ]?cee['’]?d\b", "proceed"),
            (r"\bx[- ]?ceed\b", "xceed"),
            (r"\b(?:cee['’]?d|ceed)\b", "ceed"),
            (r"\bsportage\b", "sportage"),
            (r"\brio\b", "rio"),
            (r"\bsorento\b", "sorento"),
            (r"\bstonic\b", "stonic"),
            (r"\bniro\b", "niro"),
            (r"\bpicanto\b", "picanto"),
            (r"\boptima\b", "optima"),
            (r"\bcarens\b", "carens"),
        ],
        "toyota": [
            (r"\bland[- ]?cruiser\b", "land-cruiser"),
            (r"\brav[- ]?4\b", "rav4"),
            (r"\bc[- ]?hr\b", "chr"),
            (r"\bcorolla\b", "corolla"),
            (r"\byaris\b", "yaris"),
            (r"\bauris\b", "auris"),
            (r"\bavensis\b", "avensis"),
            (r"\bcamry\b", "camry"),
            (r"\bprius\b", "prius"),
            (r"\baygo\b", "aygo"),
            (r"\bhilux\b", "hilux"),
        ],
        "opel": [
            (r"\bcrossland(?:\s*x)?\b", "crossland"),
            (r"\bgrandland(?:\s*x)?\b", "grandland"),
            (r"\bmokka(?:\s*x)?\b", "mokka"),
            (r"\bastra\b", "astra"),
            (r"\bcorsa\b", "corsa"),
            (r"\binsignia\b", "insignia"),
            (r"\bzafira\b", "zafira"),
            (r"\bmeriva\b", "meriva"),
            (r"\bvectra\b", "vectra"),
            (r"\badam\b", "adam"),
            (r"\bantara\b", "antara"),
        ],
        "peugeot": [
            # 4 cifre intai (3008, 5008, 2008) ca sa nu se potriveasca partial
            (r"\b3008\b", "3008"),
            (r"\b5008\b", "5008"),
            (r"\b2008\b", "2008"),
            (r"\b308\b", "308"),
            (r"\b508\b", "508"),
            (r"\b208\b", "208"),
            (r"\b108\b", "108"),
            (r"\b206\b", "206"),
            (r"\b207\b", "207"),
            (r"\b307\b", "307"),
            (r"\b407\b", "407"),
            (r"\brcz\b", "rcz"),
            (r"\bpartner\b", "partner"),
            (r"\brifter\b", "rifter"),
        ],
        "seat": [
            (r"\bleon\b", "leon"),
            (r"\bibiza\b", "ibiza"),
            (r"\barona\b", "arona"),
            (r"\bateca\b", "ateca"),
            (r"\btarraco\b", "tarraco"),
            (r"\baltea\b", "altea"),
            (r"\btoledo\b", "toledo"),
            (r"\bmii\b", "mii"),
        ],
        "volvo": [
            (r"\bxc[- ]?60\b", "xc60"),
            (r"\bxc[- ]?90\b", "xc90"),
            (r"\bxc[- ]?40\b", "xc40"),
            (r"\bv[- ]?40\b", "v40"),
            (r"\bv[- ]?60\b", "v60"),
            (r"\bs[- ]?60\b", "s60"),
            (r"\bs[- ]?90\b", "s90"),
            (r"\bv[- ]?90\b", "v90"),
            (r"\bs[- ]?40\b", "s40"),
            (r"\bs[- ]?80\b", "s80"),
            (r"\bv[- ]?50\b", "v50"),
            (r"\bc[- ]?30\b", "c30"),
        ],
        "nissan": [
            (r"\bx[- ]?trail\b", "x-trail"),
            (r"\bqashqai(?:\+2)?\b", "qashqai"),
            (r"\bjuke\b", "juke"),
            (r"\bmicra\b", "micra"),
            (r"\bleaf\b", "leaf"),
            (r"\bnavara\b", "navara"),
            (r"\bpulsar\b", "pulsar"),
        ],
        "mazda": [
            (r"\bcx[- ]?30\b", "cx-30"),
            (r"\bcx[- ]?5\b", "cx-5"),
            (r"\bcx[- ]?3\b", "cx-3"),
            (r"\bcx[- ]?60\b", "cx-60"),
            (r"\bmx[- ]?5\b", "mx-5"),
            (r"\b(?:mazda\s*)?3\b", "3"),
            (r"\b(?:mazda\s*)?6\b", "6"),
        ],
        "honda": [
            (r"\bcivic\b", "civic"),
            (r"\bcr[- ]?v\b", "cr-v"),
            (r"\bhr[- ]?v\b", "hr-v"),
            (r"\baccord\b", "accord"),
            (r"\bjazz\b", "jazz"),
        ],
        "suzuki": [
            (r"\bs[- ]?cross\b", "s-cross"),
            (r"\bvitara\b", "vitara"),
            (r"\bsx4\b", "sx4"),
            (r"\bswift\b", "swift"),
            (r"\bjimny\b", "jimny"),
            (r"\bignis\b", "ignis"),
        ],
        "citroen": [
            (r"\bc3\s+aircross\b", "c3-aircross"),
            (r"\bc5\s+aircross\b", "c5-aircross"),
            (r"\bc3\b", "c3"),
            (r"\bc4\b", "c4"),
            (r"\bc5\b", "c5"),
            (r"\bberlingo\b", "berlingo"),
        ],
    }

    # 3. Detectie combustibil
    FUEL_PATTERNS: List[Tuple[str, str]] = [
        # Electric
        (r"\b(?:electric[aă]?|electrica|ev)\b", "electric"),
        # Hybrid
        (r"\b(?:hybrid|hibrid|phev|mhev|plug-?in)\b", "hybrid"),
        # GPL
        (r"\b(?:gpl|lpg)\b", "gpl"),
        # Diesel
        (
            r"\b(?:diesel|tdi|dci|cdti|crdi|hdi|bluetec|bluehdi|d4d|d-4d|cdi|tdci|ddis|jtd|multijet|mjet)\b"
            r"|\b\d\.\d\s*d\b"
            r"|\b\d{3}d\b"
            r"|\b\d{3}\s*cdi\b",
            "diesel",
        ),
        # Benzina
        (
            r"\b(?:benzina|benzină|tsi|tfsi|ecoboost|mpi|gdi|skyactiv[- ]?g|tce|puretech|vtec|vti|fsi|cgi|kompressor)\b"
            r"|\b\d{3}i\b"
            r"|\b\d\.\d\s*i\b",
            "benzina",
        ),
    ]

    @classmethod
    def extract_make(cls, title: str) -> str:
        """Identifica marca din titlu pe baza tiparelor cunoscute."""
        earliest_make = "necunoscut"
        earliest_pos = float("inf")

        for pattern, make_name in cls.MAKE_PATTERNS:
            m = re.search(pattern, title, re.IGNORECASE)
            if m and m.start() < earliest_pos:
                earliest_pos = m.start()
                earliest_make = make_name

        return earliest_make

    @classmethod
    def extract_model(cls, title: str, make: str) -> Tuple[str, str]:
        """
        Extrage modelul corespunzator marcii.
        Daca marca este necunoscuta, cauta un model specific pentru a deduce si marca.
        Returneaza tuplu (make, model).
        """
        # Cazul 1: Marca a fost deja detectata
        if make in cls.MODEL_PATTERNS:
            for pattern, target in cls.MODEL_PATTERNS[make]:
                m = re.search(pattern, title, re.IGNORECASE)
                if m:
                    model_val = target(m) if callable(target) else target
                    return make, model_val

        # Cazul 2: Marca nu este in lista sau este necunoscuta - cautam printre toate marcile.
        # Deducem marca DOAR din nume de model clare (ex: "Golf", "Octavia"), nu din cifre:
        # altfel "Abarth 595 ... 160 CP" devenea "BMW Seria 1" si era comparat cu preturi de BMW.
        if make == "necunoscut":
            for mk, patterns in cls.MODEL_PATTERNS.items():
                for pattern, target in patterns:
                    if callable(target):
                        continue
                    m = re.search(pattern, title, re.IGNORECASE)
                    if m and len(re.sub(r"[^a-z]", "", m.group(0).lower())) >= 3:
                        return mk, target

        return make, "necunoscut"

    @classmethod
    def extract_year(cls, title: str, detected_model: str = "") -> int:
        """
        Extrage anul fabricatiei (2000-2029) folosind expresii regulate.
        Evita confuzia cu cilindreea (2000 cmc), pretul (2000 eur) sau modelul (Peugeot 2008).
        """
        # Cautam 4 cifre in intervalul 2000-2029
        # Excludem daca sunt urmate direct de unitati de masura sau monede
        pattern = r"\b(20[0-2]\d)\b(?!\s*(?:cmc|cm3|cc|eur|euro|€|lei|ron|km|cp|hp|de\s*km))"
        candidates: List[Tuple[int, int]] = []

        for m in re.finditer(pattern, title, re.IGNORECASE):
            start = m.start()
            # Verificam daca este precedat de simbol monetar
            prefix = title[max(0, start - 4):start]
            if any(sym in prefix for sym in ["€", "$"]):
                continue
            year_val = int(m.group(1))
            candidates.append((start, year_val))

        if not candidates:
            # Daca nu exista 4 cifre explicite, deducem anul din codul generatiei (ex: Golf 6 -> 2010, Passat B8 -> 2016)
            title_lower = title.lower()
            generation_rules = [
                (r"\bgolf\s*(?:6|vi)\b", 2010),
                (r"\bgolf\s*(?:7|vii)\b", 2015),
                (r"\bgolf\s*(?:8|viii)\b", 2021),
                (r"\bgolf\s*(?:5|v)\b", 2006),
                (r"\bpassat\s*b6\b", 2008),
                (r"\bpassat\s*b7\b", 2012),
                (r"\bpassat\s*b8\b", 2016),
                (r"\boctavia\s*(?:2|ii)\b", 2008),
                (r"\boctavia\s*(?:3|iii)\b", 2016),
                (r"\boctavia\s*(?:4|iv)\b", 2021),
                (r"\bbmw\s*(?:e60)\b|\be60\b", 2006),
                (r"\bbmw\s*(?:f10)\b|\bf10\b", 2013),
                (r"\bbmw\s*(?:g30)\b|\bg30\b", 2018),
                (r"\bbmw\s*(?:e90|e91|e92)\b|\be90\b", 2008),
                (r"\bbmw\s*(?:f30|f31)\b|\bf30\b", 2014),
                (r"\bbmw\s*(?:g20)\b|\bg20\b", 2020),
                (r"\baudi\s*a4\s*b8\b|\ba4\s*b8\b", 2011),
                (r"\baudi\s*a4\s*b9\b|\ba4\s*b9\b", 2017),
                (r"\baudi\s*a6\s*c6\b|\ba6\s*c6\b", 2008),
                (r"\baudi\s*a6\s*c7\b|\ba6\s*c7\b", 2014),
                (r"\baudi\s*a6\s*c8\b|\ba6\s*c8\b", 2019),
            ]
            for gen_pat, gen_year in generation_rules:
                if re.search(gen_pat, title_lower):
                    return gen_year
            return 0

        # Daca avem mai multi candidati si modelul este '2008' (Peugeot 2008),
        # preferam celalalt an care reprezinta anul de productie
        if len(candidates) > 1 and detected_model == "2008":
            non_2008 = [y for _, y in candidates if y != 2008]
            if non_2008:
                return non_2008[-1]

        # Returnam ultimul an valid gasit in titlu
        return candidates[-1][1]

    @classmethod
    def extract_fuel(cls, title: str) -> str:
        """Detecteaza tipul de combustibil din titlu."""
        for pattern, fuel_type in cls.FUEL_PATTERNS:
            if re.search(pattern, title, re.IGNORECASE):
                return fuel_type
        return "necunoscut"

    @staticmethod
    def parse(title: str) -> Dict[str, Any]:
        """
        Extract make, model, year, fuel from a Romanian car listing title.

        Returns dict with keys:
            make (str): Numele normalizat al marcii (ex: 'bmw', 'volkswagen')
            model (str): Numele normalizat al modelului (ex: 'seria-3', 'golf')
            year (int): Anul de fabricatie (2000-2029) sau 0 daca nu este gasit
            fuel (str): 'diesel', 'benzina', 'hybrid', 'electric', 'gpl' sau 'necunoscut'
        """
        if not title or not isinstance(title, str):
            return {
                "make": "necunoscut",
                "model": "necunoscut",
                "year": 0,
                "fuel": "necunoscut",
            }

        # 1. Detectie Make
        make = TitleParser.extract_make(title)

        # 2. Detectie Model (si posibila deducere de Make)
        make, model = TitleParser.extract_model(title, make)

        # 3. Detectie An
        year = TitleParser.extract_year(title, detected_model=model)

        # 4. Detectie Combustibil
        fuel = TitleParser.extract_fuel(title)

        return {
            "make": make,
            "model": model,
            "year": year,
            "fuel": fuel,
        }


if __name__ == "__main__":
    # Teste de validare
    test_titles = [
        "BMW Seria 3 320d 2017 Automat",
        "Volkswagen Golf 7 1.6 TDI 2018",
        "VW Passat B8 2.0 TDI DSG",
        "Dacia Duster 1.5 dCi 2019",
        "Skoda Octavia III 2.0 TDI",
        "Ford Focus 1.0 EcoBoost 2020",
        "Mercedes C-Class 2.0D 197Cp 2022",
        "Audi A4 2.0 TFSI 2019",
        "Hyundai Tucson 1.6 CRDI 2018",
        "Toyota RAV4 2.0 Hybrid 2021",
        "Renault Megane 4 1.5 DCI 2017",
        "Opel Astra K 1.6 CDTI 2016",
        "Peugeot 3008 1.6 HDI 2017",
    ]

    print(f"{'MAKE':15s} {'MODEL':15s} {'YEAR':6s} {'FUEL':12s}")
    print("-" * 50)
    for t in test_titles:
        res = TitleParser.parse(t)
        print(f"{res['make']:15s} {res['model']:15s} {str(res['year']):6s} {res['fuel']:12s}")
