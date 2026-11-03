# Rapport d'Audit Technique et Corrections Hors Matériel (`robot/docs/AUDIT.md`)

Date : 2026-11-04
Coordination : GPT-6 Astra — Exécution finale : Gemini 4 Argon

---

## 1. Contexte, État Git et Déroulement de l'Audit

- **Commit d'origine (`main`)** : `b3c1986d52a3054ef46c71fdc105b2f2de6c82a3`
- **Branche locale créée** : `work/audit-corrections`
- **État à la clôture de l’audit, avant publication autorisée** : aucun commit, aucun push, aucune PR, aucun accès au robot ni téléchargement de modèle n'ont été effectués.
- **Déroulement des vagues d'exécution** :
  - *Vague 1* : commandes terminal refusées par la politique de permissions de la session.
  - *Vague 2* : édition directe des fichiers autorisée sans commandes terminal ; statut des sous-missions : `emotion` = `SUCCESS`, `stereo` = `SUCCESS`, `teensy` = `ERROR` fournisseur final en fin de vague mais sources `.ino` et tests `tests/test_teensy.py` intégralement revus et exécutés par le coordinateur Astra.
- **Périmètre exclu** : aucun développement de nouvelles fonctionnalités (protocole série ASCII Pi ↔ Teensy, watchdog et IMU MPU6050 exclus), aucune refonte du streaming vidéo, aucune modification de `robot/pi/stereo_calib.npz`.

---

## 2. Volet Émotions, Serveur TCP et Clients PC

### Fichiers concernés
- [`pc/config.py`](../../pc/config.py)
- [`pc/text_client.py`](../../pc/text_client.py)
- [`pc/voice_client.py`](../../pc/voice_client.py)
- [`robot/pi/emotion_server.py`](../../robot/pi/emotion_server.py)
- [`robot/pi/emotions.py`](../../robot/pi/emotions.py)
- [`robot/pi/predict_emotion.py`](../../robot/pi/predict_emotion.py)
- [`robot/pi/train_emotion_model.py`](../../robot/pi/train_emotion_model.py)
- [`tests/test_emotion.py`](../../tests/test_emotion.py)

### Défauts corrigés
1. **Contrat TCP par lignes UTF-8 (`\n`), fragmentation et coalescence** :
   - Avant correction, un unique `recv(1024)` supposait qu'une requête ou une réponse correspondait exactement à un appel `recv()`, ce qui échouait en cas de fragmentation TCP (notamment au milieu d'un caractère UTF-8 multi-octets) ou de coalescence de plusieurs lignes.
   - Dans [`robot/pi/emotion_server.py`](../../robot/pi/emotion_server.py) (`handle_client`, `_process_line`) et [`pc/text_client.py`](../../pc/text_client.py) (`send_emotion_request`), les échanges sont désormais découpés sur `\n` avec tampon d'octets persistant. Le contrat JSON (`{"texte", "emotion", "confiance", "ms"}`) est intégralement préservé.
2. **Alignement IP/Port, client vocal PC et fermeture des sockets** :
   - [`pc/config.py`](../../pc/config.py) expose `PI_IP` (`192.168.1.28` par défaut, surchargeable via `SPOT_PI_IP`) et `PORT` (`5005`, surchargeable via `SPOT_PI_PORT`).
   - [`pc/voice_client.py`](../../pc/voice_client.py) utilise désormais `PI_IP` et `PORT` depuis `config.py`, délègue l'envoi/réception TCP à `send_emotion_request` et garantit la fermeture du socket dans un bloc `finally:`.
   - *Constat documentaire important* : la version versionnée dans `pc/voice_client.py` repose sur `SpeechRecognition` (`recognizer.recognize_google(..., language="fr-FR")`, dépendante d'Internet), et **non sur Vosk** (la version Vosk est décrite dans le journal, mais absente de cette copie).
3. **Modèle multilingue et résolution des chemins indépendante du `cwd`** :
   - [`robot/pi/emotion_server.py`](../../robot/pi/emotion_server.py), [`robot/pi/predict_emotion.py`](../../robot/pi/predict_emotion.py) et [`robot/pi/train_emotion_model.py`](../../robot/pi/train_emotion_model.py) utilisent tous `DEFAULT_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"` et recherchent `model_minilm` ainsi que `emotion_classifier.joblib` successivement dans `robot/pi/`, `robot/` et la racine du dépôt.
4. **Isolation des imports matériels et ML** :
   - Les scripts de prédiction, d'entraînement et de réseau démarrent sous une fonction principale. L'import de `emotions.py` essaie encore d'ouvrir le GPIO si gpiozero est disponible ; le mode sans gpiozero est accepté pour les tests hors matériel. Aucun GPIO réel n'a été utilisé pendant ces tests.

---

## 3. Volet Teensy 4.0 — Sécurité PCA9685 et Servos DS3218MG

### Fichiers concernés
- [`robot/teensy/test_servo/test_servo.ino`](../../robot/teensy/test_servo/test_servo.ino)
- [`robot/teensy/set_all_90/set_all_90.ino`](../../robot/teensy/set_all_90/set_all_90.ino)
- [`robot/teensy/walk_demo/walk_demo.ino`](../../robot/teensy/walk_demo/walk_demo.ino)
- [`robot/teensy/stop_servos/stop_servos.ino`](../../robot/teensy/stop_servos/stop_servos.ino)
- [`tests/test_teensy.py`](../../tests/test_teensy.py)

### Défauts corrigés
1. **Verrouillage immédiat de `OE` (`D2`, actif à l'état bas) à `HIGH` dès l'entrée dans `setup()`** :
   - Sur la baseline initiale, la toute première opération ne pré-positionnait pas `digitalWrite(OE_PIN, HIGH)` avant `pinMode(OE_PIN, OUTPUT)` et activait `OE = LOW` avant d'avoir éteint les 16 canaux PWM (la baseline échoue dès la première assertion `g_events[0] == digitalWrite(2, HIGH)` du harnais C++).
   - Les 4 sketchs exécutent désormais en tête de `setup()` :
     ```cpp
     digitalWrite(OE_PIN, HIGH);
     pinMode(OE_PIN, OUTPUT);
     digitalWrite(OE_PIN, HIGH);
     ```
2. **Contrôle de `pwm.begin()`, remise à `FULL_OFF` (`4096`) des 16 canaux et gestion des erreurs I2C** :
   - D'après le code source officiel de la bibliothèque Adafruit ([`Adafruit_PWMServoDriver.cpp`](https://github.com/adafruit/Adafruit-PWM-Servo-Driver-Library/blob/master/Adafruit_PWMServoDriver.cpp), vérifié par le coordinateur) :
     - `pwm.begin()` retourne un `bool` indiquant le succès de l'initialisation I2C/reset.
     - `pwm.setPWM(ch, 0, 4096)` écrit le bit `4096` (`FULL_OFF`, bit 4 de `LEDn_OFF_H`) pour couper complètement la sortie du canal `ch`, et retourne `0` en cas de succès ou `1` en cas d'échec d'écriture.
   - Dans `test_servo.ino`, `set_all_90.ino` et `walk_demo.ino`, si `!pwm.begin()` ou si `pwm.setPWM(ch, 0, 4096) != 0` sur l'un des 16 canaux (`0..15`), `setup()` s'arrête immédiatement en laissant `OE` à `HIGH` et `pwmReady = false` (`loop()` reste alors inactif).
3. **Démarrage progressif par paliers de 500 ms et bornage strict** :
   - Dans `set_all_90.ino` et `walk_demo.ino`, `OE` n'est abaissé à `LOW` qu'après extinction complète des 16 canaux, puis chacun des 12 canaux mappés (`0, 1, 2, 4, 5, 6, 8, 9, 10, 12, 13, 14`) est amené à 90° séquentiellement avec `delay(500)` entre deux servos pour limiter les appels de courant simultanés, sans garantie sur le courant de pointe réel.
   - `setServoAngle` rejette tout canal `>= 16` et applique `constrain` sur l'angle (`[0, 180]` ou `[SAFETY_MIN=85, SAFETY_MAX=95]` dans `walk_demo.ino`) ainsi que sur la largeur d'impulsion `[US_MIN=500, US_MAX=2500]` et `stepDelayMs >= 0`.
4. **Avertissement sur les firmwares binaires existants** :
   - Tout binaire `.hex` / `.elf` compilé antérieurement sur la Pi est **périmé** : il est impératif de **recompiler les sketchs `.ino` avec `arduino-cli`** avant tout téléversement sur la Teensy 4.0.

---

## 4. Volet Vision et Profondeur Stéréo (Corrections Minimales)

### Fichiers concernés
- [`robot/pi/capture_calibration.py`](../../robot/pi/capture_calibration.py)
- [`robot/pi/calibrate_stereo.py`](../../robot/pi/calibrate_stereo.py)
- [`robot/pi/test_depth.py`](../../robot/pi/test_depth.py)
- [`tests/test_stereo_pipeline.py`](../../tests/test_stereo_pipeline.py)

*(Les fichiers `stream_server.py`, `stream_dual.py`, `test_cam.py`, `test_stereo.py` et `stereo_calib.npz` sont conservés inchangés à leur état baseline.)*

### Défauts corrigés
1. **Persistance du compteur de prises et vérification de `cv2.imwrite` (`robot/pi/capture_calibration.py`)** :
   - Avant correction, `pair_count = 0` réinitialisait la numérotation à chaque exécution, écrasant `left_01.jpg` / `right_01.jpg` lors d'une reprise de capture pour accumuler 12–15 paires, et la valeur de retour de `cv2.imwrite` n'était pas vérifiée.
   - [`get_existing_pair_count`](../../robot/pi/capture_calibration.py) détecte désormais le plus grand indice numérique existant dans `SAVE_DIR` (ancré sur `SCRIPT_DIR`), et [`save_stereo_pair`](../../robot/pi/capture_calibration.py) vérifie le succès des deux appels `cv2.imwrite`, supprimant tout fichier partiel en cas d'échec.
2. **Appariement par identifiant, robustesse aux paires vides/illisibles et chemins stables (`robot/pi/calibrate_stereo.py`)** :
   - Avant correction, `zip(sorted(glob("calib_images/left_*.jpg")), sorted(glob("calib_images/right_*.jpg")))` décalait toutes les paires en présence d'un fichier orphelin, triait lexicographiquement (`left_10` avant `left_2`), plantait dans `cv2.cvtColor` si `cv2.imread` retournait `None` ou dans `cv2.calibrateCamera` si aucune paire valide n'était trouvée, et écrivait dans `"pi/stereo_calib.npz"` (dépendant du `cwd`).
   - [`match_image_pairs`](../../robot/pi/calibrate_stereo.py) apparie explicitement `left_<id>.jpg` et `right_<id>.jpg` par identifiant commun avec tri numérique. [`main`](../../robot/pi/calibrate_stereo.py) ignore les images illisibles ou de tailles incohérentes, quitte proprement (`sys.exit(1)`) si moins de `MIN_PAIRS_REQUIRED` paires sont disponibles avant `cv2.calibrateCamera`, conserve l'algorithme et le filtrage existants sans modification, et ancre `CALIB_DIR`, `CALIB_FILE` et `RECTIFIED_FILE` sur `SCRIPT_DIR`.
3. **Chemin de calibration relatif au script et fermeture des caméras en `finally` (`robot/pi/test_depth.py`)** :
   - Avant correction, `np.load("pi/stereo_calib.npz")` échouait hors du répertoire parent de `pi/`, et `cam_left.stop()` / `cam_right.stop()` n'étaient pas protégés par un bloc `try...finally`.
   - [`robot/pi/test_depth.py`](../../robot/pi/test_depth.py) utilise désormais `CALIB_FILE = os.path.join(SCRIPT_DIR, "stereo_calib.npz")` avec `with np.load(calib_file) as calib:`, et garantit la fermeture des deux caméras dans `finally:` via `_stop_camera`.

---

## 5. Vérifications Effectuées et Limites

### Résultats des suites de tests hors matériel
1. **`tests/test_emotion.py`** : **12 tests unitaires passés** (exécutés et validés par le coordinateur Astra).
2. **`tests/test_teensy.py`** : **1 test harnais C++ compilé et exécuté sous MSVC (`cl`) passé** par le coordinateur Astra (vérification de l'ordre `OE = HIGH` en première instruction, extinction `4096` des 16 canaux avant `OE = LOW`, paliers de 500 ms sur les 12 servos, maintien de `OE = HIGH` sur échec `pwm.begin()` ou `pwm.setPWM`, bornage des angles et canaux ; la baseline échouait dès la première action `OE HIGH`).
3. **`tests/test_stereo_pipeline.py`** : **5 tests unitaires passés par Astra** (ciblant le compteur persistant et le rollback `imwrite` de `capture_calibration.py`, l'appariement par identifiant et la tolérance aux paires vides/illisibles de `calibrate_stereo.py`, ainsi que le chemin relatif au script et le `finally` caméra de `test_depth.py`, avec faux modules `cv2`/`picamera2` et `TemporaryDirectory(dir=Path(__file__).resolve().parent)`). **Non exécutés par l'exécutant Argon**, puis exécutés par Astra après intégration.

### Limites explicites
- Aucune validation sur matériel réel (Raspberry Pi 5, Teensy 4.0, PCA9685, servos DS3218MG, HC-SR04, buzzer, caméras OV5647) n'a été réalisée durant cet audit.
- Les poids `model_minilm/` et les schémas `docs/schema_*.png` ne sont pas présents dans le dépôt.
- Le fichier `robot/pi/stereo_calib.npz` existant a été conservé tel quel ; la capture de ≥ 12–15 paires validées sur le robot reste nécessaire pour stabiliser la baseline stéréo autour de 50 mm.

## 6. Vérification finale du 2026-11-04

- **18 tests réussis, aucun ignoré**, via `python -m unittest discover -s tests -v` dans un terminal développeur MSVC. NumPy est utilisé ; OpenCV, les caméras, les modèles ML, le micro et les entrées/sorties Arduino sont simulés. Les avertissements scikit-learn sur les classes non prédites proviennent du faux classifieur utilisé par le test.
- Le harnais C++ compile les sources réelles avec des interfaces simulées. Il ne remplace ni la compilation Teensy avec ses bibliothèques installées, ni un essai électrique.
- Régressions reproduites sur la version d'origine : le serveur lève `UnicodeDecodeError` quand un caractère accentué arrive en deux fragments TCP ; le harnais C++ échoue sur l'initialisation OE. Les versions corrigées passent les tests correspondants.
- `git diff --check` et analyse syntaxique de tous les fichiers Python réussis. Les modèles, la calibration `.npz` et les binaires embarqués versionnés n'ont pas été modifiés.
- Dernière mission Argon `stereo-final` : `SUCCESS`, modèle annoncé `gemini-4-argon-high`. Processus de délégation terminé. À la clôture de l’audit, avant publication autorisée, les changements étaient locaux, non commités, sans push ni PR.

### Utilisation de cette copie

Les clients PC et le serveur doivent être mis à jour ensemble : chaque phrase est désormais terminée par un saut de ligne. L'ancienne version vocale ne l'envoyait pas.
Les nouvelles captures sont enregistrées dans `robot/pi/calib_images/`. Les captures historiques dans un autre dossier ne sont pas déplacées automatiquement ; conserver leurs originaux et les reprendre explicitement avant une nouvelle calibration. La calibration actuelle reste à valider sur le robot.
Pour le client PC, vérifier `pc/config.py` ou définir `SPOT_PI_IP` ; aucune adresse actuelle du robot n'a été confirmée.
