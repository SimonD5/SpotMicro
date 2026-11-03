import json
import os
import socket
import time
from joblib import load
from sentence_transformers import SentenceTransformer
from emotions import play_emotion

# Récupération dynamique des chemins (dossier pi/ et racine du projet)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))  # /home/simon/spot-micro/pi
BASE_DIR = os.path.dirname(SCRIPT_DIR)                   # /home/simon/spot-micro

# Recherche de emotion_classifier.joblib dans pi/ puis à la racine
CLASSIFIER_PATH = os.path.join(SCRIPT_DIR, "emotion_classifier.joblib")
if not os.path.exists(CLASSIFIER_PATH):
    CLASSIFIER_PATH = os.path.join(BASE_DIR, "emotion_classifier.joblib")

# Recherche de model_minilm dans pi/, puis à la racine, sinon fallback Hugging Face
if os.path.exists(os.path.join(SCRIPT_DIR, "model_minilm")):
    MODEL_PATH = os.path.join(SCRIPT_DIR, "model_minilm")
elif os.path.exists(os.path.join(BASE_DIR, "model_minilm")):
    MODEL_PATH = os.path.join(BASE_DIR, "model_minilm")
else:
    MODEL_PATH = "all-MiniLM-L6-v2"

HOST = "0.0.0.0"  # Écoute sur toutes les interfaces réseau
PORT = 5005       # Port d'écoute

print(f"1. Chargement du classifieur ({CLASSIFIER_PATH})...")
t0 = time.time()
embedder = SentenceTransformer(MODEL_PATH)
classifier = load(CLASSIFIER_PATH)
print(f"   Modèle prêt en {time.time() - t0:.2f} s.")

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind((HOST, PORT))
server_socket.listen(5)

print(f"\n2. Serveur TCP démarré sur le port {PORT}.")
print("   En attente de connexions du PC...\n")

try:
    while True:
        client_socket, client_address = server_socket.accept()
        print(f"[+] Connexion reçue de {client_address[0]}:{client_address[1]}")
        
        while True:
            data = client_socket.recv(1024)
            if not data:
                print(f"[-] Client {client_address[0]} déconnecté.\n")
                break
            
            text = data.decode("utf-8").strip()
            if not text:
                continue
            
            # Inférence IA
            t_start = time.time()
            vec = embedder.encode([text])
            emotion = classifier.predict(vec)[0]
            confidence = float(max(classifier.predict_proba(vec)[0]) * 100)
            elapsed_ms = (time.time() - t_start) * 1000

            print(f"  ➜ Reçu : '{text}'")
            print(f"  ➜ Émotion : [{emotion.upper()}] ({confidence:.1f}%) en {elapsed_ms:.1f} ms")

            # Réaction sonore R2-D2 via le buzzer (choisi une des 5 variations au hasard)
            play_emotion(emotion)
            print()

            # Réponse JSON envoyée au client
            response = {
                "texte": text,
                "emotion": emotion,
                "confiance": round(confidence, 1),
                "ms": round(elapsed_ms, 1)
            }
            client_socket.sendall((json.dumps(response) + "\n").encode("utf-8"))

        client_socket.close()

except KeyboardInterrupt:
    print("\nArrêt du serveur.")
finally:
    server_socket.close()