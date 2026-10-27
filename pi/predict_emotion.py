import sys
from joblib import load
from sentence_transformers import SentenceTransformer

MODEL_PATH = "./model_minilm"
CLASSIFIER_PATH = "emotion_classifier.joblib"

print("Chargement du modèle d'émotions...")
embedder = SentenceTransformer(MODEL_PATH)
classifier = load(CLASSIFIER_PATH)

print("\n--- TESTEUR D'ÉMOTIONS ---")
print("Touche 'Entrée' sur une ligne vide ou tape 'quitter' pour sortir.\n")

while True:
    text = input("Ta phrase > ").strip()
    if not text or text.lower() in ["quitter", "exit"]:
        break

    # Calcul de l'embedding et prédiction
    vec = embedder.encode([text])
    emotion = classifier.predict(vec)[0]
    probas = classifier.predict_proba(vec)[0]
    confidence = max(probas) * 100

    print(f"➜ Émotion détectée : [{emotion.upper()}] (confiance : {confidence:.1f}%)\n")