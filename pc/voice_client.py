import json
import socket
import speech_recognition as sr

# Adresse IP de ta Raspberry Pi 5
PI_IP = "172.20.10.2"
PORT = 5005

recognizer = sr.Recognizer()
recognizer.energy_threshold = 300  # Sensibilité du micro
recognizer.dynamic_energy_threshold = True

print(f"Connexion au serveur Spot Micro ({PI_IP}:{PORT})...")
try:
  client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  client_socket.connect((PI_IP, PORT))
  print(" Connecté à la Raspberry Pi 5 !\n")
except Exception as e:
  print(f" Impossible de se connecter au Pi : {e}")
  exit(1)

print("=== INTERACTION VOCALE SPOT MICRO ===")
print("Parle dans ton micro. Appuie sur Ctrl+C pour quitter.\n")

try:
  with sr.Microphone() as source:
    recognizer.adjust_for_ambient_noise(source, duration=1)

    while True:
      print(" Écoute en cours... Parle maintenant !")
      try:
        audio = recognizer.listen(source, timeout=5, phrase_time_limit=8)
        print(" Traitement de la voix...")

        # Reconnaissance vocale en Français
        text = recognizer.recognize_google(audio, language="fr-FR")
        print(f' Vous : "{text}"')

        # Envoi au Pi via Socket
        client_socket.sendall(text.encode("utf-8"))

        # Réception de la réponse JSON du Pi
        data = client_socket.recv(1024)
        if data:
          res = json.loads(data.decode("utf-8"))
          print(
              f" Spot Micro: [{res['emotion'].upper()}] ({res['confiance']}%"
              f" - {res['ms']} ms)\n"
          )

      except sr.WaitTimeoutError:
        pass
      except sr.UnknownValueError:
        print(" Pas compris, répète s'il te plaît...\n")
      except sr.RequestError as e:
        print(f" Erreur service vocal : {e}\n")

except KeyboardInterrupt:
  print("\nFermeture de l'interaction vocale.")
finally:
  client_socket.close()