"""
Telegram Bot Alert Dispatcher
Trimite alerte instantanee pe Telegram cu:
- Link direct accesibil cu un singur click
- Buton de deschidere directa pe site
- Buton WhatsApp cu mesaj pre-completat
- Detalii despre profitul net estimat si pretul pietei
"""

import sys
import re
import json
import time
import subprocess
import urllib.parse
from html import escape
import requests
from typing import Dict, List
from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, BUFFER_EXPENSES_EUR


def _num(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def get_chat_ids() -> List[str]:
    return [cid.strip() for cid in str(TELEGRAM_CHAT_ID).replace(";", ",").split(",") if cid.strip()]


def normalize_phone(raw_phone: str) -> str:
    """Transforma un numar romanesc in format international pentru wa.me (ex: 0722... -> 40722...)."""
    clean = re.sub(r"[^\d+]", "", str(raw_phone or "").strip())
    if clean.startswith("+"):
        clean = clean[1:]
    elif clean.startswith("00"):
        clean = clean[2:]
    elif clean.startswith("07") and len(clean) == 10:
        clean = "40" + clean[1:]
    return clean if 10 <= len(clean) <= 15 else ""


class TelegramNotifier:
    @staticmethod
    def is_configured() -> bool:
        """Verifica daca tokenul si chat_id-ul Telegram sunt configurate."""
        return bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)

    @classmethod
    def send_deal_alert(cls, deal: Dict) -> bool:
        """
        Trimite o alerta de chilipir cu link direct si butoane pe Telegram.
        """
        # Toate valorile venite din anunturi sunt escapate: un titlu cu "<" sau "&" facea Telegram
        # sa respinga mesajul ("can't parse entities"), iar pontul era retrimis la infinit.
        raw_title = str(deal.get("title") or "Autoturism")
        title = escape(raw_title)
        url = str(deal.get("url") or "")
        price = _num(deal.get("price_eur"))
        net_profit = _num(deal.get("net_profit"))
        year = escape(str(deal.get("year") or "N/A"))
        mileage = int(_num(deal.get("mileage")))
        fuel = escape(str(deal.get("fuel") or "N/A"))
        city = escape(str(deal.get("city") or "Romania"))
        source = str(deal.get("source") or "Web")
        deal_rating = deal.get("deal_rating", "PONT")

        cheapest_on_market = _num(deal.get("cheapest_on_market", deal.get("floor_price")))
        safe_sell_price = _num(deal.get("safe_sell_price", deal.get("median_price")))
        pct_below = _num(deal.get("pct_below_safe_sell", deal.get("discount_pct")))
        total_comparable = int(_num(deal.get("total_comparable")))
        total_expenses = _num(deal.get("total_expenses"), BUFFER_EXPENSES_EUR) or BUFFER_EXPENSES_EUR
        generation = escape(str(deal.get("generation") or "").upper())

        rating_emoji = "🦄 TUN DE AUR (UNICORN)" if deal_rating == "UNICORN" else "🚨 PONT VERIFICAT"

        # Raport AI - afisat doar daca exista date reale (nu mai inventam un scor de 85/100)
        ai_score = deal.get("ai_score")
        ai_summary = escape(str(deal.get("ai_summary") or ""))
        ai_model = escape(str(deal.get("ai_model") or ""))
        ai_flags = deal.get("ai_flags") or []
        if isinstance(ai_flags, str):
            ai_flags = [ai_flags]

        ai_section = ""
        if ai_score is not None or ai_summary:
            ai_section = f"🤖 <b>RAPORT INSPECȚIE ({ai_model or 'n/a'}):</b>\n"
            if ai_score is not None:
                ai_section += f"⭐ Scor Încredere: <b>{int(_num(ai_score))}/100</b>\n"
            if ai_summary:
                ai_section += f"📝 Diagnostic: <i>{ai_summary}</i>\n"
            if ai_flags:
                ai_section += f"⚠️ Puncte de verificat: <i>{escape(', '.join(str(f) for f in ai_flags))}</i>\n"
            ai_section += "\n"

        # Oferta rapida de negociere cash (clasica de flipper)
        oferta_cash = max(500, price - (500 if price >= 5000 else 300))
        pitch_msg = (
            f"Bună ziua! Vă contactez pentru mașina {raw_title}. Dacă este funcțională și actele sunt în regulă, "
            f"vă pot oferi {oferta_cash:,.0f} € cash astăzi, vin cu banii pregătiți. Vă interesează? Mulțumesc!"
        )
        wa_text = urllib.parse.quote(pitch_msg)

        raw_phone = str(deal.get("seller_phone") or "").strip()
        clean_phone = normalize_phone(raw_phone)

        gen_line = f"🏷️ <i>Generație: {generation}</i>\n\n" if generation else "\n"
        comp_line = (
            f"🎯 Comparat în generația {generation} ({total_comparable} mașini active)\n\n"
            if total_comparable else "\n"
        )

        message_html = (
            f"<b>{rating_emoji}</b>\n"
            f"{gen_line}"
            f"🚗 <b>{title}</b>\n"
            f"📅 An: <b>{year}</b> | 🛣️ Rulaj declarat: <b>{mileage:,} km</b>\n"
            f"⛽ Combustibil: <b>{fuel}</b> | 📍 Locație: <b>{city}</b>\n\n"
            f"💰 <b>Preț cerut: {price:,.0f} €</b>\n"
            f"📉 <b>Preț estimat vânzare rapidă: {safe_sell_price:,.0f} €</b>\n"
            f"🏷️ Cel mai ieftin comparabil din piață: <b>{cheapest_on_market:,.0f} €</b>\n"
            f"📊 Cu <b>{pct_below:.0f}%</b> sub prețul de vânzare rapidă\n"
            f"💸 Cheltuieli estimate (transport + pregătire + marjă): <b>-{total_expenses:,.0f} €</b>\n"
            f"💵 <b>PROFIT NET ESTIMAT: +{net_profit:,.0f} €</b>\n"
            f"{comp_line}"
            f"{ai_section}"
            f"💬 <b>OFERTĂ NEGOCIERE CASH (Apasă pe text pentru a-l copia):</b>\n"
            f"<code>{escape(pitch_msg)}</code>\n\n"
            f"🌐 Sursă: <b>{escape(source)}</b>\n\n"
            f"🔗 <b>LINK DIRECT:</b>\n"
            f"<a href=\"{escape(url, quote=True)}\">{escape(url)}</a>"
        )

        buttons = []
        if url.startswith("http"):
            buttons.append([{"text": "🌐 DESCHIDE ANUNȚUL ORIGINAL", "url": url}])

        # Buton WhatsApp se adauga DOAR daca exista un numar de telefon valid
        if clean_phone:
            wa_url = f"https://wa.me/{clean_phone}?text={wa_text}"
            buttons.append([{"text": f"💬 WHATSAPP VÂNZĂTOR ({raw_phone})", "url": wa_url}])

        is_romania = any(s in source.lower() for s in ["olx", "autovit", "publi24", "carzz"])
        if is_romania:
            buttons.append([{"text": "🔍 VERIFICĂ CARVERTICAL (KM & DAUNE)", "url": "https://www.carvertical.com/ro"}])
        else:
            buttons.append([{"text": "🔍 VERIFICĂ CARVERTICAL EUROPA", "url": "https://www.carvertical.com/"}])

        reply_markup = {"inline_keyboard": buttons}

        if not cls.is_configured():
            # Mod Simulare / Notificare in consola cand nu este setat tokenul
            # Returnam False: pontul ramane netrimis si va pleca automat dupa configurarea botului
            # (inainte era marcat ca "trimis" si se pierdea definitiv).
            safe_title = raw_title.encode("ascii", errors="replace").decode("ascii")
            print("\n" + "="*60)
            print("[SIMULARE ALERTA TELEGRAM - BOT TOKEN NECONFIGURAT]")
            print(f"Titlu: {safe_title}")
            print(f"Pret: {price} EUR | Profit Net: +{net_profit} EUR")
            print(f"Link Direct: {url}")
            print("="*60 + "\n")
            return False

        # Trimitere prin Telegram Bot API (suporta multiple Chat ID-uri separate prin virgula)
        chat_ids = get_chat_ids()
        if not chat_ids:
            return False

        telegram_api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        any_success = False

        for cid in chat_ids:
            payload = {
                "chat_id": cid,
                "text": message_html,
                "parse_mode": "HTML",
                "disable_web_page_preview": False,
                "reply_markup": reply_markup,
            }
            sent = False
            data_missing = True
            try:
                res = requests.post(telegram_api_url, json=payload, timeout=10)
                data = res.json()
                if res.status_code == 429:
                    # Limitare Telegram: asteptam cat cere API-ul si mai incercam o data
                    wait_s = int((data.get("parameters") or {}).get("retry_after", 3))
                    time.sleep(min(wait_s, 30))
                    res = requests.post(telegram_api_url, json=payload, timeout=10)
                    data = res.json()
                data_missing = False
                if data.get("ok"):
                    print(f"[Telegram] Alerta trimisa cu succes catre {cid} pentru: {raw_title}")
                    any_success = True
                    sent = True
                else:
                    print(f"[Telegram Error pentru {cid}] {data.get('description')}")
            except Exception as e:
                # Nu afisam exceptia completa: contine URL-ul cu tokenul botului
                print(f"[Telegram Requests Exception pentru {cid}] {type(e).__name__}. Se incearca prin curl...")

            # Fallback curl doar la erori de retea (nu si cand Telegram a raspuns explicit cu eroare)
            if not sent and data_missing:
                try:
                    curl_bin = "curl.exe" if sys.platform == "win32" else "curl"
                    cmd = [
                        curl_bin, "-s", "-m", "15", "-X", "POST", telegram_api_url,
                        "-H", "Content-Type: application/json",
                        "-d", json.dumps(payload, ensure_ascii=True)
                    ]
                    c_res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
                    if c_res.returncode == 0 and c_res.stdout:
                        c_data = json.loads(c_res.stdout.decode('utf-8', errors='ignore'))
                        if c_data.get("ok"):
                            print(f"[Telegram] Alerta trimisa cu succes prin curl catre {cid} pentru: {raw_title}")
                            any_success = True
                        else:
                            print(f"[Telegram Curl Error pentru {cid}] {c_data.get('description')}")
                except Exception as ce:
                    print(f"[Telegram Curl Exception pentru {cid}] {type(ce).__name__}")

        return any_success
