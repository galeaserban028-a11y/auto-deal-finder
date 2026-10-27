"""
Anti-Fraud & Anti-Leasing Shield
Elimina 100% capcanele de pe piata auto din Romania:
- Prețuri de avans sau rate lunare deghizate în preț total
- Mașini avariate, lovite, fără motor sau vândute pentru piese
- Anunțuri fără certificat fiscal sau cu probleme legale
- Prețuri suspecte sau accesorii (jante, barete)
- Rulaj excesiv (>300.000 km)
- Modele ne-lichide
"""

import re
import unicodedata
from typing import Tuple, List
from config.settings import LIQUID_MODELS, MIN_LISTING_PRICE_EUR, MAX_LISTING_PRICE_EUR, MAX_MILEAGE_KM, CURRENT_YEAR, MIN_YEAR

# Transliterare diacritice romanesti -> ASCII (lovită -> lovita, fără -> fara, etc.)
_DIACRITICS_TABLE = str.maketrans("ăâîșțĂÂÎȘȚ", "aaistAAIST")


def _label(pattern: str) -> str:
    """Text lizibil pentru motivul respingerii (fara sintaxa regex)."""
    return re.sub(r"\\[bs]|[()?:*+|\\]", " ", pattern).replace("  ", " ").strip()


def _normalize(text: str) -> str:
    """Normalizeaza textul romanesc: elimina diacritice, lowercase, ASCII-only."""
    text = text.translate(_DIACRITICS_TABLE)
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    return text.lower()


# Indicatori pozitivi de incredere
POSITIVE_TRUST_PATTERNS = [
    r"\bservice la zi\b",
    r"\brevisie facuta\b",
    r"\bdistributie schimbata\b",
    r"\bulei schimbat\b",
    r"\bgarantie\b",
    r"\bfara accident\b",
    r"\bfara daune\b",
    r"\bproprietar unic\b",
    r"\bprim proprietar\b",
    r"\bkm reali\b",
    r"\bkm verificabili\b",
    r"\bhistorical check\b",
    r"\braport carvertical\b",
    r"\bcarvertical\b",
]

# Cuvinte cheie interzise: LEASING / RATE / AVANS / FINANTARE / TVA SEPARAT
# Cuvintele generice de mai jos sunt ignorate cand sunt NEGATE ("nu accept rate", "fara leasing"),
# altfel respingeam exact vanzatorii cinstiti care scriu ca NU vand in rate.
LEASING_PATTERNS = [
    r"\bavans\b",
    r"\brata\b",
    r"\brate\b",
    r"\bleasing\b",
    r"\blunar\b",
    r"\blunara\b",
    r"\bcredit\b",
    r"\bcesiune\b",
    r"\bfinantare\b",
]

# Formule care inseamna MEREU oferta de leasing/rate (nu se aplica negatia)
LEASING_STRICT_PATTERNS = [
    r"\bpredare leasing\b",
    r"\bpreluare leasing\b",
    r"\brate fixe\b",
    r"\bfara avans\b",
    r"\bavans minim\b",
    r"\btva deductibil la avans\b",
    r"\bpretul afisat reprezinta\b",
    r"\bdoar avans\b",
    r"\bavansul este\b",
    r"\bprima rata\b",
    r"\bposibilitate rate\b",
    r"\bin rate\b",
    r"\brate buletin\b",
    r"\bdoar cu buletinul\b",
    r"\baprobare rapida\b",
    r"\baprobare rate\b",
    r"\b\+tva\b",
    r"\b\+\s*tva\b",
    r"\bfara tva\b",
    r"\bplus tva\b",
    r"\bpret net\b",
    r"\*rate\*",
    r"\*leasing\*",
]

# Cuvinte cheie interzise: DAUNE / DEFECTE GRAVE / PIESE / PROBLEME ACTE / TAXI
# NOTA SAMSAR EXPERT: Nu respingem "ambreiaj nou" sau "nu accept schimb"! Respingem doar DEFECTE reale si PROPUNERI de schimb.
EXCHANGE_PROPOSAL_PATTERNS = [
    r"\b(?:accept|prefer|doresc|astept)\s+(?:si\s+)?schimb(?:uri)?\b",
    r"\b(?:accept|astept)\s+variante\b",
    r"\bschimb\s+cu\s+(?:auto|masina|teren|apartament|diverse)\b",
    r"\bpret\s+pentru\s+schimb\b",
    r"\bla\s+schimb\s+pretul\s+este\b",
]

DAMAGE_PATTERNS = [
    r"\bavariat\b",
    r"\bavariata\b",
    r"\bavarii\b",
    r"\bdauna totala\b",
    r"\blovit\b",
    r"\blovita\b",
    r"\bepava\b",
    r"\b(?:pentru|ca|doar|la)\s+piese\b",
    r"\bdezmembrez\b",
    r"\bdezmembrari\b",
    r"\bmotor defect\b",
    r"\bmotor blocat\b",
    r"\bfara motor\b",
    r"\bcutie defecta\b",
    r"\bnu porneste\b",
    r"\bprobleme motor\b",
    r"\bprobleme cutie\b",
    r"\bneinmatriculabil\b",
    r"\bfara acte\b",
    r"\bnu am carte\b",
    r"\bcarte pierduta\b",
    r"\bdoar pentru export\b",
    r"\bacte expirate\b",
    r"\bnumere rosii expirate\b",
    r"\bfara itp\b",
    r"\bitp expirat\b",
    r"\bfara rca\b",
    r"\brca expirat\b",
    r"\bfara asigurare\b",
    r"\baccidentat\b",
    r"\baccidentata\b",
    r"\bvolan\s*(?:pe\s*(?:partea\s*)?)?dreapt[aă]\b",
    r"\brhd\b",
    r"\banglia\b",
    r"\birelanda\b",
    r"\bnumere galbene\b",
    r"\bdefect\b",
    r"\bdefecte\b",
    r"\bdefecta\b",
    r"\bnecesita\s+(?:putina\s+|mici\s+)?(?:atentie|reparatii|investitii|interventii)\b",
    r"\btrebuie\s+(?:putina\s+)?atentie\b",
    # Defecte mecanice reale (nu doar mentiuni de piese noi)
    r"\bambreiaj\s+(?:patineaza|defect|uzat|terminat)\b",
    r"\bvolanta\s+(?:bate|zgomot|defecta)\b",
    r"\bturbina\s+(?:fluiera|sparta|defecta|consuma ulei)\b",
    r"\binjectoare\s+(?:defecte|blocate|care dau pe retur)\b",
    r"\bchiuloasa\s+(?:fisurata|arsa|stramba)\b",
    r"\bgarnitura\s+(?:de\s+)?chiuloasa\s+(?:arsa|suflata|defecta|de schimbat)\b",
    r"\bscoate\s+fum\b",
    r"\bfum\s+(?:alb|albastru|negru excesiv)\b",
    r"\bbate\s+(?:motorul|tachetii|la rece)\b",
    r"\bbataie\s+(?:motor|directie|tacheti)\b",
    r"\bprobleme\s+(?:la\s+)?(?:injectoare|turbina|cutie|motor)\b",
    r"\bruginit\b",
    r"\brugina\b",
    r"\bsalvage\b",
    r"\bfost taxi\b",
    r"\bfosta scoala\b",
    r"\bscoala soferi\b",
]

# Cuvinte cheie interzise: PROBLEME FISCALE
FISCAL_RED_FLAGS = [
    r"\bfara fiscal\b",
    r"\bnu ofer fiscal\b",
    r"\bnu dau fiscal\b",
    r"\bfiscal mai tarziu\b",
    r"\bproprietar in strainatate\b",
    r"\bfara transcriere\b",
    r"\bnu se ofera fiscal\b",
]

# Configuratii tehnice toxice cu risc urias de defectare si pierdere de bani
TOXIC_CONFIGURATIONS = [
    (r"\bpowershift\b", "Cutie automata Ford Powershift (risc critic de defectare, cost reparatie >2.000€)"),
    (r"\b1\.2\s*tce\b", "Motor Renault/Dacia 1.2 TCe (consum masiv de ulei, risc gripare motor)"),
    (r"\b1\.0\s*ecoboost\b", "Motor Ford 1.0 EcoBoost (curea distributie in ulei, risc distrugere motor)"),
    (r"\bmultitronic\b", "Cutie automata Audi Multitronic CVT (fiabilitate scazuta, imposibil de revandut usor)"),
    (r"\beasy[- ]?r\b", "Cutie robotizata Dacia Easy-R (probleme frecvente de ambreiaj si actuatoare)"),
    (r"\b1\.4\s*tsi\b.*(?:160|170|180)\s*(?:cp|hp)", "Motor 1.4 TSI Twincharger EA111 (risc fisurare pistoane)"),
]


_NEGATION_RE = re.compile(r"\b(?:fara|nu|niciun|nicio|nici|zero|n-are|n-a|nu\s+are|nu\s+a\s+fost|nu\s+accept|nu\s+ofer|nu\s+fac|exclus)\b[\s\w,-]{0,12}$")


def _find_unnegated(pattern: str, text: str):
    """
    Cauta pattern-ul in text, dar ignora aparitiile negate imediat inainte
    (ex: "fara rugina", "nu are niciun defect", "nu accept rate", "nelovita").
    Returneaza primul match ne-negat sau None.
    """
    for m in re.finditer(pattern, text):
        window = text[max(0, m.start() - 25):m.start()]
        if _NEGATION_RE.search(window):
            continue
        return m
    return None


class AntiFraudShield:
    @staticmethod
    def inspect(
        title: str,
        description: str = "",
        price_eur: float = 0.0,
        mileage: int = 0,
        make: str = "",
        model: str = "",
        year: int = 0,
    ) -> Tuple[bool, str]:
        """
        Verifica daca anuntul este sigur si conform pentru profit.
        Returneaza: (is_safe: bool, reason: str)
        """
        # CRITICAL: Normalizam textul (eliminam diacritice romanesti) INAINTE de matching
        # Fara asta, "lovită" nu e prins de pattern "lovita", "fără" nu e prins de "fara" etc.
        full_text = _normalize(f"{title or ''} {description or ''}")

        # 1. Verificare prag pret (buget configurat in settings: ex. 1.800€ - 7.000€)
        if price_eur < MIN_LISTING_PRICE_EUR:
            return False, f"Pret prea mic ({price_eur:,.0f}€ < {MIN_LISTING_PRICE_EUR:,.0f}€) - suspect de defecte majore sau piese."
        if price_eur > MAX_LISTING_PRICE_EUR:
            return False, f"Pret peste bugetul maxim setat ({price_eur:,.0f}€ > {MAX_LISTING_PRICE_EUR:,.0f}€)."

        # 1b. Verificare An Fabricatie
        if year and (year < MIN_YEAR or year > CURRENT_YEAR + 1):
            return False, f"An fabricatie suspect ({year}) - prea vechi sau invalid."

        # 2. Verificare Rulaj Maxim (maxim admis din settings)
        if mileage is not None:
            try:
                if int(mileage) > MAX_MILEAGE_KM:
                    return False, f"Rulaj prea mare ({mileage:,} km > {MAX_MILEAGE_KM:,} km) - greu de revandut rapid"
            except (ValueError, TypeError):
                pass

        # 3. Verificare Model Non-Lichid (Doar modelele cu cerere uriasa si vanzare garantata < 7 zile)
        if make:
            make_clean = make.strip().lower()
            if make_clean and make_clean != "necunoscut":
                if make_clean not in LIQUID_MODELS:
                    return False, f"Marca '{make}' nu este in lista de marci ultra-lichide"
                if model:
                    model_clean = model.strip().lower()
                    if model_clean and model_clean not in ("necunoscut", "auto"):
                        allowed = LIQUID_MODELS.get(make_clean, [])
                        if not any(m in model_clean or (len(model_clean) >= 3 and model_clean in m) for m in allowed):
                            return False, f"Modelul '{model}' ({make}) nu este in lista modelelor ultra-lichide"

        # 4. Verificare Capcane Leasing / Rate / Avans
        for pattern in LEASING_STRICT_PATTERNS:
            if re.search(pattern, full_text):
                return False, f"Respins: Capcana leasing / rate detectata ('{_label(pattern)}')."
        for pattern in LEASING_PATTERNS:
            if _find_unnegated(pattern, full_text):
                return False, f"Respins: Capcana leasing / rate detectata ('{_label(pattern)}')."

        # 4b. Verificare Propuneri de Schimb (nu vrem vanzatori care cer schimburi sau supra-evalueaza)
        for pattern in EXCHANGE_PROPOSAL_PATTERNS:
            if _find_unnegated(pattern, full_text):
                return False, "Respins: Vanzatorul doreste schimburi / variante."

        # 5. Verificare Daune / Piese / Motor defect (ignora formulari negate: "fara rugina", "nu e lovita")
        for pattern in DAMAGE_PATTERNS:
            if _find_unnegated(pattern, full_text):
                return False, f"Respins: Masina avariata sau piese ('{_label(pattern)}')."

        # 6. Verificare Lipsa Fiscal
        for pattern in FISCAL_RED_FLAGS:
            if re.search(pattern, full_text):
                return False, f"Respins: Risc fiscal ridicat ('{_label(pattern)}')."

        # 7. Verificare Motoare si Cutii Toxice (risc urias de defectare si pierdere de bani)
        for pattern, reason_msg in TOXIC_CONFIGURATIONS:
            if re.search(pattern, full_text):
                return False, f"Respins: {reason_msg}"

        return True, "Sigur: Anunt curat, fara leasing si fara defecte mentionate."

    @staticmethod
    def get_trust_score(title: str, description: str = "") -> int:
        """
        Calculeaza un scor de incredere (0 - 100) pe baza descrierii vanzatorului.
        """
        full_text = _normalize(f"{title or ''} {description or ''}")
        score = 50  # scor de baza

        for pattern in POSITIVE_TRUST_PATTERNS:
            if re.search(pattern, full_text):
                score += 10

        return min(100, score)
