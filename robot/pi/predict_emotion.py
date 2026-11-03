import os
import sys

try:
    from joblib import load
except ImportError:
    load = None

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

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


def resolve_classifier_path(script_dir=SCRIPT_DIR):
    """Recherche emotion_classifier.joblib dans pi/ puis dans les dossiers parents."""
    for folder in _candidate_dirs(script_dir):
        candidate = os.path.join(folder, "emotion_classifier.joblib")
        if os.path.exists(candidate):
            return candidate
    return os.path.join(script_dir, "emotion_classifier.joblib")


MODEL_PATH = resolve_model_path()
CLASSIFIER_PATH = resolve_classifier_path()


def predict_text(text, embedder, classifier):
    """Prédit l'émotion et la confiance (%) pour une phrase donnée."""
    vec = embedder.encode([text])
    emotion = str(classifier.predict(vec)[0])
    probas = classifier.predict_proba(vec)[0]
    confidence = float(max(probas) * 100)
    return emotion, confidence


def main(embedder=None, classifier=None, input_fn=input):
    if embedder is None or classifier is None:
        if SentenceTransformer is None or load is None:
            raise RuntimeError(
                "Les dépendances 'sentence-transformers' et 'joblib' sont requises."
            )
        print("Chargement du modèle d'émotions...")
        embedder = SentenceTransformer(resolve_model_path())
        classifier = load(resolve_classifier_path())

    print("\n--- TESTEUR D'ÉMOTIONS ---")
    print("Touche 'Entrée' sur une ligne vide ou tape 'quitter' pour sortir.\n")

    while True:
        try:
            text = input_fn("Ta phrase > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not text or text.lower() in ["quitter", "exit"]:
            break

        # Calcul de l'embedding et prédiction
        emotion, confidence = predict_text(text, embedder, classifier)
        print(
            f"➜ Émotion détectée : [{emotion.upper()}] (confiance : {confidence:.1f}%)\n"
        )


if __name__ == "__main__":
    main()
