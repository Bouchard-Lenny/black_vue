import os
import json
import requests
import re
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional
import google.generativeai as genai
from dotenv import load_dotenv
from chatbot.sanitizer import sanitize, SanitizationError

load_dotenv()

API_URL     = "http://127.0.0.1:8000"
API_HEADERS = {"X-API-KEY": os.getenv("API_KEY")}

# ── GEMINI ────────────────────────────────────────────────────────────────────

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash")

SYSTEM_PROMPT = """Tu es un assistant pour la plateforme Blackvue, utilisé par des assureurs et forces de l'ordre.
Tu as accès à une base de données de détections de plaques et de véhicules volés.
Tu peux rechercher l'historique d'une plaque, vérifier si un véhicule est volé, et lister tous les véhicules volés.
Si un utilisateur demande à signaler ou ajouter un véhicule volé, dis-lui d'utiliser le bouton "Signaler un vol" disponible dans l'interface.
Quand tu affiches une liste de détections, utilise toujours un tableau Markdown avec les colonnes : Date/Heure | Latitude | Longitude | Appareil.
Si le statut véhicule volé indique "stolen: true", signale-le en début de réponse sur une ligne dédiée, puis saute une ligne, puis affiche la description sur une nouvelle ligne.
Réponds toujours en français, de façon concise et professionnelle.
"""

def extract_plate(text: str):
    match = re.search(r'\b([A-Z]{2})[\s-]?(\d{3})[\s-]?([A-Z]{2})\b', text.upper())
    if match:
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
    return None

def search_plate(plate: str) -> dict:
    try:
        r = requests.get(f"{API_URL}/recherche/{plate}", headers=API_HEADERS, timeout=5)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

def get_all_stolen() -> dict:
    try:
        r = requests.get(f"{API_URL}/stolen", headers=API_HEADERS, timeout=5)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

def check_stolen(plate: str) -> dict:
    try:
        r = requests.get(f"{API_URL}/stolen/{plate}", headers=API_HEADERS, timeout=5)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

# ── FASTAPI ───────────────────────────────────────────────────────────────────

app = FastAPI()

class Message(BaseModel):
    text: str
    history: list = []

class StolenReport(BaseModel):
    plate: str
    description: Optional[str] = None

@app.get("/", response_class=HTMLResponse)
def index():
    with open(os.path.join(os.path.dirname(__file__), "static/index.html"), encoding="utf-8") as f:
        return f.read()

def validate_and_normalize_plate(plate: str) -> str:
    """Valide et normalise une plaque au format XX-000-XX."""
    match = re.fullmatch(r'([A-Za-z]{2})[\s\-]?(\d{3})[\s\-]?([A-Za-z]{2})', plate.strip())
    if not match:
        raise SanitizationError("Plaque invalide. Format attendu : 2 lettres, 3 chiffres, 2 lettres (ex: AB-123-CD).")
    return f"{match.group(1).upper()}-{match.group(2)}-{match.group(3).upper()}"

@app.get("/alerts")
def get_alerts(since: str = None):
    try:
        params = {"since": since} if since else {}
        r = requests.get(f"{API_URL}/alerts", headers=API_HEADERS, params=params, timeout=5)
        return r.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/report-stolen")
def report_stolen_endpoint(data: StolenReport):
    try:
        plate = validate_and_normalize_plate(data.plate)
        description = None
        if data.description and data.description.strip():
            description = sanitize(data.description.strip())
    except SanitizationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    try:
        r = requests.post(f"{API_URL}/stolen", headers=API_HEADERS,
                          json={"plate": plate, "description": description}, timeout=5)
        return r.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
def chat_endpoint(msg: Message):
    try:
        user_text = sanitize(msg.text)
    except SanitizationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    plate = extract_plate(user_text)
    lower = user_text.lower()

    all_stolen_keywords = ["liste", "tous les véhicules volés", "véhicules volés", "toutes les plaques volées"]
    wants_all_stolen    = any(k in lower for k in all_stolen_keywords) and not plate

    if plate:
        api_data = search_plate(plate)
        if not api_data.get("history"):
            api_data = search_plate(plate.replace("-", ""))
        stolen_data = check_stolen(plate)
        if not stolen_data:
            stolen_data = check_stolen(plate.replace("-", ""))
    else:
        api_data    = None
        stolen_data = None

    all_stolen_data = get_all_stolen() if wants_all_stolen else None

    context = SYSTEM_PROMPT + "\n\n" + user_text
    if api_data:
        context += f"\n\n[Historique détections] : {json.dumps(api_data, ensure_ascii=False)}"
    if stolen_data:
        context += f"\n\n[Statut véhicule volé] : {json.dumps(stolen_data, ensure_ascii=False)}"
    if all_stolen_data:
        context += f"\n\n[Liste tous véhicules volés] : {json.dumps(all_stolen_data, ensure_ascii=False)}"

    history = msg.history + [{"role": "user", "parts": [{"text": context}]}]
    chat    = model.start_chat(history=history[:-1])
    response = chat.send_message(context)

    reply = re.sub(r'THOUGHTS:.*?(?=\n[A-Z]|\Z)', '', response.text, flags=re.DOTALL).strip()

    history.append({"role": "model", "parts": [{"text": reply}]})
    return JSONResponse({"reply": reply, "history": history})
