import os
import json
import threading
import ssl
import requests
import re
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import google.generativeai as genai
import paho.mqtt.client as mqtt
from dotenv import load_dotenv
from chatbot.sanitizer import sanitize, SanitizationError

load_dotenv()

# Config
API_URL = "http://127.0.0.1:8000"
BROKER  = os.getenv("BROKER_URL")
PORT    = 8883

CERTS_DIR = os.path.join(os.path.dirname(__file__), "../certs")
CA_CERT   = os.path.join(CERTS_DIR, "AmazonRootCA1.pem")
CERT      = os.path.join(CERTS_DIR, "BDDfull.crt")
KEY       = os.path.join(CERTS_DIR, "BDD.key")

recent_detections = []

# ── MQTT ─────────────────────────────────────────────────────────────────────

def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        client.subscribe("RPI/+/blackvue")

def on_message(client, userdata, msg):
    try:
        data   = json.loads(msg.payload.decode())
        plates = data.get("plates", [])
        plate  = plates[0].get("plate", "INCONNUE") if plates else "INCONNUE"
        lat    = data.get("location", {}).get("lat", 0.0)
        lon    = data.get("location", {}).get("lon", 0.0)
        recent_detections.append({"plate": plate, "lat": lat, "lon": lon})
        if len(recent_detections) > 20:
            recent_detections.pop(0)
    except Exception:
        pass

def start_mqtt():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="chatbot-web")
    client.tls_set(ca_certs=CA_CERT, certfile=CERT, keyfile=KEY,
                   tls_version=ssl.PROTOCOL_TLS)
    client.on_connect = on_connect
    client.on_message = on_message
    try:
        client.connect(BROKER, PORT)
        client.loop_forever()
    except Exception as e:
        print(f"[MQTT] Erreur : {e}")

# ── GEMINI ────────────────────────────────────────────────────────────────────

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash")
chat  = model.start_chat(history=[])

SYSTEM_PROMPT = """Tu es un assistant pour la plateforme Blackvue, utilisé par des assureurs et forces de l'ordre.
Tu aides à rechercher des véhicules détectés par des dashcams connectées.
Réponds toujours en français, de façon concise et professionnelle.
Quand tu affiches une liste de détections, utilise toujours un tableau Markdown avec les colonnes : Date/Heure | Latitude | Longitude | Appareil.
"""

def extract_plate(text: str):
    match = re.search(r'\b[A-Z]{2}-?\d{3}-?[A-Z]{2}\b', text.upper())
    return match.group(0) if match else None

def search_plate(plate: str) -> dict:
    try:
        r = requests.get(f"{API_URL}/recherche/{plate}", timeout=5)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

# ── FASTAPI ───────────────────────────────────────────────────────────────────

app = FastAPI()

class Message(BaseModel):
    text: str

@app.on_event("startup")
def startup():
    threading.Thread(target=start_mqtt, daemon=True).start()

@app.get("/", response_class=HTMLResponse)
def index():
    with open(os.path.join(os.path.dirname(__file__), "static/index.html"), encoding="utf-8") as f:
        return f.read()

@app.post("/chat")
def chat_endpoint(msg: Message):
    try:
        user_text = sanitize(msg.text)
    except SanitizationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    plate     = extract_plate(user_text)
    api_data  = search_plate(plate) if plate else None

    context = SYSTEM_PROMPT + "\n\n" + user_text
    if api_data:
        context += f"\n\n[Données BDD] : {json.dumps(api_data, ensure_ascii=False)}"
    if recent_detections:
        context += f"\n\n[Détections récentes MQTT] : {json.dumps(recent_detections[-5:], ensure_ascii=False)}"

    response = chat.send_message(context)
    return JSONResponse({"reply": response.text})

@app.get("/detections")
def get_detections():
    return JSONResponse(recent_detections)
