import json
import socket
import sys

try:
    from .config import PI_IP, PORT
except ImportError:
    from config import PI_IP, PORT


def send_emotion_request(client_socket, text, buffer=b"", recv_size=1024):
    """Envoie une phrase UTF-8 terminée par '\\n' et lit une réponse JSON terminée par '\\n'.

    Gère la fragmentation TCP, les caractères UTF-8 multi-octets coupés entre deux recv()
    et la coalescence de lignes dans le tampon de réception.
    Retourne (dict_reponse, buffer_restant) ou (None, buffer_restant) si le serveur se déconnecte.
    """
    clean_text = " ".join(str(text).splitlines()).strip()
    if not clean_text:
        return None, buffer

    client_socket.sendall((clean_text + "\n").encode("utf-8"))

    while b"\n" not in buffer:
        chunk = client_socket.recv(recv_size)
        if not chunk:
            if buffer.strip():
                raw_line = buffer
                buffer = b""
                return json.loads(raw_line.decode("utf-8")), buffer
            return None, buffer
        buffer += chunk

    raw_line, buffer = buffer.split(b"\n", 1)
    return json.loads(raw_line.decode("utf-8")), buffer


def main(host=PI_IP, port=PORT, input_fn=input, socket_factory=socket.socket):
    print(f"Connexion au serveur d'émotions sur la Pi ({host}:{port})...")
    client_socket = None
    buffer = b""

    try:
        client_socket = socket_factory(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((host, port))
        print("Connecté avec succès !\n")
        print("Tape une phrase à envoyer à la Pi (ou 'quitter' pour sortir) :\n")

        while True:
            try:
                text = input_fn("PC > ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not text or text.lower() in ["quitter", "exit"]:
                break

            response, buffer = send_emotion_request(client_socket, text, buffer)
            if response is None:
                print("Serveur déconnecté.")
                break

            print(
                f"➜ Pi a répondu : Émotion [{response['emotion'].upper()}] "
                f"({response['confiance']}%) calculée en {response['ms']} ms\n"
            )

    except ConnectionRefusedError:
        print(
            f"Erreur : Impossible de se connecter à {host}:{port}. Assure-toi que le serveur tourne sur la Pi."
        )
    except Exception as e:
        print(f"Erreur : {e}")
    finally:
        if client_socket is not None:
            try:
                client_socket.close()
            except OSError:
                pass
        print("Socket fermé.")


if __name__ == "__main__":
    main()
