import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Base Directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file if present (variabilele deja setate in mediu - ex. GitHub Secrets - au prioritate)
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)


def _env_float(name: str, default: float) -> float:
    try:
        return float(str(os.getenv(name, default)).strip() or default)
    except ValueError:
        print(f"[Config] Valoare invalida pentru {name}, se foloseste {default}")
        return float(default)


def _env_int(name: str, default: int) -> int:
    try:
        return int(float(str(os.getenv(name, default)).strip() or default))
    except ValueError:
        print(f"[Config] Valoare invalida pentru {name}, se foloseste {default}")
        return int(default)


# Telegram Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

# AI Super-Inspector Configuration (Google Gemini / OpenAI)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
# Modelele se pot schimba din .env fara modificari de cod (Google retrage periodic modelele vechi)
GEMINI_MODELS = [m.strip() for m in os.getenv("GEMINI_MODELS", "gemini-2.5-flash,gemini-2.0-flash").split(",") if m.strip()]
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
AI_INSPECTION_ENABLED = os.getenv("AI_INSPECTION_ENABLED", "true").lower() in ("true", "1", "yes")
AI_MIN_CONFIDENCE_SCORE = _env_int("AI_MIN_CONFIDENCE_SCORE", 75)

# Profit & Valuation Parameters
# Un anunt devine PONT doar daca are AMBELE: profit net >= MIN_NET_PROFIT_EUR si
# reducere fata de pretul de vanzare rapida >= MIN_DISCOUNT_PERCENT.
MIN_NET_PROFIT_EUR = _env_float("MIN_NET_PROFIT_EUR", 1500.0)
MIN_DISCOUNT_PERCENT = _env_float("MIN_DISCOUNT_PERCENT", 18.0)

# Prep & Risk Expenses Buffer (deducted before calculating net profit)
# 150€ Detailing, 150€ Basic service/oil, 150€ Transport/docs, 300€ Hidden defect buffer, 300€ Buyer discount margin
BUFFER_EXPENSES_EUR = _env_float("BUFFER_EXPENSES_EUR", 1050.0)
# Cost suplimentar pentru masini de import (platforma/transport + RAR + numere)
IMPORT_EXTRA_COST_EUR = _env_float("IMPORT_EXTRA_COST_EUR", 850.0)

# Curs de schimb folosit cand anuntul e in LEI (actualizeaza-l din cand in cand in .env)
EUR_RON_RATE = _env_float("EUR_RON_RATE", 5.0)

# Minimum and Maximum Price Guardrails
MIN_LISTING_PRICE_EUR = _env_float("MIN_LISTING_PRICE_EUR", 1800.0)
MAX_LISTING_PRICE_EUR = _env_float("MAX_LISTING_PRICE_EUR", 15000.0)

# Rulaj Maxim Admis
MAX_MILEAGE_KM = _env_int("MAX_MILEAGE_KM", 260000)

# Anul curent (calculat automat - nu mai trebuie actualizat manual in cod)
CURRENT_YEAR = datetime.now().year
MIN_YEAR = _env_int("MIN_YEAR", 2005)

# Scan Settings
SCAN_INTERVAL_SECONDS = max(30, _env_int("SCAN_INTERVAL_SECONDS", 60))
# DATABASE_PATH poate fi suprascris (ex: testele folosesc o baza separata ca sa nu polueze baza reala)
DATABASE_PATH = Path(os.getenv("DATABASE_PATH") or (BASE_DIR / "car_deals.db"))

# Highly Liquid Whitelist Models in Romania (fastest flips, sold < 7 days)
MERCEDES_MODELS = [
    "clasa-c", "clasa-e", "clasa-a", "clasa-b", "cla", "gla",
    "c-class", "e-class", "a-class", "b-class",
    "c-klasse", "e-klasse", "a-klasse", "b-klasse",
    "c class", "e class", "a class", "b class",
    "c180", "c200", "c220", "e200", "e220", "a180", "b180", "b200"
]

LIQUID_MODELS = {
    "volkswagen": ["golf", "passat", "tiguan", "polo", "touran", "caddy"],
    "skoda": ["octavia", "superb", "rapid", "fabia"],
    "audi": ["a3", "a4", "a6", "q5"],
    "bmw": ["seria-3", "seria-5", "seria-1", "x3", "x1", "3-series", "5-series", "1-series", "seria 3", "seria 5", "seria 1", "320", "520", "318", "116", "316", "525"],
    "dacia": ["duster", "logan", "sandero", "stepway"],
    "ford": ["focus", "kuga", "mondeo", "fiesta"],
    "renault": ["megane", "clio", "captur"],
    "mercedes-benz": MERCEDES_MODELS,
    "mercedes": MERCEDES_MODELS,
    "hyundai": ["tucson", "ix35", "i30"],
    "kia": ["sportage", "ceed", "cee'd"],
    "toyota": ["corolla", "yaris", "rav4", "auris"],
    "opel": ["astra", "insignia", "corsa"],
}
