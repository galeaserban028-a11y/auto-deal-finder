"""
AutoDealHunter Sniper Runner
Scriptul principal de scanare si trimitere a alertelor pe Telegram.
Rulare continua sau manuala.
"""

import os
import sys
import time
import socket
import argparse

# Ruleaza mereu din folderul proiectului (Task Scheduler / scurtatura din Startup pornesc din alt folder)
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Asigura afisare corecta UTF-8 pe Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
        sys.stderr.reconfigure(encoding="utf-8", line_buffering=True)
    except Exception:
        pass

from colorama import init, Fore
from scrapers.hub import ScraperHub
from core.db import get_unalerted_deals, mark_as_alerted, checkpoint
from alerts.telegram_bot import TelegramNotifier
from config.settings import SCAN_INTERVAL_SECONDS

init(autoreset=True)

# Port local folosit doar ca "lacat": impiedica pornirea a doua instante in paralel
# (Task Scheduler + Startup porneau instante noi la fiecare 10 minute care se adunau in fundal
# si trimiteau aceleasi alerte de mai multe ori).
_LOCK_PORT = int(os.getenv("SNIPER_LOCK_PORT", "47653"))
_lock_socket = None


def acquire_single_instance_lock() -> bool:
    global _lock_socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if sys.platform == "win32":
            s.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        s.bind(("127.0.0.1", _LOCK_PORT))
        s.listen(1)
        _lock_socket = s
        return True
    except OSError:
        return False


def run_cycle():
    print(f"\n{Fore.CYAN}==================================================")
    print(f"{Fore.GREEN}🎯 [AutoDealHunter] Lansare ciclu de scanare ponturi...")
    print(f"{Fore.CYAN}==================================================")

    result = ScraperHub.scan_all(max_pages=2)
    print(f"{Fore.YELLOW}📊 Rezumat Scanare:")
    print(f"  - Total anunturi analizate: {result['total_scanned']}")
    print(f"  - Anunturi deja cunoscute: {result['already_seen']}")
    print(f"  - Respinse (leasing/rate/daune): {result['rejected_unsafe']}")
    print(f"  - Amanate (eroare retea, se reincearca): {result.get('retry_later', 0)}")
    print(f"  - Ponturi noi descoperite: {result['new_deals_found']}")

    # Trimitere alerte pentru ponturile noi
    unalerted = get_unalerted_deals()
    if not unalerted:
        print(f"\n{Fore.BLUE}ℹ️ Niciun pont nou netransmis in acest ciclu.")
        return

    if not TelegramNotifier.is_configured():
        print(f"\n{Fore.YELLOW}⚠️ Telegram neconfigurat: {len(unalerted)} ponturi asteapta in baza de date "
              f"si vor fi trimise automat dupa configurare (vezi si Dashboard-ul).")
        return

    print(f"\n{Fore.GREEN}🚀 Trimitere alerte pentru {len(unalerted)} ponturi noi...")
    for deal in unalerted:
        if TelegramNotifier.send_deal_alert(deal):
            mark_as_alerted(deal["deal_id"])
            print(f"  {Fore.GREEN}✔ Alerta procesata pentru deal #{deal['deal_id']}: {deal['title']} (Profit: +{deal['net_profit']}€)")
        else:
            print(f"  {Fore.RED}✘ Alerta NEtrimisa pentru deal #{deal['deal_id']} (se reincearca la ciclul urmator)")
        time.sleep(1)


def main():
    parser = argparse.ArgumentParser(description="AutoDealHunter Car Deal Sniper")
    parser.add_argument("--once", action="store_true", help="Ruleaza o singura scanare si se opreste")
    parser.add_argument("--interval", type=int, default=SCAN_INTERVAL_SECONDS, help="Intervalul in secunde intre scanari")
    args = parser.parse_args()
    interval = max(30, args.interval)

    if not acquire_single_instance_lock():
        print("ℹ️ AutoDealHunter ruleaza deja (alta instanta activa). Iesire.")
        return

    print(f"{Fore.MAGENTA}╔════════════════════════════════════════════════╗")
    print(f"{Fore.MAGENTA}║      AUTODEALHUNTER — CAR SNIPER ACTIVE        ║")
    print(f"{Fore.MAGENTA}╚════════════════════════════════════════════════╝")
    print(f"{Fore.WHITE}Telegram Configurat: {Fore.GREEN if TelegramNotifier.is_configured() else Fore.YELLOW}{TelegramNotifier.is_configured()}")
    print(f"{Fore.WHITE}Interval Scanare: {interval} secunde")

    if args.once:
        try:
            run_cycle()
        finally:
            checkpoint()
        return

    while True:
        try:
            run_cycle()
            checkpoint()
            print(f"\n{Fore.LIGHTBLACK_EX}⏳ Urmatoarea scanare in {interval} secunde... (Ctrl+C pentru oprire)")
            time.sleep(interval)
        except KeyboardInterrupt:
            print(f"\n{Fore.RED}🛑 Oprire la cererea utilizatorului.")
            break
        except Exception as e:
            print(f"\n{Fore.RED}[Eroare Ciclu] {type(e).__name__}: {e}")
            time.sleep(30)


if __name__ == "__main__":
    main()
