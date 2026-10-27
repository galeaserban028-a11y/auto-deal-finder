# 🏎️ AutoDealHunter — Detecție Chilipiruri Auto

Caută automat mașini listate sub prețul pieței pe **OLX, Autovit, Publi24, CarZZ** (România) și **AutoScout24 / Willhaben** (Germania, Austria), elimină capcanele de leasing/rate/daune și trimite alerte pe **Telegram**.

> Profitul afișat este o **estimare** bazată pe prețurile active de pe Autovit, nu o garanție. Verifică întotdeauna mașina (CarVertical, mecanic) înainte să cumperi.

---

## 🎯 Cum decide dacă un anunț e pont

1. **Filtru rapid** (`core/anti_fraud.py`): buget, an, rulaj, modele lichide, leasing/rate/avans, daune, piese, fără fiscal, motoare/cutii cu probleme cunoscute. Formulările negate („fără rugină”, „nu accept rate”, „nu are niciun defect”) **nu** mai resping anunțul.
2. **Evaluare piață** (`core/live_market.py`): compară cu mașini din **aceeași generație** de pe Autovit, fără daune, cu rulaj similar sau mai mare, **excluzând anunțul însuși**. Preț vânzare rapidă = percentila 15 × 0,95.
3. **Profit net** = preț vânzare rapidă − preț cerut − cheltuieli (`BUFFER_EXPENSES_EUR`, + `IMPORT_EXTRA_COST_EUR` pentru import).
4. **Pont** doar dacă profitul ≥ `MIN_NET_PROFIT_EUR` **și** reducerea ≥ `MIN_DISCOUNT_PERCENT` (din `.env`). Reducerile prea mari (>45% RO / >35% import) sunt marcate „SUSPECT FRAUDĂ”.
5. **Inspecție pagină completă** + **AI** (Gemini/OpenAI, opțional) înainte de alertă.
6. Anunțurile deja văzute sunt ignorate, **dar sunt re-evaluate dacă prețul scade cu ≥3%**.

---

## 🚀 Pornire

Din folderul proiectului:

```powershell
pip install -r requirements.txt
copy .env.example .env      # apoi completează .env
python run_sniper.py --once # o singură scanare
python run_sniper.py        # scanare continuă
python -m streamlit run web/dashboard.py   # dashboard pe http://localhost:8501
```

Sau dublu-click pe `start_sniper.bat` / `start_dashboard.bat`.

**Rulare invizibilă pe Windows:** `start_silent_background.vbs` (manual), `setup_startup.bat` (la pornirea PC-ului), `install_windows_service.bat` (verificare la 10 minute). Nu pornesc niciodată două instanțe în paralel.

**Rulare în cloud:** vezi `GHID_RULARE_CLOUD_24_7.md`.

---

## 📱 Telegram

1. În Telegram, caută **@BotFather** → `/newbot` → copiază tokenul.
2. Caută **@userinfobot** → Start → copiază ID-ul.
3. Rulează `configure_telegram.bat` sau completează `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` în `.env` (mai multe ID-uri separate prin virgulă).
4. Trimite `/start` botului tău, apoi `python send_test_message.py`.

🔒 **Nu pune niciodată tokenul în cod, în documentație sau pe GitHub.** `.env` este exclus prin `.gitignore`. Dacă tokenul a ajuns vreodată public, revocă-l din @BotFather (`/revoke`) și pune-l pe cel nou în `.env`.

---

## 🧪 Teste

```powershell
python -m unittest tests.test_offline -v
```

`tests/test_offline.py` rulează fără internet și pe o bază de date temporară (nu atinge `car_deals.db`). Celelalte fișiere din `tests/` sunt scripturi de investigație care accesează site-urile live.
