import json
import os
import socket
import time

try:
    from joblib import load
except ImportError:
    load = None

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

try:
    from .emotions import play_emotion
except ImportError:
    from emotions import play_emotion

DEFAULT_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

# Récupération dynamique des chemins (dossier pi/, parent et racine du projet)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))  # /home/simon/spot-micro/pi
BASE_DIR = os.path.dirname(SCRIPT_DIR)                   # /home/simon/spot-micro
ROOT_DIR = os.path.dirname(BASE_DIR)


def _candidate_dirs(script_dir=SCRIPT_DIR):
    """Retourne la liste ordonnée des dossiers candidats (sans doublons)."""
    base_dir = os.path.dirname(script_dir)
    root_dir = os.path.dirname(base_dir)
    dirs = []
    for folder in (script_dir, base_dir, root_dir):
        if folder and folder not in dirs:
            dirs.append(folder)
    return dirs


def resolve_classifier_path(script_dir=SCRIPT_DIR):
    """Recherche emotion_classifier.joblib dans pi/ puis dans les dossiers parents."""
    for folder in _candidate_dirs(script_dir):
        candidate = os.path.join(folder, "emotion_classifier.joblib")
        if os.path.exists(candidate):
            return candidate
    return os.path.join(script_dir, "emotion_classifier.joblib")


def resolve_model_path(script_dir=SCRIPT_DIR, default_model=DEFAULT_MODEL_NAME):
    """Recherche model_minilm dans pi/ puis dans les parents, sinon fallback Hugging Face multilingue."""
    for folder in _candidate_dirs(script_dir):
        candidate = os.path.join(folder, "model_minilm")
        if os.path.exists(candidate):
            return candidate
    return default_model


CLASSIFIER_PATH = resolve_classifier_path()
MODEL_PATH = resolve_model_path()

HOST = "0.0.0.0"  # Écoute sur toutes les interfaces réseau
PORT = 5005       # Port d'écoute


def load_models(model_path=None, classifier_path=None):
    """Charge le modèle d'embeddings et le classifieur en mémoire."""
    if SentenceTransformer is None or load is None:
        raise RuntimeError(
            "Les dépendances 'sentence-transformers' et 'joblib' sont requises pour charger le modèle."
        )
    resolved_model = model_path if model_path is not None else resolve_model_path()
    resolved_classifier = (
        classifier_path if classifier_path is not None else resolve_classifier_path()
    )
    print(f"1. Chargement du classifieur ({resolved_classifier})...")
    t0 = time.time()
    embedder = SentenceTransformer(resolved_model)
    classifier = load(resolved_classifier)
    print(f"   Modèle prêt en {time.time() - t0:.2f} s.")
    return embedder, classifier


def predict_response(text, embedder, classifier):
    """Exécute l'inférence sur une phrase et retourne (dict_reponse, elapsed_ms, confidence)."""
    t_start = time.time()
    vec = embedder.encode([text])
    emotion = str(classifier.predict(vec)[0])
    confidence = float(max(classifier.predict_proba(vec)[0]) * 100)
    elapsed_ms = (time.time() - t_start) * 1000

    response = {
        "texte": text,
        "emotion": emotion,
        "confiance": round(confidence, 1),
        "ms": round(elapsed_ms, 1),
    }
    return response, elapsed_ms, confidence


def _process_line(raw_line, client_socket, embedder, classifier, buzzer_fn=play_emotion):
    """Traite une ligne brute UTF-8, joue l'émotion et envoie une ligne JSON de réponse."""
    text = raw_line.decode("utf-8", errors="replace").strip()
    if not text:
        return None

    response, elapsed_ms, confidence = predict_response(text, embedder, classifier)
    emotion = response["emotion"]

    print(f"  ➜ Reçu : '{text}'")
    print(f"  ➜ Émotion : [{emotion.upper()}] ({confidence:.1f}%) en {elapsed_ms:.1f} ms")

    # Réaction sonore R2-D2 via le buzzer (choisi une des 5 variations au hasard)
    if buzzer_fn is not None:
        try:
            buzzer_fn(emotion)
        except Exception as exc:
            print(f"  [!] Erreur buzzer ignorée : {exc}")
    print()

    # Réponse JSON envoyée au client (contrat TCP : 1 ligne JSON par requête)
    payload = (json.dumps(response) + "\n").encode("utf-8")
    client_socket.sendall(payload)
    return response


def handle_client(
    client_socket,
    client_address,
    embedder,
    classifier,
    buzzer_fn=play_emotion,
    recv_size=1024,
):
    """Gère un client TCP avec découpage par lignes UTF-8 (fragmentation et coalescence)."""
    print(f"[+] Connexion reçue de {client_address[0]}:{client_address[1]}")
    buffer = b""
    try:
        while True:
            data = client_socket.recv(recv_size)
            if not data:
                if buffer.strip():
                    try:
                        _process_line(
                            buffer, client_socket, embedder, classifier, buzzer_fn
                        )
                    except (ConnectionError, OSError):
                        pass
                    buffer = b""
                print(f"[-] Client {client_address[0]} déconnecté.\n")
                break

            buffer += data
            while b"\n" in buffer:
                raw_line, buffer = buffer.split(b"\n", 1)
                _process_line(
                    raw_line, client_socket, embedder, classifier, buzzer_fn
                )
    except (ConnectionError, OSError) as exc:
        print(f"[-] Connexion interrompue avec {client_address[0]} ({exc}).\n")
    finally:
        try:
            client_socket.close()
        except OSError:
            pass


def run_server(
    host=HOST,
    port=PORT,
    embedder=None,
    classifier=None,
    buzzer_fn=play_emotion,
    max_clients=None,
):
    """Démarre le serveur TCP et accepte les connexions entrantes."""
    if embedder is None or classifier is None:
        embedder, classifier = load_models()

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server_socket.bind((host, port))
        server_socket.listen(5)

        print(f"\n2. Serveur TCP démarré sur le port {port}.")
        print("   En attente de connexions du PC...\n")

        clients_served = 0
        while max_clients is None or clients_served < max_clients:
            client_socket, client_address = server_socket.accept()
            handle_client(
                client_socket,
                client_address,
                embedder,
                classifier,
                buzzer_fn=buzzer_fn,
            )
            clients_served += 1
    except KeyboardInterrupt:
        print("\nArrêt du serveur.")
    finally:
        try:
            server_socket.close()
        except OSError:
            pass


def main():
    run_server()


if __name__ == "__main__":
    main()
