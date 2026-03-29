-- Création de l'utilisateur et de la base de données
CREATE USER jass_admin WITH PASSWORD 'jass';
CREATE DATABASE dashcam_db OWNER jass_admin;

-- Connexion à la base
\c dashcam_db

-- Droits
GRANT ALL PRIVILEGES ON DATABASE dashcam_db TO jass_admin;

-- Table des détections de plaques
CREATE TABLE detections (
    id SERIAL PRIMARY KEY,
    plate_number VARCHAR(20) NOT NULL,
    latitude NUMERIC(9, 6),
    longitude NUMERIC(9, 6),
    device_id VARCHAR(50),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table des véhicules volés
CREATE TABLE stolen_vehicles (
    id SERIAL PRIMARY KEY,
    plate_number VARCHAR(20) UNIQUE NOT NULL,
    description TEXT
);

-- Droits sur les tables
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO jass_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO jass_admin;

-- Données de test : détections
INSERT INTO detections (plate_number, latitude, longitude, device_id) VALUES
    ('AB-123-CD', 48.8566, 2.3522, 'RPI11'),
    ('AB-123-CD', 48.8570, 2.3530, 'RPI11'),
    ('XY-456-ZZ', 45.7640, 4.8357, 'RPI11'),
    ('EF-789-GH', 43.2965, 5.3811, 'RPI11');

-- Données de test : véhicules volés
INSERT INTO stolen_vehicles (plate_number, description) VALUES
    ('XY-456-ZZ', 'Véhicule volé le 2026-01-15, Renault Clio rouge'),
    ('EF-789-GH', 'Véhicule recherché par la police, BMW noire');
