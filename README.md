# Blackvue — IoT Security Project

Système de détection de plaques d'immatriculation via dashcam connectée, avec API de consultation et chatbot intelligent.

## Architecture

```
Raspberry Pi (caméra)
    │  détecte une plaque → publie sur MQTT (AWS IoT)
    ▼
AWS IoT Broker
    │
    ▼
Subscriber (api/) → stocke dans PostgreSQL
    │
    ▼
API REST (api/) ← interrogée par le Chatbot (chatbot/)
```

## Prérequis

- Python 3.10+
- PostgreSQL
- Certificats AWS IoT (à placer dans `certs/`)

## Installation

**1. Créer et activer le virtual environment**
```bash
python3 -m venv venv
source venv/bin/activate
```

**2. Installer les dépendances**
```bash
pip install -r requirements.txt
```

**3. Configurer les variables d'environnement**

Créer un fichier `.env` à la racine :
```
DB_NAME=dashcam_db
DB_USER=jass_admin
DB_PASSWORD=<mot_de_passe>
DB_HOST=localhost
DB_PORT=5432

BROKER_URL=<url_broker_aws>

GEMINI_API_KEY=<votre_clé_api>
```

**4. Initialiser la base de données**
```bash
cp database/init_db.sql /tmp/
sudo -u postgres psql -f /tmp/init_db.sql
```

## Lancement

Ouvrir **3 terminaux** :

**Terminal 1 — API BDD**
```bash
venv/bin/uvicorn api.api:app --reload
```

**Terminal 2 — Subscriber MQTT**
```bash
cd api && ../venv/bin/python subscriber.py
```

**Terminal 3 — Chatbot**
```bash
venv/bin/uvicorn chatbot.server:app --reload --port 8001
```

Ouvrir `http://127.0.0.1:8001` dans le navigateur.
