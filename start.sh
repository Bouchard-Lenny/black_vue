#!/bin/bash

echo "=== Blackvue - Démarrage des services ==="

# Détection du terminal disponible
if command -v gnome-terminal &> /dev/null; then
    TERM_CMD="gnome-terminal --"
elif command -v xterm &> /dev/null; then
    TERM_CMD="xterm -e"
elif command -v konsole &> /dev/null; then
    TERM_CMD="konsole -e"
else
    echo "Aucun terminal graphique trouvé (gnome-terminal, xterm, konsole)."
    exit 1
fi

DIR=$(pwd)

# Terminal 1 : API BDD
$TERM_CMD bash -c "cd $DIR && echo '=== API BDD ===' && venv/bin/uvicorn api.api:app --reload; exec bash" &
sleep 1

# Terminal 2 : Subscriber MQTT
$TERM_CMD bash -c "cd $DIR/api && echo '=== Subscriber MQTT ===' && ../venv/bin/python subscriber.py; exec bash" &
sleep 1

# Terminal 3 : Chatbot
$TERM_CMD bash -c "cd $DIR && echo '=== Chatbot ===' && venv/bin/uvicorn chatbot.server:app --reload --port 8001; exec bash" &

echo ""
echo "Les 3 services démarrent..."
echo "Chatbot disponible sur http://127.0.0.1:8001"
