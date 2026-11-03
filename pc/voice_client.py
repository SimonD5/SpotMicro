import json
import socket
import sys

try:
  import speech_recognition as sr
except ImportError:
  sr = None

try:
  from .config import PI_IP, PORT
except ImportError:
  from config import PI_IP, PORT

try:
  from .text_client import send_emotion_request
except ImportError:
  from text_client import send_emotion_request


def main(host=PI_IP, port=PORT, recognizer=None, mic_factory=None, socket_factory=socket.socket):
  if sr is None and (recognizer is None or mic_factory is None):
    raise RuntimeError(
        "La dépendance 'SpeechRecognition' est requise pour utiliser le client vocal."
    )

  if recognizer is None:
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 300  # Sensibilité du micro
    recognizer.dynamic_energy_threshold = True

  if mic_factory is None:
    mic_factory = sr.Microphone

  wait_timeout_err = getattr(sr, "WaitTimeoutError", TimeoutError)
  unknown_value_err = getattr(sr, "UnknownValueError", ValueError)
  request_err = getattr(sr, "RequestError", RuntimeError)

  print(f"Connexion au serveur Spot Micro ({host}:{port})...")
  client_socket = None
  buffer = b""

  try:
    try:
      client_socket = socket_factory(socket.AF_INET, socket.SOCK_STREAM)
      client_socket.connect((host, port))
      print(" Connecté à la Raspberry Pi 5 !\n")
    except Exception as e:
      print(f" Impossible de se connecter au Pi : {e}")
      return 1

    print("=== INTERACTION VOCALE SPOT MICRO ===")
    print("Parle dans ton micro. Appuie sur Ctrl+C pour quitter.\n")

    with mic_factory() as source:
      recognizer.adjust_for_ambient_noise(source, duration=1)

      while True:
        print(" Écoute en cours... Parle maintenant !")
        try:
          audio = recognizer.listen(source, timeout=5, phrase_time_limit=8)
          print(" Traitement de la voix...")

          # Reconnaissance vocale en Français
          text = recognizer.recognize_google(audio, language="fr-FR")
          if not text or not text.strip():
            continue
          print(f' Vous : "{text}"')

          # Envoi au Pi via Socket (contrat TCP : 1 ligne UTF-8 terminée par \n)
          res, buffer = send_emotion_request(client_socket, text, buffer)
          if res is None:
            print(" Serveur déconnecté.")
            break

          print(
              f" Spot Micro: [{res['emotion'].upper()}] ({res['confiance']}%"
              f" - {res['ms']} ms)\n"
          )

        except wait_timeout_err:
          pass
        except unknown_value_err:
          print(" Pas compris, répète s'il te plaît...\n")
        except request_err as e:
          print(f" Erreur service vocal : {e}\n")

  except KeyboardInterrupt:
    print("\nFermeture de l'interaction vocale.")
  finally:
    if client_socket is not None:
      try:
        client_socket.close()
      except OSError:
        pass
  return 0


if __name__ == "__main__":
  sys.exit(main())
