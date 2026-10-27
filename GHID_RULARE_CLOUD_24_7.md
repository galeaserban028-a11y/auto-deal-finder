# 🚀 Ghid: Rulare 24/7 în Cloud (Fără PC Deschis) + Activare AI

Acest ghid îți arată cum să faci ca sistemul să ruleze **complet autonom în cloud**, la fiecare minut sau la fiecare 15 minute, **chiar dacă închizi complet laptopul sau PC-ul**, și cum să activezi gratuit inspecția AI cu **Google Gemini**.

---

## 🔑 Partea 1: Cum activezi Google Gemini Gratuit (Opțional, dar Recomandat)

Google oferă acces gratuit (cu limite) la modelele **Gemini Flash** prin AI Studio:
1. Intră pe [Google AI Studio](https://aistudio.google.com/).
2. Conectează-te cu contul tău de Google.
3. Apasă pe butonul albastru **"Get API Key"** $\rightarrow$ **"Create API Key"**.
4. Copiază cheia generată (începe cu `AIzaSy...`).
5. Deschide fișierul `.env` din proiect și adaugă:
   ```env
   GEMINI_API_KEY=cheia_ta_copiata_aici
   ```
*Dacă nu adaugi cheia, sistemul rulează automat pe motorul euristic local de siguranță.*

---

## ☁️ Partea 2: Cum rulezi 24/7 în Cloud FĂRĂ Calculator Deschis

Ai la dispoziție **2 opțiuni 100% gratuite**:

### Opțiunea 1: GitHub Actions (Cea mai simplă, fără niciun server de plătit)
Rulează pe serverele Microsoft/GitHub la fiecare 15 minute permanent:
1. Creează un cont gratuit pe [github.com](https://github.com) dacă nu ai deja.
2. Creează un repository **PRIVAT** (ex: `auto-deal-finder`). Baza de date cu anunțuri este salvată în repo după fiecare rulare.
3. Urcă codul din acest folder pe GitHub (fișierul `.gitignore` împiedică urcarea fișierului `.env` cu parolele tale — verifică cu `git status` înainte de commit că `.env` NU apare în listă):
   ```bash
   git init
   git add .
   git commit -m "AutoDealHunter with Multi-AI"
   git branch -M main
   git remote add origin https://github.com/UTILIZATOR/auto-deal-finder.git
   git push -u origin main
   ```
4. În GitHub, mergi la **Settings** $\rightarrow$ **Secrets and variables** $\rightarrow$ **Actions** $\rightarrow$ **New repository secret**:
   - `TELEGRAM_BOT_TOKEN`: *(tokenul tău de la @BotFather — NU îl scrie niciodată într-un fișier din proiect)*
   - `TELEGRAM_CHAT_ID`: *(ID-ul tău de la @userinfobot)*
   - `GEMINI_API_KEY`: *(opțional, cheia ta de la Google)*
5. Mergi la **Settings** → **Actions** → **General** → **Workflow permissions** și alege **Read and write permissions** (altfel baza de date nu se poate salva între rulări și primești aceleași alerte de fiecare dată).
6. Mergi la tabul **Actions** din repository și apasă **Enable workflows**.
7. **GATA!** Din acest moment, GitHub va porni scanerul la fiecare 15 minute și îți va trimite notificările pe Telegram, chiar dacă PC-ul tău e stins.

---

### Opțiunea 2: Render.com (Rulare Continuă)
Dacă vrei scanare la fiecare minut (non-stop).

> ⚠️ Atenție: Background Worker-ele pe Render sunt servicii **plătite**, iar discul este temporar — la fiecare redeploy baza de date se pierde și poți primi din nou alerte vechi. Pentru rulare gratuită folosește Opțiunea 1.

1. Creează cont pe [render.com](https://render.com).
2. Apasă **New +** $\rightarrow$ **Blueprint** (sau **Background Worker**).
3. Conectează repository-ul tău de GitHub.
4. Render va citi automat fișierul `render.yaml` pe care l-am creat.
5. Introdu variabilele `TELEGRAM_BOT_TOKEN` și `TELEGRAM_CHAT_ID`.
6. Apasă **Apply**. Sistemul va rula 24 de ore din 24 în cloud.

---

## 💻 Partea 3: Rulare pe PC-ul Tău în Fundal (Când lucrezi pe calculator)
Dacă vrei să ruleze și pe PC în timp ce folosești calculatorul fără să vezi nicio fereastră neagră deschisă:
- Dă dublu-click pe fișierul `start_silent_background.vbs`.
- Va rula complet invizibil în fundal.
- Poți rula `setup_startup.bat` (pornire automată la deschiderea PC-ului) și/sau `install_windows_service.bat` (verificare la fiecare 10 minute că sniperul merge). Nu se pornesc instanțe duble: dacă sniperul rulează deja, copia nouă se închide singură.
- Pentru oprire: Task Manager → Detalii → închide procesul `python.exe` / `pythonw.exe` care rulează `run_sniper.py`.
