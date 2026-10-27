"""
Helper interactiv pentru configurarea Telegram Bot
===================================================
Permite setarea rapida a TELEGRAM_BOT_TOKEN si TELEGRAM_CHAT_ID
si trimite un mesaj de test direct pe telefonul tau.
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"


def save_env_values(values: dict) -> None:
    lines = []
    if ENV_PATH.exists():
        lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
    remaining = dict(values)
    out = []
    for line in lines:
        key = line.split("=", 1)[0].strip()
        if key in remaining and not line.lstrip().startswith("#"):
            out.append(f"{key}={remaining.pop(key)}")
        else:
            out.append(line)
    for k, v in remaining.items():
        out.append(f"{k}={v}")
    ENV_PATH.write_text("\n".join(out) + "\n", encoding="utf-8")


def test_telegram_connection(token: str, chat_id: str) -> bool:
    import requests
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": "🎉 <b>Conexiune Reușită!</b>\n\nAutoDealHunter este acum conectat la telefonul tău. De acum vei primi aici ponturile filtrate automat.",
        "parse_mode": "HTML"
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code != 200:
            print(f"Telegram a raspuns: {r.json().get('description', r.status_code)}")
        return r.status_code == 200
    except Exception as e:
        print(f"Eroare conexiune Telegram: {type(e).__name__}")
        return False


def main():
    print("=" * 60)
    print("   CONFIGURARE NOTIFICARI TELEGRAM — AUTODEALHUNTER")
    print("=" * 60)
    print("\nAi nevoie de 2 lucruri (dureaza 1 minut):")
    print("1. BOT TOKEN: Deschide Telegram, cauta @BotFather, trimite /newbot si copiaza tokenul primit.")
    print("2. CHAT ID: Cauta @userinfobot pe Telegram, da Start si copiaza Id-ul tau numeric.")
    print("-" * 60)

    token = input("\nIntrodu TELEGRAM_BOT_TOKEN: ").strip()
    chat_id = input("Introdu TELEGRAM_CHAT_ID: ").strip()

    if not token or not chat_id:
        print("\n[EROARE] Nu ai completat ambele campuri. Configurarea a fost anulata.")
        return

    print("\nSe trimite mesaj de test pe telefonul tau...")
    if test_telegram_connection(token, chat_id):
        print("\n✔ [SUCCES!] Mesajul de test a fost primit pe telefonul tau!")
        
        # Actualizam DOAR cheile Telegram in .env si pastram restul setarilor
        # (inainte fisierul era rescris complet si se pierdeau cheia Gemini si pragurile tale).
        save_env_values({"TELEGRAM_BOT_TOKEN": token, "TELEGRAM_CHAT_ID": chat_id})
        print("✔ Configuratia a fost salvata in .env.")
    else:
        print("\n❌ [EROARE] Nu s-a putut trimite mesajul. Verifica tokenul si chat_id-ul.")


if __name__ == "__main__":
    main()
