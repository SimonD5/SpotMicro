import json
import socket
import sys

from config import PI_IP, PORT

print(f"Connexion au serveur d'émotions sur la Pi ({PI_IP}:{PORT})...")

try:
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((PI_IP, PORT))
    print("Connecté avec succès !\n")
    print("Tape une phrase à envoyer à la Pi (ou 'quitter' pour sortir) :\n")

    while True:
        text = input("PC > ").strip()
        if not text or text.lower() in ["quitter", "exit"]:
            break

        # Envoi de la phrase à la Pi
        client_socket.sendall((text + "\n").encode("utf-8"))

        # Réception de la réponse de la Pi
        data = client_socket.recv(1024)
        if not data:
            print("Serveur déconnecté.")
            break

        response = json.loads(data.decode("utf-8"))
        print(f"➜ Pi a répondu : Émotion [{response['emotion'].upper()}] "
              f"({response['confiance']}%) calculée en {response['ms']} ms\n")

except ConnectionRefusedError:
    print(f"Erreur : Impossible de se connecter à {PI_IP}:{PORT}. Assure-toi que le serveur tourne sur la Pi.")
except Exception as e:
    print(f"Erreur : {e}")
finally:
    client_socket.close()
    print("Socket fermé.")