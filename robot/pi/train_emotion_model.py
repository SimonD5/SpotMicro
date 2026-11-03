import os
import time

try:
    import numpy as np
except ImportError:
    np = None

try:
    from joblib import dump
except ImportError:
    dump = None

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

try:
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score, classification_report
except ImportError:
    LogisticRegression = None
    accuracy_score = None
    classification_report = None

try:
    from .emotions_data import EMOTIONS, TEST, TRAIN
except ImportError:
    from emotions_data import EMOTIONS, TEST, TRAIN

DEFAULT_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
ROOT_DIR = os.path.dirname(BASE_DIR)


def _candidate_dirs(script_dir=SCRIPT_DIR):
    base_dir = os.path.dirname(script_dir)
    root_dir = os.path.dirname(base_dir)
    dirs = []
    for folder in (script_dir, base_dir, root_dir):
        if folder and folder not in dirs:
            dirs.append(folder)
    return dirs


def resolve_model_path(script_dir=SCRIPT_DIR, default_model=DEFAULT_MODEL_NAME):
    """Recherche model_minilm dans pi/ puis dans les parents, sinon fallback Hugging Face multilingue."""
    for folder in _candidate_dirs(script_dir):
        candidate = os.path.join(folder, "model_minilm")
        if os.path.exists(candidate):
            return candidate
    return default_model


MODEL_PATH = resolve_model_path()
OUTPUT_CLASSIFIER = os.path.join(SCRIPT_DIR, "emotion_classifier.joblib")


def build_dataset(data_dict):
    """Transforme un dictionnaire {emotion: [phrases]} en listes parallèles (X_text, y_labels)."""
    x_text = []
    y_labels = []
    for emotion, sentences in data_dict.items():
        for sentence in sentences:
            x_text.append(sentence)
            y_labels.append(emotion)
    return x_text, y_labels


def train_and_evaluate(
    model_path=None,
    output_classifier=OUTPUT_CLASSIFIER,
    embedder=None,
    classifier=None,
    dump_fn=None,
):
    """Entraîne le classifieur d'émotions, le sauvegarde et l'évalue sur TEST."""
    resolved_model = model_path if model_path is not None else resolve_model_path()
    if embedder is None:
        if SentenceTransformer is None:
            raise RuntimeError("La dépendance 'sentence-transformers' est requise.")
        print(f"1. Chargement du modèle d'embeddings ({resolved_model})...")
        embedder = SentenceTransformer(resolved_model)

    if classifier is None:
        if LogisticRegression is None:
            raise RuntimeError("La dépendance 'scikit-learn' est requise.")
        classifier = LogisticRegression(max_iter=1000, random_state=42)

    if dump_fn is None:
        if dump is None:
            raise RuntimeError("La dépendance 'joblib' est requise.")
        dump_fn = dump

    # Préparation des données d'entraînement
    X_train_text, y_train = build_dataset(TRAIN)

    print(f"2. Vectorisation de {len(X_train_text)} phrases d'entraînement...")
    t0 = time.time()
    X_train_embeddings = embedder.encode(X_train_text, show_progress_bar=True)
    print(f"   Vectorisation terminée en {time.time() - t0:.2f} s.")

    print("3. Entraînement du classifieur (LogisticRegression)...")
    classifier.fit(X_train_embeddings, y_train)

    # Sauvegarde du classifieur
    dump_fn(classifier, output_classifier)
    print(f"   Classifieur sauvegardé dans '{output_classifier}'.")

    # Évaluation sur le jeu TEST
    print("\n4. Évaluation sur le jeu TEST...")
    X_test_text, y_test_true = build_dataset(TEST)

    t0 = time.time()
    X_test_embeddings = embedder.encode(X_test_text)
    y_test_pred = classifier.predict(X_test_embeddings)
    inference_time = (time.time() - t0) / max(1, len(X_test_text))

    if accuracy_score is not None:
        acc = accuracy_score(y_test_true, y_test_pred)
    else:
        acc = sum(1 for a, b in zip(y_test_true, y_test_pred) if a == b) / max(
            1, len(y_test_true)
        )

    print("\n--- RÉSULTATS PISTE A ---")
    print(f"Précision (Accuracy) : {acc * 100:.1f} %")
    print(f"Temps moyen par phrase : {inference_time * 1000:.1f} ms")
    if classification_report is not None:
        print("\nRapport détaillé par émotion :")
        print(
            classification_report(
                y_test_true,
                y_test_pred,
                labels=EMOTIONS,
                target_names=EMOTIONS,
            )
        )
    return classifier, acc, inference_time


def main():
    train_and_evaluate()


if __name__ == "__main__":
    main()
