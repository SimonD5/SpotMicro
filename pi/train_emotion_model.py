import time
import numpy as np
from joblib import dump
from sentence_transformers import SentenceTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, accuracy_score

from emotions_data import EMOTIONS, TEST, TRAIN

MODEL_PATH = "./model_minilm"
OUTPUT_CLASSIFIER = "emotion_classifier.joblib"

print("1. Chargement du modèle d'embeddings depuis le dossier local...")
embedder = SentenceTransformer(MODEL_PATH)

# Preparation des données d'entraînement
X_train_text = []
y_train = []
for emotion, sentences in TRAIN.items():
    for sentence in sentences:
        X_train_text.append(sentence)
        y_train.append(emotion)

print(f"2. Vectorisation de {len(X_train_text)} phrases d'entraînement...")
t0 = time.time()
X_train_embeddings = embedder.encode(X_train_text, show_progress_bar=True)
print(f"   Vectorisation terminée en {time.time() - t0:.2f} s.")

print("3. Entraînement du classifieur (LogisticRegression)...")
classifier = LogisticRegression(max_iter=1000, random_state=42)
classifier.fit(X_train_embeddings, y_train)

# Sauvegarde du classifieur
dump(classifier, OUTPUT_CLASSIFIER)
print(f"   Classifieur sauvegardé dans '{OUTPUT_CLASSIFIER}'.")

# Évaluation sur le jeu TEST
print("\n4. Évaluation sur le jeu TEST...")
X_test_text = []
y_test_true = []
for emotion, sentences in TEST.items():
    for sentence in sentences:
        X_test_text.append(sentence)
        y_test_true.append(emotion)

t0 = time.time()
X_test_embeddings = embedder.encode(X_test_text)
y_test_pred = classifier.predict(X_test_embeddings)
inference_time = (time.time() - t0) / len(X_test_text)

acc = accuracy_score(y_test_true, y_test_pred)
print(f"\n--- RÉSULTATS PISTE A ---")
print(f"Précision (Accuracy) : {acc * 100:.1f} %")
print(f"Temps moyen par phrase : {inference_time * 1000:.1f} ms")
print("\nRapport détaillé par émotion :")
print(classification_report(y_test_true, y_test_pred, target_names=EMOTIONS))