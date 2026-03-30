from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security.api_key import APIKeyHeader
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Dashcam Security API")

# --- 1. CONFIGURATION DB ---
DB_SETTINGS = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT")
}

# --- 2. API KEY SECURITY ---
API_KEY = os.getenv("API_KEY")
API_KEY_NAME = "X-API-KEY"

# This defines the header we are looking for
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

def get_api_key(api_key: str = Security(api_key_header)):
    if api_key == API_KEY:
        return api_key
    # If the key is missing or wrong, we kick them out
    raise HTTPException(
        status_code=403,
        detail="Forbidden access: Invalid API Key"
    )

# --- 3. ROUTES ---
@app.get("/")
def read_root():
    return {"message": "Welcome to the Dashcam API. Please use your API Key to access data."}

# Notice the added parameter: api_key: str = Depends(get_api_key)
@app.get("/recherche/{plate}")
def get_detections(plate: str, api_key: str = Depends(get_api_key)):
    try:
        conn = psycopg2.connect(**DB_SETTINGS)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        query = "SELECT * FROM detections WHERE plate_number = %s ORDER BY timestamp DESC;"
        cur.execute(query, (plate.upper(),))
        
        results = cur.fetchall()
        cur.close()
        conn.close()
        
        if not results:
            return {"plate": plate.upper(), "message": "No detection found", "history": []}

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
        print(f"❌ API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Security added here as well
@app.get("/stolen/{plate}")
def check_stolen_vehicle(plate: str, api_key: str = Depends(get_api_key)):
    try:
        conn = psycopg2.connect(**DB_SETTINGS)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        query = "SELECT description FROM stolen_vehicles WHERE plate_number = %s;"
        cur.execute(query, (plate.upper(),))
        
        result = cur.fetchone()
        cur.close()
        conn.close()
        
        if result:
            return {
                "plate": plate.upper(),
                "stolen": True,
                "description": result['description']
            }
        else:
            return {
                "plate": plate.upper(),
                "stolen": False
            }
            
    except Exception as e:
        print(f"❌ API Error on /stolen route: {e}")
        raise HTTPException(status_code=500, detail=str(e))