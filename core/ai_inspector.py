"""
Multi-AI Super-Inspector (Google Gemini 2.0 Flash & OpenAI GPT-4o)
==================================================================
Sistem de inspectie avansat multi-modal pentru ponturi auto:
1. Text Reasoning: Analizeaza psihologia vanzatorului, subtilitatile din textul romanesc,
   defectele mecanice mascate si neconcordantele tehnice.
2. Computer Vision: Analizeaza pozele masinii (lufturi caroserie, elemente revopsite,
   martori aprinsi in bord, uzura volan/interior vs km declarati).
3. Fallback Heuristic: Daca nu exista cheie API configurata, foloseste motorul euristic
   local si instruieste utilizatorul cum sa activeze cheia gratuita Google Gemini.
"""

import os
import re
import json
import base64
import requests
from typing import Dict, List, Tuple, Optional
from config.settings import (
    GEMINI_API_KEY,
    OPENAI_API_KEY,
    AI_INSPECTION_ENABLED,
    AI_MIN_CONFIDENCE_SCORE,
    GEMINI_MODELS,
    OPENAI_MODEL,
)


def _normalize_ai_result(parsed: Dict, model_label: str, default_summary: str) -> Dict:
    """Valideaza raspunsul AI (scor numeric 0-100, lista de riscuri) - LLM-urile nu respecta mereu schema."""
    try:
        score = int(float(parsed.get("confidence_score", 50)))
    except (TypeError, ValueError):
        score = 50
    score = max(0, min(100, score))
    approved_raw = parsed.get("approved", False)
    if isinstance(approved_raw, str):
        approved = approved_raw.strip().lower() in ("true", "da", "yes", "1")
    else:
        approved = bool(approved_raw)
    if score < AI_MIN_CONFIDENCE_SCORE:
        approved = False
    flags = parsed.get("risk_flags", [])
    if isinstance(flags, str):
        flags = [flags] if flags.strip() else []
    elif not isinstance(flags, list):
        flags = []
    flags = [str(f).strip() for f in flags if str(f).strip()][:5]
    return {
        "approved": approved,
        "ai_score": score,
        "ai_summary": str(parsed.get("summary") or default_summary)[:400],
        "risk_flags": flags,
        "model_used": model_label,
    }


class MultiAIInspector:
    """
    Inspector Multi-AI ce combina cele mai puternice modele din lume:
    - Google Gemini 2.0 Flash / 1.5 Flash (Super-rapid, viziune de top, gratuit via AI Studio)
    - OpenAI GPT-4o / GPT-4o-mini (Rationament de elita)
    """

    @classmethod
    def is_active(cls) -> bool:
        return AI_INSPECTION_ENABLED and bool(GEMINI_API_KEY or OPENAI_API_KEY)

    @classmethod
    def inspect_deal(cls, listing: Dict) -> Dict:
        """
        Executa inspectia AI completa (Text + Imagini daca sunt disponibile).
        Returneaza:
            {
                "approved": bool,
                "ai_score": int (0-100),
                "ai_summary": str,
                "risk_flags": List[str],
                "model_used": str
            }
        """
        if not AI_INSPECTION_ENABLED:
            return {
                "approved": True,
                "ai_score": None,
                "ai_summary": "Inspecția AI este dezactivată din configurare.",
                "risk_flags": [],
                "model_used": "none",
            }

        # Daca avem cheie Gemini sau OpenAI, folosim AI-ul de varf
        if GEMINI_API_KEY:
            res = cls._inspect_with_gemini(listing)
            if res:
                return res

        if OPENAI_API_KEY:
            res = cls._inspect_with_openai(listing)
            if res:
                return res

        # Fara cheie API (sau daca API-ul a picat) rulam inspectia euristica locala
        if GEMINI_API_KEY or OPENAI_API_KEY:
            print("[AI Inspector] API-urile AI nu au raspuns - se foloseste verificarea locala.")
        return cls._local_heuristic_inspection(listing)

    # =========================================================================
    # 1. GOOGLE GEMINI (2.0 Flash / 1.5 Flash) - MULTIMODAL (TEXT + IMAGINI)
    # =========================================================================
    @classmethod
    def _inspect_with_gemini(cls, listing: Dict) -> Optional[Dict]:
        """Apeleaza Google Gemini 2.0 Flash cu analiza de text si viziune."""
        title = listing.get("title", "")
        description = listing.get("description", "")
        price = listing.get("price_eur", 0)
        mileage = listing.get("mileage", 0)
        year = listing.get("year", 0)
        make = listing.get("make", "")
        model = listing.get("model", "")
        photo_url = listing.get("photo_url", "")

        system_instruction = (
            "Esti cel mai experimentat mecanic auto si inspector tehnic RAR din Romania. "
            "Misiunea ta este sa analizezi anuntul de vanzare auto si sa decizi daca masina este o teapa "
            "sau o oportunitate sigura de profit la revanzare.\n"
            "Cauta:\n"
            "1. Defecte mecanice mascate in descriere (ex: 'bate la rece', 'trebuie putina atentie', 'martor aprins', 'cutia agata', 'fum la pornire')\n"
            "2. Limbaj tipic de samsar sau minciuni de vanzator (ex: 'o dau ca plec din tara', 'masina de batran', 'carte pierduta')\n"
            "3. Neconcordante intre pretul cerut si valoarea reala (daca e suspect de ieftina pentru anul si dotarile ei)\n"
            "4. Daca poza atasata indica lufturi anormale, elemente revopsite, daune vizibile sau uzura excesiva.\n\n"
            "Raspunde STRICT in format JSON:\n"
            "{\n"
            '  "approved": true/false,\n'
            '  "confidence_score": 0-100,\n'
            '  "risk_flags": ["lista", "cu", "riscuri"],\n'
            '  "summary": "rezumat scurt in romana de max 2 propozitii"\n'
            "}"
        )

        user_content = (
            f"MASINA: {make.upper()} {model.upper()}\n"
            f"TITLU: {title}\n"
            f"AN: {year}\n"
            f"KILOMETRI: {int(mileage or 0):,} km\n"
            f"PRET CERUT: {float(price or 0):,.0f} EUR\n"
            f"DESCRIERE COMPLETA VANZATOR:\n{description[:2500]}"
        )

        parts = [{"text": user_content}]

        # Descarcam poza daca exista pentru inspectie vizuala (limitata la 1 poza rapida)
        if photo_url and photo_url.startswith("http"):
            img_part = cls._fetch_image_as_part(photo_url)
            if img_part:
                parts.append(img_part)

        for model_name in GEMINI_MODELS:
            # Cheia se trimite in header, NU in URL: URL-urile apar in mesajele de eroare/loguri
            # (inclusiv in logurile GitHub Actions) si cheia ar fi expusa.
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
            payload = {
                "contents": [{"role": "user", "parts": parts}],
                "systemInstruction": {"parts": [{"text": system_instruction}]},
                "generationConfig": {
                    "temperature": 0.1,
                    "responseMimeType": "application/json",
                },
            }

            try:
                resp = requests.post(
                    url, json=payload, timeout=20,
                    headers={"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts_resp = (candidates[0].get("content") or {}).get("parts") or [{}]
                        text_resp = parts_resp[0].get("text", "")
                        parsed = cls._clean_and_parse_json(text_resp)
                        if parsed:
                            return _normalize_ai_result(parsed, f"Google {model_name}", "Inspecție finalizată.")
                else:
                    print(f"[AI Inspector] Gemini {model_name} a raspuns HTTP {resp.status_code}")
            except Exception as e:
                print(f"[AI Inspector] Eroare Gemini ({model_name}): {type(e).__name__}")

        return None

    # =========================================================================
    # 2. OPENAI GPT-4o / GPT-4o-mini
    # =========================================================================
    @classmethod
    def _inspect_with_openai(cls, listing: Dict) -> Optional[Dict]:
        """Apeleaza OpenAI GPT-4o pentru inspectie inteligenta."""
        title = listing.get("title", "")
        description = listing.get("description", "")
        price = listing.get("price_eur", 0)
        mileage = listing.get("mileage", 0)
        year = listing.get("year", 0)
        make = listing.get("make", "")
        model = listing.get("model", "")
        photo_url = listing.get("photo_url", "")

        system_msg = (
            "Esti un inspector tehnic auto expert si mecanic din Romania. Evaluezi oportunitati de flipping auto. "
            "Raspunde STRICT in format JSON valid cu cheile: "
            '{"approved": bool, "confidence_score": int (0-100), "risk_flags": list[str], "summary": str}. '
            "Daca masina are semne de daune, piese defecte, limbaj de samsar sau pret suspect, approved=false."
        )

        user_content_blocks = [
            {
                "type": "text",
                "text": (
                    f"MASINA: {make} {model}, AN: {year}, KM: {mileage}, PRET: {price} EUR.\n"
                    f"TITLU: {title}\n"
                    f"DESCRIERE: {description[:2000]}"
                ),
            }
        ]

        if photo_url and photo_url.startswith("http"):
            user_content_blocks.append({
                "type": "image_url",
                "image_url": {"url": photo_url, "detail": "low"},
            })

        payload = {
            "model": OPENAI_MODEL,
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_content_blocks},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        }

        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }

        try:
            resp = requests.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers, timeout=20)
            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                parsed = cls._clean_and_parse_json(content)
                if parsed:
                    return _normalize_ai_result(parsed, f"OpenAI {OPENAI_MODEL}", "Inspecție OpenAI finalizată.")
            else:
                print(f"[AI Inspector] OpenAI a raspuns HTTP {resp.status_code}")
        except Exception as e:
            print(f"[AI Inspector] Eroare OpenAI: {type(e).__name__}")

        return None

    # =========================================================================
    # 3. LOCAL HEURISTIC INSPECTION (CAND NU EXISTA CHEIE API)
    # =========================================================================
    @classmethod
    def _local_heuristic_inspection(cls, listing: Dict) -> Dict:
        """
        Inspectie semantica euristica locala atunci cand utilizatorul nu a configurat inca
        o cheie API Gemini/OpenAI. Asigura ca masina nu scapa nicio capcana de text.
        """
        title = listing.get("title", "").lower()
        desc = listing.get("description", "").lower()
        text = f"{title} {desc}"

        score = 85
        risk_flags = []

        # Indicatori de risc semantic suplimentar
        subtle_red_flags = [
            ("se vinde urgent", "Urgenta nejustificata - risc de viciu ascuns grav"),
            ("usor negociabil la fata locului", "Posibile defecte estetice sau mecanice vizibile doar live"),
            ("pret fix", "Marja zero de negociere suplimentara"),
            ("primul venit", "Tehnica de presiune psihologica tipica pietei samsarilor"),
            ("porneste la sfert", "Expresie de cosmetizare a unor defecte electrice/injectoare"),
            ("investitii recente", "Masina problematica in care s-au bagat bani fara succes"),
            ("accept orice test", "Formula standard - nu garanteaza starea tehnica reala"),
        ]

        for phrase, reason in subtle_red_flags:
            if phrase in text:
                score -= 8
                risk_flags.append(reason)

        approved = score >= 60

        summary = (
            "Analiză euristică de siguranță completă. "
            "Pentru activare inspecție vizuală Gemini/GPT-4o, adaugă GEMINI_API_KEY în .env."
        )

        return {
            "approved": approved,
            "ai_score": score,
            "ai_summary": summary,
            "risk_flags": risk_flags[:3],
            "model_used": "Verificare locala (fara AI)",
        }

    # =========================================================================
    # UTILITARE
    # =========================================================================
    @staticmethod
    def _fetch_image_as_part(image_url: str) -> Optional[Dict]:
        """Descarca imaginea si o pregateste ca part inlineData pentru Gemini API."""
        try:
            r = requests.get(image_url, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code == 200 and len(r.content) < 4 * 1024 * 1024:
                mime = r.headers.get("Content-Type", "image/jpeg")
                if "jpeg" in mime or "jpg" in mime:
                    mime_type = "image/jpeg"
                elif "png" in mime:
                    mime_type = "image/png"
                elif "webp" in mime:
                    mime_type = "image/webp"
                else:
                    mime_type = "image/jpeg"

                b64 = base64.b64encode(r.content).decode("utf-8")
                return {
                    "inlineData": {
                        "mimeType": mime_type,
                        "data": b64,
                    }
                }
        except Exception:
            pass
        return None

    @staticmethod
    def _clean_and_parse_json(text: str) -> Optional[Dict]:
        """Extrage si parseaza un obiect JSON din raspunsul LLM-ului."""
        try:
            clean = text.strip()
            if clean.startswith("```"):
                clean = re.sub(r"^```(?:json)?\s*", "", clean)
                clean = re.sub(r"\s*```$", "", clean)
            return json.loads(clean.strip())
        except Exception:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except Exception:
                    pass
        return None
