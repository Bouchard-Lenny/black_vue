import json
import ssl
from datetime import datetime
import paho.mqtt.client as mqtt

# Config broker
BROKER = "a2gqtw1w63pv1n-ats.iot.us-east-1.amazonaws.com"
PORT = 8883
TOPIC = "RPI/+/blackvue"
CLIENT_ID = "chatbot"

CA_CERT = "AmazonRootCA1.pem"
CERT = "BDDfull.crt"
KEY = "BDD.key"

# Stockage en mémoire des détections reçues
detections = []


def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print("Connecté au broker MQTT")
        client.subscribe(TOPIC)
        print(f"Abonné au topic : {TOPIC}")
    else:
        print(f"Erreur de connexion, code : {reason_code}")


def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
    except json.JSONDecodeError:
        payload = msg.payload.decode()

    detection = {
        "topic": msg.topic,
        "timestamp": datetime.now().isoformat(),
        "data": payload,
    }
    detections.append(detection)

    print(f"\n[{detection['timestamp']}] Message reçu sur {msg.topic}")
    print(json.dumps(payload, indent=2))


def start_listener():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=CLIENT_ID)

    client.tls_set(
        ca_certs=CA_CERT,
        certfile=CERT,
        keyfile=KEY,
        tls_version=ssl.PROTOCOL_TLS,
    )

    client.on_connect = on_connect
    client.on_message = on_message

    print(f"Connexion à {BROKER}...")
    client.connect(BROKER, PORT)
    client.loop_forever()


if __name__ == "__main__":
    start_listener()
