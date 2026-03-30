import os
import json
import threading
import ssl
import requests
from google import genai
import paho.mqtt.client as mqtt
from dotenv import load_dotenv

load_dotenv()

# Configuration
API_URL = "http://127.0.0.1:8000"
BROKER = os.getenv("BROKER_URL")
TOPIC = "RPI/+/blackvue"
PORT = 8883

CERTS_DIR = os.path.join(os.path.dirname(__file__), "../certs")
CA_CERT   = os.path.join(CERTS_DIR, "AmazonRootCA1.pem")
CERT      = os.path.join(CERTS_DIR, "BDDfull.crt")
KEY       = os.path.join(CERTS_DIR, "BDD.key")

# Dernières détections reçues via MQTT (max 20)
recent_detections = []

# ── MQTT ────────────────────────────────────────────────────────────────────

def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        client.subscribe(TOPIC)
        print("[MQTT] Connecté et en écoute des détections en temps réel.")
    else:
        print(f"[MQTT] Erreur de connexion : {reason_code}")

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
        plates = data.get("plates", [])
        plate  = plates[0].get("plate", "INCONNUE") if plates else "INCONNUE"
        lat    = data.get("location", {}).get("lat", 0.0)
        lon    = data.get("location", {}).get("lon", 0.0)

        detection = {"plate": plate, "lat": lat, "lon": lon, "topic": msg.topic}
        recent_detections.append(detection)
        if len(recent_detections) > 20:
            recent_detections.pop(0)

        print(f"\n[ALERTE] Plaque détectée en temps réel : {plate} ({lat}, {lon})")
        print("Chatbot > ", end="", flush=True)
    except Exception as e:
        print(f"[MQTT] Erreur de traitement : {e}")

def start_mqtt():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="chatbot")
    client.tls_set(ca_certs=CA_CERT, certfile=CERT, keyfile=KEY,
                   tls_version=ssl.PROTOCOL_TLS)
    client.on_connect = on_connect
    client.on_message = on_message
    try:
        client.connect(BROKER, PORT)
        client.loop_forever()
    except Exception as e:
        print(f"[MQTT] Impossible de se connecter : {e}")

# ── API BDD ──────────────────────────────────────────────────────────────────

def search_plate(plate: str) -> dict:
    try:
        response = requests.get(f"{API_URL}/recherche/{plate}", timeout=5)
        return response.json()
    except Exception as e:
        return {"error": str(e)}

# ── GEMINI ───────────────────────────────────────────────────────────────────

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "gemini-2.5-flash"

SYSTEM_PROMPT = """Tu es un assistant pour la plateforme Blackvue, utilisé par des assureurs et forces de l'ordre.
Tu aides à rechercher des véhicules détectés par des dashcams connectées.

Quand l'utilisateur demande des informations sur une plaque, tu reçois les données de la base de données et tu les présentes clairement.
Réponds toujours en français, de façon concise et professionnelle.
"""

conversation_history = []

def ask_gemini(user_message: str, api_data: dict = None) -> str:
    context = user_message
    if api_data:
        context += f"\n\n[Données de la base] : {json.dumps(api_data, ensure_ascii=False)}"
    if recent_detections:
        context += f"\n\n[Détections récentes via MQTT] : {json.dumps(recent_detections[-5:], ensure_ascii=False)}"

    conversation_history.append({"role": "user", "parts": [{"text": context}]})

    response = client.models.generate_content(
        model=MODEL,
        contents=conversation_history,
        config={"system_instruction": SYSTEM_PROMPT}
    )

    reply = response.text
    conversation_history.append({"role": "model", "parts": [{"text": reply}]})
    return reply

# ── BOUCLE PRINCIPALE ────────────────────────────────────────────────────────

def extract_plate(text: str):
    """Cherche une plaque dans le message (format XX-000-XX ou similaire)."""
    import re
    match = re.search(r'\b[A-Z]{2}-?\d{3}-?[A-Z]{2}\b', text.upper())
    return match.group(0) if match else None

def main():
    # Démarrage MQTT en arrière-plan
    mqtt_thread = threading.Thread(target=start_mqtt, daemon=True)
    mqtt_thread.start()

    print("=== Chatbot Blackvue ===")
    print("Posez vos questions sur les plaques détectées. (Ctrl+C pour quitter)\n")

    while True:
        try:
            user_input = input("Vous > ").strip()
            if not user_input:
                continue

            # Détection automatique d'une plaque dans la question
            plate = extract_plate(user_input)
            api_data = search_plate(plate) if plate else None

            response = ask_gemini(user_input, api_data)
            print(f"Chatbot > {response}\n")

        except KeyboardInterrupt:
            print("\nAu revoir.")
            break
        except Exception as e:
            print(f"Erreur : {e}")

if __name__ == "__main__":
    main()
