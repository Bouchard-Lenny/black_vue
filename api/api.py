from fastapi import FastAPI, HTTPException
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Dashcam Security API")

# Configuration DB (identique au subscriber)
DB_SETTINGS = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT")
}

@app.get("/")
def read_root():
    return {"message": "Bienvenue sur l'API de consultation des détections Dashcam"}

@app.get("/recherche/{plate}")
def get_detections(plate: str):
    try:
        conn = psycopg2.connect(**DB_SETTINGS)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Correction ici : on utilise 'timestamp' au lieu de 'created_at'
        query = "SELECT * FROM detections WHERE plate_number = %s ORDER BY timestamp DESC;"
        cur.execute(query, (plate.upper(),))
        
        results = cur.fetchall()
        cur.close()
        conn.close()
        
        if not results:
            return {"plate": plate.upper(), "message": "Aucune détection trouvée", "history": []}

        # Conversion des types pour que le JSON soit valide
        for row in results:
            if row.get('timestamp'):
                row['timestamp'] = row['timestamp'].isoformat()
            if row.get('latitude'):
                row['latitude'] = float(row['latitude'])
            if row.get('longitude'):
                row['longitude'] = float(row['longitude'])

        return {
            "plate": plate.upper(), 
            "status": "success",
            "total_detections": len(results), 
            "history": results
        }
        
    except Exception as e:
        print(f"❌ Erreur API : {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/stolen/{plate}")
def check_stolen_vehicle(plate: str):
    try:
        conn = psycopg2.connect(**DB_SETTINGS)
        # On utilise RealDictCursor pour récupérer les résultats sous forme de dictionnaire
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        query = "SELECT description FROM stolen_vehicles WHERE plate_number = %s;"
        cur.execute(query, (plate.upper(),))
        
        result = cur.fetchone()
        cur.close()
        conn.close()
        
        # Si la plaque est trouvée dans la table stolen_vehicles
        if result:
            return {
                "plate": plate.upper(),
                "stolen": True,
                "description": result['description']
            }
        # Si la plaque n'est pas trouvée
        else:
            return {
                "plate": plate.upper(),
                "stolen": False
            }
            
    except Exception as e:
        print(f"❌ Erreur API sur la route /stolen : {e}")
        raise HTTPException(status_code=500, detail=str(e))