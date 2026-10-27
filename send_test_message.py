import os
import sys
import json
import subprocess
import requests
from dotenv import load_dotenv

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

token = os.getenv("TELEGRAM_BOT_TOKEN")
raw_chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
chat_ids = [cid.strip() for cid in raw_chat_id.replace(";", ",").split(",") if cid.strip()]

message = (
    "🔔 <b>TEST SISTEM — AutoDealHunter Hardcore Samsar Edition</b> 🔔\n\n"
    "Salutare! Acesta este <b>mesajul de test oficial</b> pentru a confirma conectarea botului de Telegram.\n\n"
    "✅ Conexiunea funcționează cu succes!\n"
    "🎯 Radarul scanează acum 8 surse (România, Germania, Austria) fără greșeli de monedă și fără leasing.\n"
    "💵 De acum vei primi aici ponturile filtrate automat.\n\n"
    "Spor la vânzări și profit maxim! 🏎️💨"
)

if not token or not chat_ids:
    print("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID lipsesc din .env - ruleaza configure_telegram.bat")
    sys.exit(1)

print(f"Trimitere mesaj de test catre {len(chat_ids)} destinatari...")

for cid in chat_ids:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": cid,
        "text": message,
        "parse_mode": "HTML",
    }
    sent = False
    try:
        r = requests.post(url, json=payload, timeout=8)
        res_data = r.json()
        if res_data.get("ok"):
            print(f"  ✔ Trimis cu succes catre {cid}")
            sent = True
        else:
            print(f"  ❌ Eroare trimitere catre {cid}: {res_data.get('description')}")
    except Exception as e:
        print(f"  ℹ️ Requests timeout/eroare catre {cid} ({type(e).__name__}). Se incearca prin curl...")

    if not sent:
        try:
            curl_bin = "curl.exe" if sys.platform == "win32" else "curl"
            cmd = [
                curl_bin, "-s", "-m", "15", "-X", "POST", url,
                "-H", "Content-Type: application/json",
                "-d", json.dumps(payload, ensure_ascii=True)
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
            if res.returncode == 0 and res.stdout:
                res_data = json.loads(res.stdout.decode('utf-8', errors='ignore'))
                if res_data.get("ok"):
                    print(f"  ✔ Trimis cu succes prin curl catre {cid}!")
                    sent = True
                else:
                    print(f"  ❌ Eroare curl catre {cid}: {res_data.get('description')}")
        except Exception as ce:
            print(f"  ❌ Exceptie curl catre {cid}: {type(ce).__name__}")
