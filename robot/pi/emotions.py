import random
import sys
import time
try:
  from gpiozero import PWMOutputDevice
except ImportError:
  PWMOutputDevice = None

# Pin GPIO connecté au buzzer passif (GPIO 18 = Broche physique 12)
BUZZER_PIN = 18

# Réduction du volume via le Duty Cycle (Rapport cyclique)
# 0.50 = Volume maximal (50%)
# 0.05 = Volume très doux (5% - ideal pour préserver les oreilles)
# 0.02 = Volume extrêmement bas (2%)
DEFAULT_VOLUME = 0.05

try:
  buzzer = PWMOutputDevice(BUZZER_PIN) if PWMOutputDevice is not None else None
except Exception:
  buzzer = None  # Mode simulation si exécuté hors de la Pi


def play_tone(frequency, duration_ms, volume=DEFAULT_VOLUME):
  """Joue une fréquence (Hz) pendant une durée (ms) à un volume ajusté."""
  if frequency <= 0 or buzzer is None:
    if buzzer:
      buzzer.value = 0
    time.sleep(duration_ms / 1000.0)
    return

  buzzer.frequency = int(frequency)
  buzzer.value = volume  # Duty cycle réduit = volume bas
  time.sleep(duration_ms / 1000.0)
  buzzer.value = 0


def glissando(
    start_freq, end_freq, duration_ms, steps=30, volume=DEFAULT_VOLUME
):
  """Effet de glissement de fréquence fluide (style R2-D2)."""
  step_duration = (duration_ms / 1000.0) / steps
  freq_step = (end_freq - start_freq) / steps

  for i in range(steps):
    current_freq = start_freq + (i * freq_step)
    if buzzer:
      buzzer.frequency = int(current_freq)
      buzzer.value = volume
    time.sleep(step_duration)

  if buzzer:
    buzzer.value = 0


def play_emotion(emotion, variation="random", volume=DEFAULT_VOLUME):
  """Exécute la séquence sonore associée à l'émotion.

  35 variations uniques au total (5 par émotion : a, b, c, d, e).
  Si variation='random', choisit aléatoirement une déclinaison parmi les 5.
  """
  emotion = str(emotion).lower().strip()

  valid_emotions = [
      "content",
      "triste",
      "curieux",
      "surpris",
      "colere",
      "peur",
      "neutre",
  ]
  mapping = {
      "1": "content",
      "2": "triste",
      "3": "curieux",
      "4": "surpris",
      "5": "colere",
      "6": "peur",
      "7": "neutre",
  }

  # Si l'émotion passée est déjà un nom valide exact ou un chiffre (ex: "neutre", "triste", "1")
  if emotion in valid_emotions or emotion in mapping:
    target_emotion = mapping.get(emotion, emotion)
    var = variation
  else:
    # Sinon c'est une combinaison type "4c", "content_b", "7e"
    var = variation
    if len(emotion) > 1 and emotion[-1] in ["a", "b", "c", "d", "e"]:
      var = emotion[-1]
      emotion = emotion[:-1].strip("_ ")
    target_emotion = mapping.get(emotion, emotion)

  # Sélection de la variation
  if var == "random" or str(var).lower() not in ["a", "b", "c", "d", "e"]:
    var = random.choice(["a", "b", "c", "d", "e"])
  else:
    var = str(var).lower()

  emotion = target_emotion

  print(
      f"--> [{emotion.upper()}] | Var: [{var.upper()}] | Vol:"
      f" {volume * 100:.1f}%"
  )

  # ==========================================
  # 1. CONTENT (5 variations joyeuses)
  # ==========================================
  if emotion == "content":
    if var == "b":
      # Arpège étendu + sifflement final
      play_tone(523, 110, volume)
      play_tone(659, 110, volume)
      play_tone(784, 110, volume)
      play_tone(1047, 140, volume)
      time.sleep(0.05)
      glissando(1047, 1800, 280, steps=25, volume=volume)
      time.sleep(0.03)
      play_tone(1975, 180, volume)
    elif var == "c":
      # Chant mélodique R2-D2 en 5 phrases
      glissando(700, 1200, 200, steps=20, volume=volume)
      time.sleep(0.04)
      play_tone(1400, 120, volume)
      play_tone(1600, 120, volume)
      time.sleep(0.04)
      glissando(1600, 2200, 250, steps=25, volume=volume)
    elif var == "d":
      # Fanfare expressive
      glissando(500, 1000, 180, steps=20, volume=volume)
      play_tone(1200, 100, volume)
      play_tone(1500, 100, volume)
      glissando(1500, 2400, 300, steps=30, volume=volume)
      play_tone(2400, 150, volume)
    elif var == "e":
      # Double trille ascendant
      glissando(800, 1300, 150, steps=15, volume=volume)
      time.sleep(0.03)
      glissando(1100, 1700, 150, steps=15, volume=volume)
      time.sleep(0.03)
      glissando(1500, 2300, 220, steps=20, volume=volume)
    else:  # 'a'
      # Mélodie sautillante classique
      play_tone(600, 120, volume)
      glissando(800, 1400, 220, steps=20, volume=volume)
      time.sleep(0.04)
      play_tone(1500, 150, volume)
      play_tone(1800, 200, volume)

  # ==========================================
  # 2. TRISTE (5 soupirs graves et lents)
  # ==========================================
  elif emotion == "triste":
    if var == "b":
      # Plainte hésitante en 3 étapes
      play_tone(550, 280, volume)
      time.sleep(0.10)
      play_tone(420, 320, volume)
      time.sleep(0.12)
      glissando(350, 160, 650, steps=40, volume=volume)
    elif var == "c":
      # Descente vibrante très grave
      glissando(800, 400, 350, steps=25, volume=volume)
      time.sleep(0.06)
      for freq in [320, 280, 240]:
        play_tone(freq, 120, volume)
        time.sleep(0.04)
      glissando(200, 120, 500, steps=30, volume=volume)
    elif var == "d":
      # Chute chromatique lente
      glissando(650, 450, 300, steps=20, volume=volume)
      time.sleep(0.08)
      glissando(450, 280, 400, steps=25, volume=volume)
      time.sleep(0.10)
      glissando(280, 110, 600, steps=35, volume=volume)
    elif var == "e":
      # Soupir étouffé
      play_tone(400, 250, volume)
      glissando(400, 250, 350, steps=20, volume=volume)
      time.sleep(0.08)
      glissando(250, 130, 550, steps=30, volume=volume)
    else:  # 'a'
      # Long soupir progressif
      glissando(750, 350, 500, steps=35, volume=volume)
      time.sleep(0.10)
      glissando(320, 140, 750, steps=45, volume=volume)

  # ==========================================
  # 3. CURIEUX (5 hausses interrogatives)
  # ==========================================
  elif emotion == "curieux":
    if var == "b":
      # Escalier progressif (3 paliers)
      play_tone(450, 160, volume)
      time.sleep(0.06)
      glissando(500, 850, 280, steps=25, volume=volume)
      time.sleep(0.05)
      glissando(850, 1400, 250, steps=20, volume=volume)
    elif var == "c":
      # Oscillation hésitante puis envolée
      glissando(600, 800, 150, steps=15, volume=volume)
      glissando(800, 650, 150, steps=15, volume=volume)
      time.sleep(0.06)
      glissando(650, 1350, 320, steps=30, volume=volume)
    elif var == "d":
      # Questionnement suraigu court
      play_tone(700, 100, volume)
      time.sleep(0.04)
      play_tone(900, 120, volume)
      time.sleep(0.04)
      glissando(1100, 1900, 300, steps=25, volume=volume)
    elif var == "e":
      # Double impulsion ondulée
      glissando(500, 950, 220, steps=20, volume=volume)
      time.sleep(0.08)
      glissando(800, 1650, 280, steps=25, volume=volume)
    else:  # 'a'
      # Double question fluide
      play_tone(550, 140, volume)
      time.sleep(0.08)
      play_tone(680, 140, volume)
      time.sleep(0.05)
      glissando(750, 1300, 300, steps=30, volume=volume)

  # ==========================================
  # 4. SURPRIS (5 sursauts expressifs)
  # ==========================================
  elif emotion == "surpris":
    if var == "b":
      # Rebond expressif
      glissando(500, 1800, 200, steps=25, volume=volume)
      time.sleep(0.04)
      glissando(1800, 1300, 160, steps=20, volume=volume)
      time.sleep(0.03)
      play_tone(1600, 200, volume)
    elif var == "c":
      # Hoquet vocal rapide
      play_tone(800, 80, volume)
      play_tone(1600, 100, volume)
      time.sleep(0.03)
      glissando(1600, 2200, 180, steps=20, volume=volume)
      time.sleep(0.02)
      play_tone(1900, 150, volume)
    elif var == "d":
      # Sursaut en double pic
      glissando(600, 2100, 160, steps=20, volume=volume)
      time.sleep(0.03)
      glissando(1200, 2300, 180, steps=20, volume=volume)
      play_tone(1800, 140, volume)
    elif var == "e":
      # Effroi staccato
      play_tone(1200, 60, volume)
      play_tone(1700, 60, volume)
      play_tone(2200, 80, volume)
      time.sleep(0.03)
      glissando(2200, 1400, 220, steps=20, volume=volume)
    else:  # 'a'
      # Sursaut fluide (Monte rapide + 2 bips clairs)
      glissando(450, 1600, 180, steps=22, volume=volume)
      time.sleep(0.04)
      play_tone(1700, 120, volume)
      time.sleep(0.03)
      play_tone(2000, 180, volume)

  # ==========================================
  # 5. COLERE (5 grondements rudes)
  # ==========================================
  elif emotion == "colere":
    vol_c = volume * 1.5
    if var == "b":
      # Râle saccadé rapide
      for _ in range(5):
        play_tone(210, 80, vol_c)
        play_tone(130, 80, vol_c)
        time.sleep(0.03)
    elif var == "c":
      # Chute brute et saccades
      glissando(400, 150, 250, steps=20, volume=vol_c)
      time.sleep(0.04)
      for _ in range(3):
        play_tone(160, 100, vol_c)
        time.sleep(0.03)
    elif var == "d":
      # Bourdonnement bas oscillant
      for _ in range(4):
        glissando(250, 110, 120, steps=10, volume=vol_c)
        glissando(110, 250, 120, steps=10, volume=vol_c)
    elif var == "e":
      # Salve colérique descendante
      play_tone(320, 100, vol_c)
      play_tone(240, 100, vol_c)
      play_tone(180, 120, vol_c)
      time.sleep(0.04)
      for _ in range(3):
        play_tone(130, 90, vol_c)
        time.sleep(0.02)
    else:  # 'a'
      # Grondement grave en 3 salves
      for _ in range(3):
        play_tone(190, 120, vol_c)
        play_tone(120, 120, vol_c)
        time.sleep(0.05)

  # ==========================================
  # 6. PEUR (5 paniques frissonnantes)
  # ==========================================
  elif emotion == "peur":
    if var == "b":
      # Frisson continu et longue chute
      for _ in range(7):
        play_tone(1400, 45, volume)
        play_tone(1050, 45, volume)
      glissando(1050, 220, 400, steps=35, volume=volume)
    elif var == "c":
      # Sirène de panique montante et descendante
      glissando(800, 1600, 180, steps=20, volume=volume)
      glissando(1600, 700, 180, steps=20, volume=volume)
      glissando(700, 1800, 200, steps=20, volume=volume)
      glissando(1800, 200, 350, steps=30, volume=volume)
    elif var == "d":
      # Bégaiement aigu paniqué
      for _ in range(8):
        play_tone(1600, 35, volume)
        time.sleep(0.02)
      glissando(1600, 300, 300, steps=25, volume=volume)
    elif var == "e":
      # Alerte stridente ondulante
      glissando(1200, 1900, 150, steps=15, volume=volume)
      for _ in range(4):
        play_tone(1900, 40, volume)
        play_tone(1500, 40, volume)
      glissando(1500, 180, 420, steps=35, volume=volume)
    else:  # 'a'
      # Trémolo aigu fluide puis effondrement
      for _ in range(5):
        play_tone(1500, 50, volume)
        play_tone(1150, 50, volume)
      glissando(1150, 280, 350, steps=30, volume=volume)

  # ==========================================
  # 7. NEUTRE (5 confirmations douces)
  # ==========================================
  elif emotion == "neutre":
    vol_n = volume * 0.7
    if var == "b":
      # Léger sifflement d'acquittement
      glissando(500, 800, 220, steps=20, volume=vol_n)
      time.sleep(0.04)
      play_tone(800, 120, volume=vol_n)
    elif var == "c":
      # Triple bip amical "boop-ba-beep"
      play_tone(500, 90, volume=vol_n)
      time.sleep(0.04)
      play_tone(650, 90, volume=vol_n)
      time.sleep(0.04)
      play_tone(850, 140, volume=vol_n)
    elif var == "d":
      # Tonalité d'attente "bip-boop"
      play_tone(750, 100, volume=vol_n)
      time.sleep(0.05)
      play_tone(520, 140, volume=vol_n)
    elif var == "e":
      # Chime discret ascendant
      glissando(450, 700, 180, steps=15, volume=vol_n)
      time.sleep(0.03)
      play_tone(900, 110, volume=vol_n)
    else:  # 'a'
      # Double bip classique "boop-beep"
      play_tone(550, 110, volume=vol_n)
      time.sleep(0.06)
      play_tone(800, 160, volume=vol_n)

  else:
    print(f"Émotion inconnue : '{emotion}'")


if __name__ == "__main__":
  emo_arg = sys.argv[1] if len(sys.argv) > 1 else "content"
  var_arg = sys.argv[2] if len(sys.argv) > 2 else "random"

  vol_arg = DEFAULT_VOLUME
  if len(sys.argv) > 3:
    try:
      vol_arg = float(sys.argv[3])
    except ValueError:
      pass
  elif len(sys.argv) > 2:
    try:
      vol_arg = float(sys.argv[2])
      var_arg = "random"
    except ValueError:
      pass

  play_emotion(emo_arg, variation=var_arg, volume=vol_arg)