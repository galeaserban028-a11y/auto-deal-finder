"""
AutoDealHunter — Modern Live Dashboard (Streamlit)
Interfata web interactiva pentru:
1. Monitorizarea ponturilor auto din piata
2. Calculator & Simulator Instant de Profit Garantat (pentru orice masina gasita)
3. Testare si configurare alerte Telegram
"""

import os
import sys
from pathlib import Path
import urllib.parse
from html import escape
import streamlit as st
import pandas as pd

# Adauga directorul parinte in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.db import get_all_deals
from scrapers.hub import ScraperHub
from core.live_market import PreciseMarketEngine
from alerts.telegram_bot import TelegramNotifier
from config.settings import (
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, 
    MIN_NET_PROFIT_EUR, MIN_DISCOUNT_PERCENT, ENV_PATH, BUFFER_EXPENSES_EUR,
    GEMINI_API_KEY, MAX_LISTING_PRICE_EUR, CURRENT_YEAR
)

st.set_page_config(
    page_title="AutoDealHunter — Radar Ponturi Auto & Profit Garantat",
    page_icon="🏎️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling (Dark & Green Modern Theme)
st.markdown("""
<style>
    .main-title { font-size: 2.2rem; font-weight: 800; color: #00FF66; margin-bottom: 0px; }
    .sub-title { font-size: 1rem; color: #888888; margin-bottom: 20px; }
    .deal-card { background-color: #12171e; border: 1px solid #1e293b; border-radius: 12px; padding: 18px; margin-bottom: 15px; }
    .badge-unicorn { background-color: #7928CA; color: white; padding: 4px 10px; border-radius: 6px; font-weight: 700; font-size: 0.85rem; }
    .badge-super { background-color: #0070F3; color: white; padding: 4px 10px; border-radius: 6px; font-weight: 700; font-size: 0.85rem; }
    .badge-good { background-color: #10B981; color: white; padding: 4px 10px; border-radius: 6px; font-weight: 700; font-size: 0.85rem; }
    .profit-text { font-size: 1.5rem; font-weight: 800; color: #00FF66; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🏎️ AutoDealHunter — Live Radar & Calculator Profit</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Sistem de monitorizare și arbitraj auto fără leasing — profit estimat pe baza pieței live</div>', unsafe_allow_html=True)

# Tabs
tab_live, tab_calculator, tab_settings = st.tabs(["📡 Ponturi Live Detectate", "🧮 Calculator Profit", "⚙️ Configurare Telegram"])

# Sidebar
st.sidebar.header("🎯 Panou de Control")

if st.sidebar.button("🚀 Scanează Platformele Acum", type="primary", use_container_width=True):
    with st.spinner("Se scanează 8 platforme din România, Germania și Austria..."):
        res = ScraperHub.scan_all(max_pages=2)
    st.sidebar.success(f"Găsite {res['new_deals_found']} ponturi noi din {res['total_scanned']} anunțuri!")

st.sidebar.markdown("---")
st.sidebar.subheader("🔍 Filtre Afișare")
# Implicit 0: arata toate ponturile salvate (care au trecut deja pragurile din .env).
# Valorile sunt limitate la intervalul slider-ului ca sa nu crape pagina cu valori din .env in afara lui.
min_profit_filter = st.sidebar.slider("Profit Net Minim (€)", 0, 5000, 0, step=100)
min_discount_filter = st.sidebar.slider("Reducere Minimă sub prețul de vânzare rapidă (%)", 0, 45, 0, step=1)
st.sidebar.caption(f"Praguri active în scanner (.env): profit ≥ {MIN_NET_PROFIT_EUR:,.0f} € și reducere ≥ {MIN_DISCOUNT_PERCENT:.0f}%")

# ==================== TAB 1: PONTURI LIVE ====================
with tab_live:
    deals = get_all_deals(limit=100)
    filtered_deals = [
        d for d in deals 
        if (d.get("net_profit") or 0) >= min_profit_filter and (d.get("discount_pct") or 0) >= min_discount_filter
    ]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Ponturi în Bază", len(deals))
    col2.metric("Ponturi Filtrate", len(filtered_deals))
    max_profit = max([d.get("net_profit", 0) for d in deals], default=0)
    col3.metric("Cel Mai Mare Profit", f"+{max_profit:,.0f} €")
    col4.metric("Status Telegram", "🟢 Conectat" if TelegramNotifier.is_configured() else "🟡 Neconfigurat")

    st.markdown("---")

    if not filtered_deals:
        st.info("ℹ️ Nu există anunțuri care să întrunească filtrele curente. Apasă pe butonul **'🚀 Scanează Platformele Acum'** din stânga pentru a colecta oferte proaspete!")
    else:
        for deal in filtered_deals:
            rating = deal.get("deal_rating", "STANDARD")
            badge_class = "badge-unicorn" if rating == "UNICORN" else "badge-good"
            discount = deal.get("discount_pct") or 0
            rating_text = escape(f"🦄 UNICORN (-{discount:.0f}%)" if rating == "UNICORN" else f"🔥 {rating} (-{discount:.0f}%)")

            # Datele vin de pe site-uri externe -> escapate inainte de a fi puse in HTML
            url = deal.get("url") or "#"
            raw_title = deal.get("title") or "Autoturism"
            title = escape(raw_title)
            price = deal.get("price_eur") or 0
            net_profit = deal.get("net_profit") or 0
            safe_sell = deal.get("median_price") or 0
            year = escape(str(deal.get("year") or "N/A"))
            mileage = int(deal.get("mileage") or 0)
            fuel = escape(str(deal.get("fuel") or "N/A"))
            city = escape(str(deal.get("city") or "Romania"))
            source = escape(str(deal.get("source") or "Web"))
            expenses = deal.get("total_expenses") or BUFFER_EXPENSES_EUR
            sent_badge = "✅ trimis pe Telegram" if deal.get("alerted_telegram") else "⏳ netrimis"

            wa_text = urllib.parse.quote(
                f"Bună ziua! Vă contactez referitor la anunțul cu {raw_title} la prețul de {price:,.0f} €. "
                f"Mai este valabilă mașina? Pot veni să o văd astăzi cu plata pe loc."
            )
            wa_url = f"https://wa.me/?text={wa_text}"

            with st.container():
                st.markdown(f"""
                <div class="deal-card">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                        <div>
                            <span class="{badge_class}">{rating_text}</span>
                            <span style="color: #94a3b8; font-size: 0.85rem; margin-left: 10px;">Sursă: <b>{source}</b> | Locație: {city} | {sent_badge}</span>
                        </div>
                        <div class="profit-text">+{net_profit:,.0f} € NET</div>
                    </div>
                    <h3 style="margin-top: 5px; margin-bottom: 8px; color: #f8fafc;">{title}</h3>
                    <p style="color: #cbd5e1; margin-bottom: 12px; font-size: 0.95rem;">
                        📅 <b>An:</b> {year} &nbsp;|&nbsp; 🛣️ <b>Rulaj:</b> {mileage:,} km &nbsp;|&nbsp; ⛽ <b>Combustibil:</b> {fuel}
                    </p>
                    <div style="background-color: #0f172a; padding: 12px 16px; border-radius: 8px; margin-bottom: 12px; font-size: 0.95rem;">
                        💰 <b>Preț Vânzător:</b> {price:,.0f} € &nbsp;•&nbsp; 
                        📊 <b>Preț estimat vânzare rapidă:</b> {safe_sell:,.0f} € &nbsp;•&nbsp;
                        💸 <b>Costuri scăzute:</b> -{expenses:,.0f} € &nbsp;•&nbsp;
                        💵 <b style="color: #00FF66;">Profit estimat:</b> +{net_profit:,.0f} €
                    </div>
                </div>
                """, unsafe_allow_html=True)

                b_col1, b_col2, _ = st.columns([2, 2, 4])
                if url.startswith("http"):
                    b_col1.link_button("🌐 DESCHIDE ANUNȚUL", url, use_container_width=True)
                b_col2.link_button("💬 TRIMITE WHATSAPP", wa_url, use_container_width=True)
                st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

# ==================== TAB 2: CALCULATOR INSTANT PROFIT ====================
with tab_calculator:
    st.subheader("🧮 Evaluează Instant Orice Mașină Găsită Manual")
    st.write("Ai văzut o mașină pe Facebook Marketplace, OLX sau pe stradă? Introdu datele ei mai jos pentru a estima **profitul la revânzare**.")

    calc_c1, calc_c2 = st.columns(2)
    with calc_c1:
        calc_make = st.selectbox("Marca", ["volkswagen", "skoda", "audi", "bmw", "mercedes-benz", "dacia", "ford", "renault", "opel", "hyundai", "kia", "toyota"])
        calc_model = st.text_input("Modelul (ex: golf, passat, octavia, duster, a4, seria-3)", value="golf")
        calc_fuel = st.selectbox("Combustibil", ["diesel", "benzina", "hybrid", "electric"])
        calc_year = st.number_input("Anul Fabricației", min_value=2005, max_value=CURRENT_YEAR + 1, value=2017)
    with calc_c2:
        calc_km = st.number_input("Kilometrajul declarat (km)", min_value=0, max_value=500000, value=175000, step=5000)
        calc_price = st.number_input("Prețul cerut de vânzător (€)", min_value=500, max_value=100000, value=7500, step=250)

    if st.button("📊 Calculează Profitul pe Piața LIVE", type="primary", use_container_width=True):
        with st.spinner("Se interoghează piața live din România pentru comparație precisă..."):
            eval_result = PreciseMarketEngine.evaluate(
                listing_price=float(calc_price),
                make=calc_make,
                model=calc_model,
                fuel=calc_fuel,
                year=int(calc_year),
                mileage=int(calc_km)
            )

        st.markdown("---")
        st.subheader("📋 Rezultatul Evaluării:")

        safe_sell = eval_result.get('safe_sell_price', 0)
        cheapest = eval_result.get('cheapest_on_market', 0)
        net_profit = eval_result.get('net_profit', 0)
        pct_below = eval_result.get('pct_below_safe_sell', 0)
        total_comp = eval_result.get('total_comparable', 0)

        rc1, rc2, rc3, rc4 = st.columns(4)
        rc1.metric("Cel Mai Ieftin pe Piață", f"{cheapest:,.0f} €")
        rc2.metric("Preț Re-vânzare Rapidă", f"{safe_sell:,.0f} €")
        rc3.metric("Sub prețul de vânzare rapidă", f"{pct_below:.1f} %")
        rc4.metric("PROFIT NET ESTIMAT", f"{net_profit:+,.0f} €")
        st.caption(f"Comparat cu {total_comp} mașini din aceeași generație ({eval_result.get('generation', '-')}), fără daune, cu rulaj similar sau mai mare.")

        if eval_result.get("is_deal"):
            st.success(f"🎉 **PONT ({eval_result.get('deal_rating', 'PONT')})!** Dacă cumperi la {calc_price:,.0f}€ și vinzi la prețul de vânzare rapidă ({safe_sell:,.0f}€), după cheltuielile estimate de {eval_result.get('total_expenses', BUFFER_EXPENSES_EUR):,.0f}€ rămân aprox. **+{net_profit:,.0f}€ profit net** (estimare, nu garanție - verifică mașina!).")
        elif eval_result.get("deal_rating") == "SUSPECT FRAUDA":
            st.error(f"⚠️ **SUSPECT FRAUDĂ!** Prețul e prea mic față de piață. {eval_result.get('reason', '')} Poate fi mașină avariată, daună totală sau țeapă de avans.")
        elif eval_result.get("deal_rating") in ("INSUFICIENTE DATE", "PIATA INDISPONIBILA", "MODEL NECUNOSCUT"):
            st.warning(f"ℹ️ Nu se poate evalua ({eval_result.get('deal_rating')}): prea puține mașini comparabile găsite pe Autovit pentru acest model/an.")
        else:
            st.warning(f"🔴 **NU ESTE PONT PENTRU REVÂNZARE ({eval_result.get('deal_rating')}).** Prețul de {calc_price:,.0f}€ este deja preț de piață. Marja de profit după cheltuieli ar fi {net_profit:,.0f}€.")

# ==================== TAB 3: CONFIGURARE TELEGRAM & MULTI-AI ====================
with tab_settings:
    st.subheader("📱 Setări Telegram (Multi-Utilizator) & AI")
    st.write("Configurează botul pentru a trimite alertele către **mai multe persoane în același timp** și activează cel mai nou AI de inspecție.")

    # Afisam conturile active
    current_chats = [cid.strip() for cid in str(TELEGRAM_CHAT_ID).replace(";", ",").split(",") if cid.strip()]
    if current_chats:
        st.info(f"👥 **{len(current_chats)} cont(uri) conectate.**")

    with st.form("telegram_form"):
        st.markdown("#### 1. Conexiune Telegram")
        token_input = st.text_input("Bot Token (de la @BotFather)", value=TELEGRAM_BOT_TOKEN, type="password")
        chat_id_input = st.text_area(
            "Chat ID-uri Destinatari (separate prin virgulă)",
            value=TELEGRAM_CHAT_ID,
            help="Poți trece mai multe conturi separate prin virgulă! Ex: 123456789, 987654321. Toate vor primi alertele instant!"
        )
        st.caption("💡 Fiecare persoană trebuie să caute botul pe Telegram și să apese **/start** înainte de a primi mesaje!")

        st.markdown("---")
        st.markdown("#### 2. Cheie Google Gemini 2.0 Flash (Opțional)")
        gemini_input = st.text_input("Gemini API Key (Gratuit de pe aistudio.google.com)", value=GEMINI_API_KEY, type="password")

        st.markdown("---")
        st.markdown("#### 3. Plafon Maxim de Preț")
        max_price_input = st.number_input("Preț Maxim Căutare (€)", min_value=3000, max_value=50000, value=min(50000, max(3000, int(MAX_LISTING_PRICE_EUR))), step=500)

        save_btn = st.form_submit_button("💾 Salvează Toate Datele în .env", type="primary", use_container_width=True)

        if save_btn:
            env_vars = {}
            if os.path.exists(ENV_PATH):
                with open(ENV_PATH, "r", encoding="utf-8") as f:
                    for line in f:
                        clean_line = line.strip()
                        if clean_line and not clean_line.startswith("#") and "=" in clean_line:
                            k, v = clean_line.split("=", 1)
                            env_vars[k.strip()] = v.strip()

            env_vars["TELEGRAM_BOT_TOKEN"] = token_input.strip()
            env_vars["TELEGRAM_CHAT_ID"] = chat_id_input.strip()
            if gemini_input.strip():
                env_vars["GEMINI_API_KEY"] = gemini_input.strip()
            env_vars["MAX_LISTING_PRICE_EUR"] = str(max_price_input)

            with open(ENV_PATH, "w", encoding="utf-8") as f:
                for k, v in env_vars.items():
                    f.write(f"{k}={v}\n")
            st.success("✅ Configurația a fost salvată! Repornește dashboard-ul și sniperul ca să o încarce.")

    if TelegramNotifier.is_configured():
        st.markdown("---")
        st.subheader("🔔 Testare Trimitere pe Toate Conturile")
        if st.button("🚀 Trimite Mesaj de Test Către Toți Utilizatorii", use_container_width=True):
            test_deal = {
                "title": "Volkswagen Golf 6 1.6 TDI (Test Alert)",
                "url": "https://www.autovit.ro",
                "price_eur": 4500.0,
                "median_price": 6200.0,
                "floor_price": 5800.0,
                "net_profit": 750.0,
                "discount_pct": 22.0,
                "year": 2012,
                "mileage": 158000,
                "fuel": "Diesel",
                "city": "București",
                "source": "Autovit.ro",
                "deal_rating": "PONT REAL",
                "ai_score": 90,
                "ai_summary": "Test transmisie multi-cont realizat cu succes.",
                "ai_model": "Multi-AI Inspector",
            }
            res = TelegramNotifier.send_deal_alert(test_deal)
            if res:
                st.success(f"🎉 Mesaj de test expediat cu succes către toate cele {len(current_chats)} conturi conectate! Verifică telefoanele.")
            else:
                st.error("Eroare la trimitere. Asigură-te că fiecare cont a trimis cel puțin o dată /start către bot.")
