#!/bin/bash

echo "=== Blackvue - Installation ==="

# 1. Venv
echo ""
echo "[1/4] Vérification du virtual environment..."
if [ -d "venv" ]; then
    echo "venv déjà existant, ignoré."
else
    python3 -m venv venv
    echo "venv créé."
fi

# 2. Dépendances
echo ""
echo "[2/4] Installation des dépendances..."
venv/bin/pip install -r requirements.txt -q
echo "OK"

# 2. Fichier .env
echo ""
echo "[3/4] Configuration du fichier .env..."
if [ -f ".env" ]; then
    echo ".env déjà existant, ignoré."
else
    cat > .env << 'EOF'
DB_NAME=dashcam_db
DB_USER=jass_admin
DB_PASSWORD=jass
DB_HOST=localhost
DB_PORT=5432

BROKER_URL=a2gqtw1w63pv1n-ats.iot.us-east-1.amazonaws.com

GEMINI_API_KEY=remplace_par_ta_clé
EOF
    echo ".env créé. Pense à y mettre ta clé Gemini."
fi

# 3. Base de données
echo ""
echo "[4/4] Initialisation de la base de données..."
cp database/init_db.sql /tmp/blackvue_init.sql
sudo -u postgres psql -f /tmp/blackvue_init.sql > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "OK"
else
    echo "La BDD existe peut-être déjà, ou une erreur s'est produite."
fi

echo ""
echo "=== Installation terminée ==="
echo "Lance ./start.sh pour démarrer les services."
