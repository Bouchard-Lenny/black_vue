import paho.mqtt.client as mqtt
import ssl
import psycopg2
import json
import sys
import os
from dotenv import load_dotenv

load_dotenv()

# --- 1. CONFIGURATION DE LA BASE DE DONNÉES ---
DB_SETTINGS = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT")
}

# --- 2. CONFIGURATION AWS IOT ---
BROKER_URL = os.getenv("BROKER_URL")
PORT = 8883
TOPIC = "#"  # Écoute absolue pour le diagnostic

# --- 3. FONCTION POUR ENREGISTRER DANS POSTGRESQL ---
def save_to_db(plate, lat, lon, device_id):
    try:
        conn = psycopg2.connect(**DB_SETTINGS)
        cur = conn.cursor()
        query = """
            INSERT INTO detections (plate_number, latitude, longitude, device_id)
            VALUES (%s, %s, %s, %s);
        """
        cur.execute(query, (plate, lat, lon, device_id))
        conn.commit()
        cur.close()
        conn.close()
        print(f"[DB] ✅ Plaque {plate} sauvegardée avec succès.")
    except Exception as e:
        print(f"[DB] ❌ Erreur d'enregistrement PostgreSQL : {e}")

# --- 4. ACTIONS QUAND LA CONNEXION EST ÉTABLIE ---
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("\n✅ CONNECTÉ AVEC SUCCÈS AU BROKER AWS !")
        client.subscribe(TOPIC)
        print(f"📡 ÉCOUTE ACTIVE SUR LE TOPIC : {TOPIC}")
        print("------------------------------------------")
    else:
        print(f"❌ ÉCHEC DE CONNEXION. Code erreur : {rc}")
        if rc == 5: print("👉 Cause probable : Problème d'autorisation (Policy AWS).")

def check_stolen(plate):
    try:
        conn = psycopg2.connect(**DB_SETTINGS)
        cur = conn.cursor()
        cur.execute("SELECT description FROM stolen_vehicles WHERE plate_number = %s", (plate,))
        result = cur.fetchone()
        cur.close()
        conn.close()
        return result
    except Exception as e:
        print(f"❌ Erreur check stolen : {e}")
        return None
    
# --- 5. ACTIONS QUAND UN MESSAGE ARRIVE ---
def on_message(client, userdata, msg):
    print(f"\n🔔 [MQTT] MESSAGE REÇU")
    try:
        payload = msg.payload.decode()
        data = json.loads(payload)
        
        plates_list = data.get("plates", [])
        plate = plates_list[0].get("plate", "INCONNUE") if plates_list else "AUCUNE_DETECTION"
        
        location = data.get("location", {})
        lat = location.get("lat", 0.0)
        lon = location.get("lon", 0.0)
        device_id = data.get("device_id", "Unknown")

        print(f"🔎 Analyse : {plate} par {device_id}")
        
        # 1. Sauvegarde
        save_to_db(plate, lat, lon, device_id)
        
        # 2. Vérification Alerte
        stolen_info = check_stolen(plate)
        if stolen_info:
            print("\n" + "!"*50)
            print(f"🚨 ALERTE VÉHICULE VOLÉ DÉTECTÉ : {plate}")
            print(f"📝 Infos : {stolen_info[0]}")
            print("!"*50 + "\n")
            
    except Exception as e:
        print(f"⚠️ Erreur de traitement : {e}")

# --- 6. INITIALISATION DU CLIENT ---
# ID unique pour éviter que AWS ne te déconnecte (Mise à jour v2 de l'API MQTT)
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id="BDD")

client.on_connect = on_connect
client.on_message = on_message

# Configuration TLS avec les bons chemins relatifs
try:
    client.tls_set(
        ca_certs="../certs/AmazonRootCA1.pem",
        certfile="../certs/BDDfull.crt",
        keyfile="../certs/BDD.key",
        cert_reqs=ssl.CERT_REQUIRED,
        tls_version=ssl.PROTOCOL_TLSv1_2
    )
except FileNotFoundError as e:
    print(f"❌ ERREUR : Impossible de trouver les certificats : {e}")
    sys.exit(1)

# Connexion
print("🚀 Démarrage de l'Ingestor...")
try:
    client.connect(BROKER_URL, PORT, keepalive=60)
    client.loop_forever()
except Exception as e:
    print(f"💥 Impossible de se connecter au Broker : {e}")