# Spot Micro R2-D2 — journal de bord et feuille de route

> **Ce fichier est la source de vérité du projet.** Il récapitule la config, les décisions et ce qui a été fait, pour qu'une personne ou un agent IA puisse reprendre le travail sans tout redemander.
> **Règle : après chaque étape terminée, mettre à jour la section *Statut*, la section *Journal* et, si besoin, la section *Configuration*.**

Dernière mise à jour : 2026-11-04

### Copie GitHub et journal du robot

Ce dépôt GitHub range le code embarqué dans `robot/pi/` et `robot/teensy/`.
Les chemins `pi/` et `teensy/` du journal ci-dessous décrivent l'installation
historique sur la Pi. Depuis la racine de cette copie, utiliser par exemple
`python robot/pi/emotion_server.py` ; ne pas recopier les anciennes commandes
sans adapter leur chemin.

Le dossier `pc/` contient une copie versionnée des clients. Le fichier vocal
présent ici utilise `SpeechRecognition` et son service Google, avec accès
Internet, alors que le journal décrit une version Vosk locale. La version Vosk
du dossier personnel n'est pas fournie. Les validations matérielles consignées
dans ce journal ne constituent donc pas une validation de cette copie du code.
Le dossier personnel PC reste hors du périmètre de travail.

Les poids `model_minilm/` ne sont pas fournis : il faut retrouver le modèle
multilingue utilisé pour entraîner le classifieur avant de valider l'inférence.
Les schémas annoncés dans `docs/` ne sont pas présents non plus ; les tableaux
de câblage restent disponibles dans ce document.

---

## 1. Vue d'ensemble

Robot quadrupède de type **Spot Micro** (12 servos, à confirmer), autonome et expressif :

- **S'exprime** avec des bruits style **R2-D2** (buzzer passif) selon son « émotion ». *C'est la première fonction développée.*
- **Entend** (micro du PC au départ, micro sur la Pi à terme), comprend ce qui est dit et **adapte son humeur**.
- **Voit** avec 2 caméras (stéréo → profondeur) et **suit une personne**.
- **Marche** grâce à une politique entraînée par **renforcement learning (RL) sur PC**.
- Se **développe à distance en wifi** (SSH, VS Code Remote, Raspberry Pi Connect).
- Inspiration : le robot **Microduck** (Pollen Robotics / Hugging Face), pour son fonctionnement et ses émotions.

**Ordre de développement : émotions (buzzer) d'abord, caméras ensuite.**

Répartition : **Pi 5 = émotions / audio / vision / réseau / décisions haut niveau**, **Teensy 4.0 = temps réel / servos / IMU / ultrason / sécurité**, **PC = entraînement RL, micro et calculs lourds au début** (à terme, le robot doit fonctionner **sans PC**).

---

## 2. Statut rapide

Légende : `[x]` fait, `[~]` en cours, `[ ]` à faire, `[?]` à confirmer.

- [x] Choix de l'architecture (Raspberry Pi 5 + Teensy 4.0 + PC)
- [x] Raspberry Pi 5 (8 Go) acquise
- [x] Caméra n°1 Whadda WPI408 acquise et fonctionnelle (`CAM0`)
- [x] Caméra n°2 OV5647 acquise, branchée et détectée (`CAM1`)
- [x] Raspberry Pi Connect activé
- [x] OS écrit sur la microSD, utilisateur `simon`, SSH activé (hôte à retrouver, voir §5)
- [x] **Premier démarrage de la Pi** (chargeur de téléphone USB-C), connexion SSH réussie le 2026-10-27
- [x] Phase 0 : base système et dev à distance (SSH, mise à jour, outils, `enable-linger`, clé SSH et VS Code Remote-SSH faits ; dépôt Git `spot-micro` en place sur la Pi ; `[?]` vérif `vcgencmd get_throttled` non notée dans le journal)
- [x] Réseau Wi-Fi de la Pi (NetworkManager) : `Livebox-63C0` / `Danielandjacobs` (priorité 20, principal), hotspot iPhone priorité 10 (secours)
- [x] **Phase 1 : buzzer passif et émotions R2-D2 (sur la Pi), terminée le 2026-11-02**
  - [x] 1a : banque sonore `pi/emotions.py` : **35 déclinaisons R2-D2** (5 variations `a` à `e` pour chacune des 7 émotions), buzzer passif sur GPIO 18 (broche 12) + GND
  - [x] 1b : volume réglé par rapport cyclique PWM (**5 %** par défaut, 50 % était trop fort et strident)
  - [x] 1c : branchée sur `pi/emotion_server.py` (déclinaison tirée au hasard à chaque phrase)
- [x] Phase 2 : parole via le micro du PC → humeur (terminée le 2026-10-28) ; **boucle complète micro PC → Pi → buzzer validée le 2026-11-02**
  - [x] 2a : modèle Piste A validé (embeddings `paraphrase-multilingual-MiniLM-L12-v2` + `LogisticRegression`, précision 88.6 % sur 35 phrases de test, 15.9 ms/phrase sur Pi 5) ; piste B (petit LLM) non testée
  - [x] 2b : serveur TCP `pi/emotion_server.py` sur la Pi (port 5005, modèle gardé en RAM, 50-100 ms au total)
  - [x] 2c : client vocal PC `voice_client.py` (Vosk `vosk-model-small-fr-0.22` + `sounddevice`), configuration IP centralisée dans `config.py` (côté PC)
- [x] Phase 3 : caméra n°1 (terminée le 2026-10-31) : WPI408 / OV5647 fonctionnelle sur `CAM0`, tests CLI et Python OK, streaming Web Flask (port 8080) + détection d'objets **YOLOv8s**
- [x] **Phase 4 : alimentation et électronique du robot, validée en fonctionnement le 2026-11-03** (convertisseur 10 A à 5,55 V pour les 12 servos, LM2596 n°1 à 5,0 V pour la Pi, schémas en §5) ; `[?]` mesure du courant réel au wattmètre non notée
- [~] **Phase 5 : Teensy (servos, IMU, ultrason) + liaison Pi ↔ Teensy (en cours : tout est validé sauf l'IMU et le protocole série, 2026-11-03)**
  - [x] 5a : Teensy 4.0 branchée en USB sur la Pi, vue sur `/dev/ttyACM0` (`ID 16c0:0483`)
  - [x] 5b : chaîne de compilation en ligne de commande sur la Pi : `arduino-cli` + `teensy_loader_cli` + règles udev PJRC
  - [x] 5c : premier firmware `teensy/i2c_scanner/i2c_scanner.ino` compilé et téléversé depuis la Pi
  - [x] 5d : scan I2C réussi : **PCA9685 détecté à `0x40`** (et `0x70`, adresse All-Call)
  - [x] 5e : **test du HC-SR04** : `teensy/test_hcsr04/test_hcsr04.ino` fonctionnel (TRIG D3, ECHO D4 avec diviseur 1 kΩ / 2,2 kΩ)
  - [x] 5f : **pilotage des servos par le PCA9685**, validé le 2026-11-03 :
    - broche **OE sur D2** (`LOW` = sorties activées, `HIGH` = sorties coupées)
    - test de mouvement lent d'un servo, canal 0 (`teensy/test_servo/test_servo.ino`)
    - **cartographie des 12 canaux** : AV-G 0, 1, 2 | AV-D 4, 5, 6 | AR-G 8, 9, 10 | AR-D 12, 13, 14 (détail en §5)
    - démarrage séquentiel des 12 servos à 90°, 500 ms par servo (`teensy/set_all_90/set_all_90.ino`)
    - micro-marche diagonale bridée à ±5° (`teensy/walk_demo/walk_demo.ino`)
    - mise en sécurité, coupure des sorties PWM (`teensy/stop_servos/stop_servos.ino`)
  - [ ] 5g : **IMU MPU6050** : seul composant restant à tester (I2C pin 18 / 19, 3,3 V, adresse `0x68`)
  - [ ] 5h : protocole série ASCII Pi ↔ Teensy sur `/dev/ttyACM0` avec watchdog
- [~] Phase 6 : 2e caméra et profondeur stéréo
  - [x] 6a : outil de dimensionnement `stereo_planner.py` (PC) terminé le 2026-10-31
  - [x] 6b : HFOV réel de la WPI408 mesuré sur la Pi (**55.4°**, et non 130°). Support imprimé : entraxe $B = 50\text{ mm}$, caméras parallèles (0°), plage utile théorique 0.48 m à 3.0 m à 640×480
  - [x] 6c : 2e caméra branchée (`CAM1`), serveur de streaming dual `stream_dual.py`, scripts `test_stereo.py` et `capture_calibration.py` (score de validation géométrique en temps réel)
  - [~] 6d : calibration stéréo et filtrage automatique (`calibrate_stereo.py`) : damier asymétrique $8 \times 7$ coins (9×8 cases, 22 mm), filtrage per-image atteint (RMS individuel < 0.85 px, RMS stéréo ≈ 1.1 px). **Étape courante** : accumuler ≥ 12 paires `[VALIDE]` pour stabiliser la baseline autour de 50 mm
  - [x] 6e : script de calcul de la carte de disparité / profondeur `test_depth.py` (OpenCV `StereoSGBM`), à valider une fois la calibration stabilisée
- [ ] Phase 7 : détection et suivi d'une personne
- [ ] Phase 8 : locomotion par RL
- [ ] Phase 9 : sécurité
- [ ] Phase 10 : intégration, micro sur la Pi, autonomie sans PC
- [x] Audit logiciel hors matériel (2026-11-04) : émotions/TCP, sécurité Teensy (`OE` / `FULL_OFF` / paliers 500 ms), scripts stéréo et suites `tests/` (`robot/docs/AUDIT.md`) ; non testé sur matériel réel

---

## 3. Matériel

| Élément | Détail | Statut |
|---|---|---|
| Ordinateur embarqué | **Raspberry Pi 5, 8 Go** | possédé |
| Microcontrôleur | **Teensy 4.0** (Cortex-M7 600 MHz, **3,3 V, entrées non tolérantes 5 V**) | possédé, branché en USB sur la Pi (`/dev/ttyACM0`) |
| Buzzer | **passif**, branché sur le **GPIO 18 (broche 12)** de la **Pi** + GND (broche 14), pas sur le Teensy | possédé et fonctionnel |
| Sortie audio (haut-parleur) | **non utilisée**, seul le buzzer s'exprime | abandonnée |
| Micro | **micro du PC** au départ, micro sur la Pi à terme (USB ou I2S) | micro du PC utilisé ; micro de la Pi à acheter plus tard |
| IMU | **MPU6050** (module GY-521) sur le **Teensy**, I2C | en attente de livraison (broches à souder) |
| Contrôleur de servos | **PCA9685** (16 canaux, I2C `0x40`, **OE sur D2**) | possédé, détecté et fonctionnel |
| Servos | **DS3218MG** × 12 : numérique, engrenages métal, **4,8 à 6,8 V**, couple 19 kg·cm à 5 V, courant à l'arrêt (rotor bloqué) 1,8 à 2,6 A, impulsions 500-2500 µs (neutre 1500 µs) | possédés, **12 canaux configurés et testés** (2026-11-03) |
| Batterie | **LiPo 3S** (11,1 V nominal, 12,6 V pleine charge) | possédée |
| Convertisseurs | **1 gros convertisseur buck « 10 A »** (DZS Elec, 4,5-30 V → 0,8-30 V, vendu 12 A, **compté 10 A par prudence**, protections thermique et court-circuit) ; **2 × LM2596** (2 A nominal, 3 A max avec dissipateur). **Pas d'achat d'autre convertisseur prévu** (budget) | possédés |
| Ultrason | **HC-SR04** (TRIG D3, ECHO D4 via diviseur 1 kΩ / 2,2 kΩ), dans la tête, pour la sécurité (au-dessus ou en dessous des caméras) | possédé, **testé et fonctionnel** (2026-11-03) |
| Caméra n°1 (gauche) | **Whadda WPI408** : capteur OV5647 5 Mpx, **HFOV mesuré 55.4°** (la fiche annonce 130°, c'est faux), mise au point manuelle, 2 LED infrarouges, nappe 15 broches, branchée sur `CAM0` | possédée et fonctionnelle |
| Caméra n°2 (droite) | **OV5647 5 Mpx**, branchée sur `CAM1` | possédée et fonctionnelle |
| Câbles caméra | adaptateur **22 broches (Pi 5) → 15 broches (caméra)** × 2 | possédés |
| Support stéréo | support imprimé en 3D : entraxe $B = 50\text{ mm}$, inclinaison 0° (parallèle) | installé |
| PC | machine d'entraînement RL, micro, développement | possédé |

---

## 4. Architecture

```
      wifi (NetworkManager : Livebox-63C0 / Danielandjacobs prio 20 / hotspot iPhone prio 10)
   ┌────────────┐ <──────────────────────────────> ┌──────────────────┐
   │     PC     │   SSH / VS Code / voix (TCP 5005) │  Raspberry Pi 5  │
   │ micro (au  │   Web Stream MJPEG (HTTP 8080)    │ buzzer (GPIO),   │
   │ début), RL,│                                   │ caméras (YOLOv8, │
   │ calculs    │                                   │ StereoSGBM),     │
   │ lourds     │                                   │ micro (à terme), │
   │            │                                   │ décisions        │
   └────────────┘                                   └────────┬─────────┘
                                                             │ USB série
                                                             │ (/dev/ttyACM0)
                                                    ┌────────┴─────────┐
                                                    │    Teensy 4.0    │
                                                    │ servos (PCA9685),│
                                                    │ IMU MPU6050,     │
                                                    │ ultrason,        │
                                                    │ sécurité         │
                                                    └──────────────────┘
```

### Architecture logicielle actuelle (Pi 5)
1. **`pi/emotion_server.py`** (fait) : serveur TCP en arrière-plan sur le port **5005**. Reçoit des lignes de texte UTF-8 envoyées par le PC (puis par le micro local en phase 10) et répond en JSON : `{"emotion": ..., "confiance": ..., "ms": ...}`.
2. **`pi/emotion_classifier.joblib` + `pi/model_minilm/`** (fait) : classifieur et modèle d'embeddings, chargés **une seule fois en RAM** au démarrage du serveur (~16 ms par phrase).
3. **`pi/stream_server.py`** (fait, phase 3) : serveur Web Flask sur le port **8080**. Capture la caméra `CAM0` via `picamera2`, exécute **YOLOv8s** (classes `person` 0, `cat` 15, `dog` 16, `cell phone` 67, `conf=0.15`), régule la boucle à ~10 FPS (`time.sleep(0.03)`) et diffuse en MJPEG.
4. **`pi/stream_dual.py`** (fait, phase 6) : serveur Web Flask de vérification dual-caméra sur le port **8080** (à lancer à la place de `stream_server.py`, même port), avec grilles de niveau horizontales pour contrôler l'alignement physique.
5. **`pi/capture_calibration.py`** (fait, phase 6) : capture de paires stéréo avec score de tolérance géométrique en temps réel (`MAX_PAIR_DISPARITY_STD`) ; les paires sont marquées `[VALIDE]` ou rejetées.
6. **`pi/calibrate_stereo.py`** (fait, phase 6) : calibration et rectification stéréo avec filtre per-image (RMS < 1.5 px) pour éliminer les clichés flous ou trop inclinés ; écrit `pi/stereo_calib.npz`.
7. **`pi/test_depth.py`** (fait, phase 6) : cartes de disparité et de profondeur avec OpenCV `StereoSGBM`.
8. **`pi/emotions.py`** (fait, phase 1) : générateur audio R2-D2 PWM pour buzzer passif (GPIO 18), **35 déclinaisons** (5 par émotion), volume par rapport cyclique (5 % par défaut), appelé par `pi/emotion_server.py` via `play_emotion()`.
9. **`teensy/i2c_scanner/i2c_scanner.ino`** (fait, phase 5) : firmware C++ compilé par `arduino-cli`, téléversé par `teensy_loader_cli`, scanne le bus I2C (SDA 18, SCL 19) et confirme le PCA9685 à `0x40`.
10. **Liaison série USB `/dev/ttyACM0`** (à faire, phase 5, étape 5f) : protocole ASCII, état émotionnel et commandes de déplacement vers le Teensy 4.0 ; le Teensy a le dernier mot sur la sécurité.

Règles d'architecture :
1. **La boucle de marche (politique RL + asservissement des servos) tourne sur le robot** (Teensy, ou Pi), jamais dépendante du wifi ni du PC.
2. Le wifi et le PC servent au développement, au streaming et à des calculs optionnels. Si le wifi coupe, le robot doit rester debout ou s'asseoir.
3. **Le Teensy a le dernier mot sur la sécurité** : arrêt si l'ultrason détecte un obstacle proche, ou s'il ne reçoit plus d'ordre du Pi pendant un délai fixé (watchdog).
4. **Source audio interchangeable** : le code de reconnaissance vocale lit un flux « micro » abstrait, qui vient du PC au début et du micro local de la Pi à terme, sans changer le reste.
5. Le Teensy ne gère **pas** le buzzer : les émotions sonores sont jouées par la Pi.

---

## 5. Alimentation et électronique

### Schémas de câblage (2026-11-01)
Deux schémas dessinés, version image à ranger dans `docs/` : **`docs/schema_alimentation.png`** et **`docs/schema_signaux.png`**.

![Schéma d'alimentation](docs/schema_alimentation.png)

![Schéma des signaux et capteurs](docs/schema_signaux.png)

Les mêmes informations en texte (pour un agent qui ne voit pas les images) sont dans l'arbre d'alimentation, le tableau des tensions et le tableau de brochage ci-dessous.

### Arbre d'alimentation (décision du 2026-11-01 : un seul gros convertisseur)
```
LiPo 3S (9 à 12,6 V)  ── fusible 10 A ── interrupteur ── rail +
   │
   ├─► [gros convertisseur 10 A, réglé à 5,5 V] ─► les 12 servos (fils rouges directs, pas via le PCA9685)
   │         + condensateur 470 à 2200 µF en sortie, démarrage des servos un par un
   │
   ├─► [LM2596 n°1, réglé à 5,1 V] ─► Raspberry Pi 5 (pin 2 = 5 V, pin 6 = GND)
   │                                    ├─ USB ─► Teensy 4.0 (5 V + données, /dev/ttyACM0)
   │                                    │            └─ broche 3,3 V ─► PCA9685 (VCC) + MPU6050
   │                                    ├─ GPIO 18 (pin 12) + GND (pin 14) ─► buzzer passif
   │                                    └─ pin 4 (5 V) ─► HC-SR04, environ 15 mA
   │
   ├─► [LM2596 n°2 : en réserve, jamais en parallèle avec le n°1]
   └─► diviseur 33 kΩ / 10 kΩ ─► Teensy A0 (mesure de la tension batterie)

Toutes les masses (GND) sont reliées entre elles.
```

### Rappel : tension de chaque convertisseur et ce qu'on y branche
| Source | Tension à régler (au multimètre, **sans charge**) | Courant | À brancher dessus | À ne **pas** brancher |
|---|---|---|---|---|
| **LiPo 3S** (après fusible 10 A et interrupteur) | 9 à 12,6 V (11,1 V nominal), **jamais sous 3,5 V par élément** | selon charge, fusible 10 A | entrée du gros convertisseur, entrée du LM2596 n°1, diviseur de mesure batterie | rien de sensible directement (Pi, Teensy, capteurs) |
| **Gros convertisseur 10 A** | **5,5 V** (plage servos 4,8 à 6,8 V ; 6,0 V seulement si le couple manque ; **jamais > 6,8 V**) | 10 A max. Estimation (non mesurée) : 4 à 6 A debout, 8 à 12 A en pointe | **fils rouges des 12 servos DS3218MG** + condensateur 470 à 2200 µF | Pi, Teensy, PCA9685 (VCC), capteurs |
| **LM2596 n°1** | **5,1 V** (compense la chute dans les fils) | 3 A max (la Pi 5 en charge peut dépasser 2 A) | **Raspberry Pi 5** (pin 2 et pin 6). Via la Pi : Teensy (USB), HC-SR04 (pin 4), buzzer, caméras | servos |
| **LM2596 n°2** | en réserve (secours pour la Pi) | 3 A max | rien pour l'instant | **ne jamais le mettre en parallèle** avec le n°1 |
| **3,3 V du Teensy** (régulateur interne, alimenté par l'USB de la Pi) | 3,3 V, non réglable | faible (quelques dizaines de mA) | **PCA9685 VCC**, **MPU6050 VCC** | servos, 5 V |
| **5 V de la Pi** (pin 4) | 5 V | environ 15 mA | **HC-SR04 VCC** | entrées du Teensy (3,3 V seulement) |
| **Diviseur batterie** | 12,6 V → environ 2,93 V sur A0 (33 kΩ en haut, 10 kΩ en bas ; tension batterie = tension lue × 4,3) | négligeable | **Teensy A0** | autre chose que A0 |

Points d'attention : le **V+ du PCA9685 reste non connecté** (les fils rouges des servos vont directement sur le bornier du 10 A) ; **ECHO du HC-SR04 passe par un diviseur 1 kΩ / 2,2 kΩ** avant D4 (environ 3,4 V sur D4) ; toutes les masses sont communes.

### Brochage retenu (2026-11-01, à reprendre tel quel dans le firmware)
| Signal | Origine | Destination |
|---|---|---|
| 5,1 V (LM2596 n°1) | sortie du LM2596 | Pi pin 2 (5 V) et pin 6 (GND) |
| Buzzer passif | Pi pin 12 (GPIO 18), pin 14 (GND) | buzzer + / − (100 Ω en série conseillé) |
| HC-SR04 VCC | Pi pin 4 (5 V) | capteur ; GND au GND commun |
| TRIG | Teensy D3 | HC-SR04 TRIG |
| ECHO | HC-SR04 ECHO → 1 kΩ → Teensy D4 (2,2 kΩ de D4 vers GND, soudé : environ 3,4 V) | |
| Tension batterie | rail + → 33 kΩ → Teensy A0 (10 kΩ de A0 vers GND) | 12,6 V → environ 2,93 V ; batterie = tension lue × 4,3 |
| I2C | Teensy pin 18 (SDA), pin 19 (SCL), 3,3 V, GND | PCA9685 (`0x40`) et MPU6050 (`0x68`, AD0 au GND) |
| Coupure servos | Teensy D2 | PCA9685 OE, **actif à l'état bas** : `LOW` = sorties activées, `HIGH` = toutes les sorties servos coupées (validé le 2026-11-03) |
| Servos | PCA9685 canaux 0-2 AV-G, 4-6 AV-D, 8-10 AR-G, 12-14 AR-D (voir « Cartographie des 12 servos ») | signal + GND seulement ; rouges sur le bornier du 10 A |
| Caméras | CAM0 = WPI408, CAM1 = OV5647 | Pi 5 |
| Pi ↔ Teensy | câble USB (5 V + données) | **décision 2026-11-02 : on garde l'USB** (pas de VIN ni d'UART) |

Brochage **validé en fonctionnement le 2026-11-03** pour D2 (OE), D3 (TRIG), D4 (ECHO), I2C 18 / 19 ; **A0 (tension batterie) et le MPU6050 restent à tester**.

### Cartographie des 12 servos (PCA9685, validée le 2026-11-03)
Un groupe de 4 canaux = une patte. Dans chaque groupe : **canal 0 = extrémité de la patte, canal 1 = milieu, canal 2 = épaule**, le canal 3 du groupe est **libre**. Gauche et droite sont vues **de dessus, dans le sens de marche du robot**.
| Patte | Extrémité (genou, « pied ») | Milieu (cuisse) | Épaule | Libre |
|---|---|---|---|---|
| Avant gauche (AV-G) | CH 0 | CH 1 | CH 2 | CH 3 |
| Avant droite (AV-D) | CH 4 | CH 5 | CH 6 | CH 7 |
| Arrière gauche (AR-G) | CH 8 | CH 9 | CH 10 | CH 11 |
| Arrière droite (AR-D) | CH 12 | CH 13 | CH 14 | CH 15 |
Libellés de l'ancienne version du README : extrémité = « Pied », milieu = « Genou », épaule = « Épaule ». Même convention, noms différents : à l'extrémité de la patte se trouve l'articulation du genou. Pour l'URDF et le RL, garder cette table comme référence.

### Conversions de tension : ce qui est nécessaire et ce qui ne l'est pas
- **5 V → 3,3 V pour le Teensy : aucun convertisseur à ajouter.** Le Teensy 4.0 a son régulateur 3,3 V intégré. Il peut être alimenté en 5 V par le câble USB de la Pi. Sa broche **3,3 V** sert ensuite à alimenter les petits modules 3,3 V (MPU6050, côté logique du PCA9685).
- **PCA9685** : alimenter sa broche **VCC à 3,3 V** (pas 5 V), car ses résistances de rappel I2C sont reliées à VCC et un VCC à 5 V enverrait du 5 V sur le bus I2C du Teensy. Le **V+** du module reste **non connecté** : les fils rouges des servos vont directement sur le bornier du gros convertisseur (voir règle de câblage 2). Le signal de commande des servos sortira en 3,3 V, ce qui est normalement accepté par les servos (**à tester sur un servo avant de tout brancher**).
- **MPU6050** : module GY-521 alimenté en 3,3 V, I2C du Teensy (**broches SDA 18 / SCL 19** de `Wire`). Même bus que le PCA9685, adresses différentes (0x68 et 0x40 par défaut).
- **HC-SR04 / HC-SR05** : alimentés en **5 V**. **TRIG** (sortie du Teensy, 3,3 V) est en général accepté tel quel. **ECHO** sort en **5 V** et **le Teensy 4.0 n'est pas tolérant 5 V** : mettre un **diviseur de tension** (ECHO → 1 kΩ → point milieu vers le Teensy → 2,2 kΩ → GND, ce qui donne environ 3,4 V avec un ECHO à 5 V, un peu plus si le 5 V monte à 5,1 V : marge faible sous la limite du Teensy, voir §10 ; 2 × 1 kΩ en série à la place du 2,2 kΩ donneraient 3,33 V), ou utiliser un capteur 3,3 V (HC-SR04P, etc.).
- **Servos DS3218MG** : plage **4,8 à 6,8 V**. **Décision (2026-11-01)** : les 12 servos sur **un seul convertisseur de 10 A réglé à 5,5 V** (moins de courant de pointe, couple largement suffisant pour un robot d'environ 2 kg ; monter à 6,0 V seulement si le couple manque, **ne jamais dépasser 6,8 V**). Courant à l'arrêt **1,8 à 2,6 A par servo** : 12 servos bloqués = **22 à 31 A** théoriques, bien au-delà des 10 A. La consommation réelle est **à mesurer** (wattmètre XT60 sur la batterie) ; estimation **non mesurée** : 4 à 6 A debout, 8 à 12 A en pointe. Conditions de réussite : **ne jamais bloquer un servo**, limiter vitesse et accélération dans le code, démarrer les servos un par un, condensateur en sortie. Si le convertisseur coupe ou chute en marche : répartir 6 servos sur un 2e convertisseur (à acheter alors).
- **Gros convertisseur (DZS, vendu 12 A, compté 10 A)** : le rendement baisse avec le courant (environ 81 % à 5 V / 10 A selon une fiche), prévoir un dissipateur et, au-delà d'environ 8 A en continu, un petit ventilateur. Les fiches se contredisent sur la **protection contre l'inversion de polarité** : fusible + connecteurs XT60 détrompés. Protections thermique et court-circuit présentes. **Deux potentiomètres bleus (103 = 10 kΩ)** : celui du haut règle la **tension**, celui du bas la **limite de courant** (CC), sans effet visible à vide. Pour les servos, **mettre la limite de courant au maximum** (tourner à fond, plusieurs tours) ; trop basse, la tension s'effondre dès que les servos tirent (sursauts, redémarrages).
- **LM2596** (2 exemplaires) : **2 A nominal, 3 A max avec dissipateur**. **Pas adapté aux servos**. Le n°1 alimente la Pi 5 (régler à 5,1 V, mesurer la consommation réelle : la Pi 5 peut dépasser 2 A en charge, vérifier avec `vcgencmd get_throttled`, `0x0` = tout va bien) ; le n°2 reste en réserve.
- **Pi 5** : alimentation officielle 5 V / 5 A. Alimentée par un convertisseur sur les broches du GPIO, elle peut signaler une alimentation insuffisante si elle ne détecte pas 5 A. **Le Teensy reste alimenté et relié par le câble USB de la Pi** (décision du 2026-11-02 ; l'alimentation par VIN + liaison série UART a été écartée : elle demanderait de couper un pad sous le Teensy 4.0, à vérifier sur la page PJRC avant tout).

### Règles de câblage
1. **Régler chaque convertisseur au multimètre avant de brancher quoi que ce soit** dessus.
2. **Servos sur leur propre alimentation**, jamais depuis la Pi. **Fils rouges des servos reliés directement à la sortie du convertisseur** (bornier ou carte de distribution), pas à travers les pistes du PCA9685 : le PCA9685 ne fournit que le **signal** et la **masse**. Un condensateur sur la sortie du convertisseur des servos (idéal 2200 µF, **minimum environ 470 µF**, 10 V minimum, polarité à respecter ; récupérable sur une vieille carte). Facultatif pour les tout premiers essais à vide, à ajouter si les servos sursautent ou si le convertisseur se coupe au démarrage.
3. **Masses communes** entre Pi, Teensy, PCA9685, capteurs et alimentation des servos.
4. **Fusible** sur la batterie, connecteurs XT60, interrupteur général.
5. **Alarme ou coupure basse tension** pour la LiPo 3S (ne pas descendre sous environ 3,5 V par élément).
6. Premier essai de chaque nouvelle alimentation **sans servos branchés**.
7. **Démarrage progressif** : ne pas activer les 12 servos d'un coup (appel de courant), les mettre en position l'un après l'autre ou lentement. Après réglage au multimètre, **couper et rallumer plusieurs fois** en mesurant la sortie, pour vérifier qu'il n'y a pas de pic de tension à l'allumage.

---

## 6. Configuration actuelle de la Pi (à compléter au fur et à mesure)

| Paramètre | Valeur |
|---|---|
| OS | Raspberry Pi OS Lite 64 bits, base Debian, noyau 6.18 `rpt-rpi-2712` (confirmé le 2026-10-27) |
| Nom d'hôte | `spot` (connexion actuelle : `ssh simon@192.168.1.28` depuis PowerShell Windows ; `ssh simon@spot.local` fonctionne selon le réseau) |
| Utilisateur | `simon` |
| SSH | activé |
| Adresse IP | `192.168.1.28` sur le Wi-Fi principal (2026-11-01). Anciennes valeurs : `10.20.30.31` (2026-10-28), `172.20.10.2` sur le hotspot iPhone (2026-10-27). Variable selon le réseau → voir §7 |
| Réseaux Wi-Fi | NetworkManager : `Livebox-63C0` / `Danielandjacobs` (priorité 20, principal) ; `netplan-wlan0-iPhone de Simon` (priorité 10, secours) |
| Serveur d'émotions | `pi/emotion_server.py`, port TCP **5005**, tourne en arrière-plan (méthode de lancement permanent `[?]` à confirmer ; services `systemd` prévus en phase 10) |
| Teensy 4.0 | branché en USB sur la Pi, port série `/dev/ttyACM0` (`ID 16c0:0483`, Teensyduino Serial) |
| Outils de flash Teensy | `arduino-cli` (dans `/usr/local/bin`) + `teensy_loader_cli` (MCU `TEENSY40`), règles udev PJRC installées |
| Buzzer | GPIO 18 (broche physique 12) + GND (broche 14), volume PWM 5 % |
| Stream Web (vision / dual) | `pi/stream_server.py` (caméra n°1 + YOLOv8s) **ou** `pi/stream_dual.py` (2 caméras, alignement), port HTTP **8080** (un seul à la fois) |
| Raspberry Pi Connect | activé le 2026-10-27 (sur Lite : accès par **shell distant**, à confirmer) |
| Alimentation du premier démarrage | chargeur de téléphone USB-C (suffisant pour démarrer, à remplacer à terme) |
| Caméras | Dual OV5647 : n°1 WPI408 sur `CAM0` (gauche), n°2 sur `CAM1` (droite), HFOV = **55.4°**, toutes deux détectées par `rpicam-hello --list-cameras` |
| Python | paquets système : `python3-picamera2`, `python3-opencv` |
| Environnement Python | `python3 -m venv --system-site-packages ~/venv`, avec `picamera2`, `opencv-python-headless`, `ultralytics`, `flask`, `scikit-learn`, `numpy` |

> Ne **jamais** écrire de mot de passe ni de clé dans ce fichier.

### Retrouver le nom d'hôte
- Carte avant le premier démarrage : sur le PC, partition `bootfs`, fichier `user-data` (images récentes) ou `firstrun.sh` (plus anciennes). **Ne pas partager ce fichier**, il peut contenir le mot de passe wifi.
- Pi démarrée : liste des appareils connectés du téléphone (hotspot), tableau de bord Raspberry Pi Connect.
- Sans nom choisi, la valeur par défaut est `raspberrypi`. La connexion est donc `ssh simon@NOM.local`.

### Installation de l'OS (pour mémoire)
1. Sur le PC, installer **Raspberry Pi Imager**.
2. Choisir : appareil **Pi 5** → *Raspberry Pi OS (other)* → **Raspberry Pi OS Lite (64-bit)** → la carte microSD (32 Go ou plus).
3. Dans la **personnalisation** : nom d'hôte, utilisateur + mot de passe, **wifi (SSID, mot de passe, pays)**, **SSH activé**.
4. Écrire la carte, la mettre dans la Pi, alimenter. Le premier démarrage prend 2 à 3 minutes.
5. Depuis le PC, sur le même réseau : `ssh simon@NOM.local`
6. `sudo apt update && sudo apt full-upgrade -y && sudo reboot`

---

## 7. Accès et workflow de développement

### Réseau (changements fréquents de partage de connexion)
- Ajouter ou changer un réseau : `sudo nmtui` ou `sudo nmcli device wifi connect "SSID" password "MOTDEPASSE"`
- Les réseaux connus sont mémorisés, la Pi se reconnecte seule.
- Priorité d'un réseau : `sudo nmcli connection modify "SSID" connection.autoconnect-priority 10`
- **Réseaux actuels** : `Livebox-63C0` / `Danielandjacobs` (priorité 20, tenté en premier), puis `netplan-wlan0-iPhone de Simon` (priorité 10, secours). IP actuelle sur le Wi-Fi principal : `192.168.1.28`.
- **Si l'IP de la Pi change** : `hostname -I` (via Raspberry Pi Connect si besoin), puis modifier `HostName` dans `C:\Users\nomis\.ssh\config` et `PI_IP` dans le `config.py` du PC.
- Voir l'IP : `hostname -I`
- **Le PC doit être sur le même réseau que la Pi** (hotspot du téléphone inclus).
- Si `NOM.local` ne marche pas sur le hotspot du téléphone : utiliser l'IP indiquée dans la liste des appareils connectés du téléphone.
- Si la Pi n'a plus aucun réseau connu : câble Ethernet, ou écran + clavier, ou refaire la carte avec le bon wifi.
- **Raspberry Pi Connect** : accès à distance quel que soit le réseau, en passant par le compte Raspberry Pi.

### Développement
- **VS Code + extension Remote-SSH** : éditer et lancer le code directement sur la Pi.
- **Git** : un dépôt unique `spot-micro` sur la Pi (`README.md`, `pi/`, `teensy/`, `docs/`, `hardware/`). Commits fréquents, un message clair par étape.
- **Code PC** : dossier `C:\Users\nomis\Documents\Spot\`, **géré par Simon hors dépôt Git** (ne pas le commiter ni le transférer depuis la Pi).
- **Clé SSH** : pour éviter de retaper le mot de passe.
- Programmer le **Teensy directement depuis la Pi** (depuis le 2026-11-02) : `arduino-cli` pour compiler (de préférence avec `--output-dir .` pour avoir le `.hex` dans le dossier du projet), `teensy_loader_cli --mcu=TEENSY40 -w -v fichier.hex` pour téléverser. Si le chargeur reste sur *Waiting for Teensy device*, appuyer sur le bouton de la Teensy. Arduino IDE + Teensyduino sur le PC reste possible.

### Arborescence du dépôt Git (sur la Pi, `/home/simon/spot-micro/`)
```
spot-micro/
├── .gitignore                    ← ignore __pycache__/, venv/, pi/model_minilm/, *.pt, *.jpg, calib_images/
├── README.md                     ← ce fichier
├── pi/                           ← code exécuté sur la Pi
│   ├── emotions_data.py          ← jeu de données TRAIN/TEST (7 émotions)
│   ├── emotions.py               ← banque de 35 sons R2-D2 PWM (5 variations x 7 émotions), volume 5 %
│   ├── hello.py                  ← script de test basique
│   ├── train_emotion_model.py    ← entraînement de la régression logistique
│   ├── predict_emotion.py        ← testeur interactif local (CLI)
│   ├── emotion_server.py         ← serveur TCP émotions, port 5005
│   ├── emotion_classifier.joblib ← classifieur entraîné
│   ├── model_minilm/             ← modèle d'embeddings local (~450 Mo, hors Git)
│   ├── test_cam.py               ← validation capture picamera2 + OpenCV
│   ├── test_stereo.py            ← capture instantanée d'une paire stéréo
│   ├── stream_server.py          ← serveur Web Flask + détection YOLOv8s (port 8080)
│   ├── stream_dual.py            ← serveur Web Flask dual-caméra avec lignes repères (port 8080)
│   ├── capture_calibration.py    ← capture stéréo avec score de tolérance géométrique
│   ├── calibrate_stereo.py       ← calibration stéréo + filtrage d'outliers per-image
│   ├── test_depth.py             ← disparité / profondeur StereoSGBM
│   └── stereo_calib.npz          ← paramètres intrinsèques et cartes de rectification (généré)
├── teensy/                       ← firmware du Teensy (servos, IMU, ultrason, sécurité)
│   ├── i2c_scanner/              ← scan du bus I2C (PCA9685 vu à 0x40)
│   ├── test_hcsr04/              ← test du HC-SR04 (TRIG D3, ECHO D4)
│   ├── test_servo/               ← balayage lent du canal 0, gestion de OE (D2)
│   ├── set_all_90/               ← calage progressif des 12 servos à 90° (500 ms par servo)
│   ├── walk_demo/                ← micro-marche diagonale bridée à ±5°
│   └── stop_servos/              ← mise en sécurité (OE → HIGH, PWM coupée)
├── docs/                         ← schémas de câblage, notes de calibration, photos
└── hardware/                     ← CAO, URDF (masses des composants à jour)
```

### Dossier du PC Windows (hors dépôt Git : `C:\Users\nomis\Documents\Spot\`)
```
Spot/
├── config.py          ← réseau : PI_IP = "192.168.1.28", PORT = 5005
├── text_client.py     ← client de test au clavier
├── voice_client.py    ← micro du PC (sounddevice) + Vosk, envoi du texte à la Pi
├── stereo_planner.py  ← plage de profondeur selon écart, inclinaisons et champ (numpy + matplotlib)
├── model_vosk/        ← modèle français Vosk (vosk-model-small-fr-0.22)
└── model_minilm/      ← copie de sauvegarde du modèle MiniLM
```

---

## 8. Feuille de route détaillée par fonction

Chaque phase a : un **objectif**, des **étapes**, et un **critère de validation**. Cocher et dater dans le *Journal* en fin de phase.

### Phase 0 — Base système et dev à distance
**Objectif** : une Pi accessible à distance, à jour, stable.
1. Premier démarrage, retrouver le nom d'hôte (§6), `ssh simon@NOM.local`.
2. `sudo apt update && sudo apt full-upgrade -y && sudo reboot`
3. Installer : `sudo apt install -y git python3-venv python3-pip htop tmux`
4. Vérifier Pi Connect et le wifi, enregistrer le hotspot du téléphone en réseau connu.
5. Remote-SSH sur VS Code, clé SSH, création du dépôt Git (arborescence du §7).
- Si des avertissements de sous-tension apparaissent (`vcgencmd get_throttled` ≠ `0x0`), changer de chargeur ou de câble.
- **Validation** : connexion SSH et Pi Connect OK, un script modifié depuis le PC se lance sur la Pi.

### Phase 1 — Buzzer passif et émotions R2-D2 (sur la Pi) [terminée le 2026-11-02]
**Objectif** : une bibliothèque d'émotions sonores jouées par la Pi.
**Réalisé (2026-11-02)** : buzzer sur GPIO 18 + GND, `pi/emotions.py` avec **35 séquences** (5 variations `a` à `e` par émotion, glissandos et arpèges), **volume par rapport cyclique PWM à 5 %** (à 50 % le son était trop fort et strident), appelé par `pi/emotion_server.py` (`play_emotion()`, déclinaison aléatoire). Correction d'un bug : l'extraction de la lettre de variation tronquait le `e` final de `neutre`, `triste` et `colere`. Dépendances système Pi 5 pour `rpi-lgpio` : `swig`, `python3-dev`, `liblgpio-dev`. Les étapes ci-dessous restent la procédure de référence.
- **Buzzer passif vs actif** : un buzzer *actif* contient son propre oscillateur et ne joue qu'**une seule note fixe** dès qu'on l'alimente ; un buzzer *passif* joue **la fréquence qu'on lui envoie**, donc des mélodies, des glissandos et des trilles. Il faut un passif pour R2-D2.
1. Brancher le buzzer passif : une broche sur un GPIO de la Pi (ex. GPIO 18), l'autre sur GND (résistance en série de quelques centaines d'ohms si le son est trop fort).
2. Jouer des notes avec **gpiozero** (`TonalBuzzer`) :
```python
from gpiozero import TonalBuzzer
from gpiozero.tones import Tone
b = TonalBuzzer(18)
b.play(Tone(frequency=880)); # ... attendre, puis b.stop()
```
3. Écrire `pi/emotions.py` : un dictionnaire émotion → séquence de (fréquence, durée), plus des glissandos (boucles qui font varier la fréquence). Liste validée le 2026-10-27 : content, triste, curieux, surpris, colere, peur, neutre (les 7 doivent avoir un son ; `neutre` = silence ou bip discret). Émotions : content (montée aiguë rapide), triste (descente lente), curieux (note montante + pause), surpris (saut aigu), en colère (graves courts), etc.
4. Exposer `jouer(emotion)` en Python, testable en SSH.
5. Le serveur TCP existe déjà (`pi/emotion_server.py`, phase 2) : y brancher `jouer(emotion)` sur l'émotion reconnue, pour qu'une phrase prononcée devant le PC déclenche le son.
- **Si le son est instable** (la PWM logicielle de gpiozero sur Pi 5 peut être irrégulière), passer au **PWM matériel** du RP1 (overlay `pwm` dans `config.txt` + bibliothèque dédiée).
- Les émotions sont des **séquences écrites à la main**, pas du machine learning.
- **Validation** : chaque émotion est reconnaissable à l'oreille et déclenchable à distance depuis le PC.

### Phase 2 — Parole via le micro du PC → humeur (terminée le 2026-10-28)
**Objectif** : transformer ce que le robot « entend » en émotion, sans micro sur la Pi pour l'instant.
1. Sur le PC : capter le micro (Python, `sounddevice`). **Fait** : `voice_client.py`.
2. Reconnaissance vocale sur le PC : **Vosk** retenu, modèle français léger `vosk-model-small-fr-0.22` (dossier `model_vosk/`).
3. Convertir le texte en humeur avec un **petit modèle qui comprend le sens** (pas seulement des mots-clés), **à faire tourner sur la Pi 5 de préférence** (8 Go de RAM, consommation à limiter). Sortie limitée à une liste fixe d'émotions. Voir « Choix du modèle » ci-dessous. **Fait** : piste A retenue.
4. **Fait** : le PC envoie le texte à la Pi par TCP (`pi/emotion_server.py`, port 5005, réponse JSON `{"emotion", "confiance", "ms"}`, 50-100 ms au total) et, depuis le 2026-11-02, le serveur **joue directement le son R2-D2** correspondant sur le buzzer (phase 1).
5. Écrire le code avec une **source audio interchangeable** (flux du PC / micro local), pour la phase 10.
- **Validation atteinte** : une phrase prononcée devant le micro du PC est transcrite, l'émotion est renvoyée par la Pi en moins de 100 ms et **le buzzer réagit instantanément** (boucle complète validée le 2026-11-02).

**Choix du modèle texte → émotion (terminé : piste A retenue, 2026-10-27)** — contraintes : tourne sur la Pi 5 (8 Go), faible consommation, comprend des phrases complexes (« mon chat est mort » → triste). Les durées et tailles du tableau étaient des **estimations** faites avant les mesures ; seule la piste A a été mesurée (voir Résultat).
| Piste | Principe | Avantages | Limites |
|---|---|---|---|
| **A. Embeddings multilingues + classifieur léger** (ex. `paraphrase-multilingual-MiniLM-L12-v2`, ~118 M de paramètres, + régression logistique) | la phrase devient un vecteur, un classifieur appris sur quelques dizaines de phrases d'exemple par émotion choisit l'émotion | léger, rapide (quelques dizaines de ms estimées), RAM < 1 Go estimée, comprend le sens | il faut écrire les phrases d'exemple ; négations et sarcasme mal gérés |
| **B. Petit LLM quantifié** (ex. Qwen2.5 0.5B ou 1.5B Instruct, llama.cpp) | prompt « réponds par un seul mot parmi : content, triste… » | aucune donnée à préparer, meilleure compréhension | plus lent (de l'ordre de 1 à 3 s estimées), plus de RAM et de CPU, donc plus de consommation |
| **C. Mots-clés** | règles écrites à la main | trivial | écarté : ne comprend pas le sens |
- **Piste recommandée** : **A en premier**, **B en repli** si A se trompe trop. Ne lancer le modèle qu'**après détection de parole** (pour ne pas charger le CPU en continu). **Décision de l'utilisateur (2026-10-27)** : tester A d'abord, puis B, garder le meilleur ; la **rapidité de réponse prime**. La Pi n'a pas d'autre charge lourde prévue (profondeur 2 caméras, parole + émotion, buzzer) : un modèle plus gros que prévu est envisageable. Méthode : le même jeu de phrases de test sert à comparer A et B (précision et temps de réponse mesurés sur la Pi).
- **Reconnaissance vocale** (transcription) : Vosk avec un petit modèle français (léger) ou whisper.cpp (plus précis, plus lourd). Au début, le micro du PC envoie le texte ou l'audio à la Pi ; développer d'abord avec du **texte tapé au clavier**. **Réalisé** : `text_client.py` (clavier), puis `voice_client.py` (micro + Vosk).
- **Résultat (2026-10-27 soir, mesuré sur la Pi 5)** : piste A, **88.6 % de précision sur les 35 phrases de test** (31/35), **15.9 ms par phrase**. Retenue pour sa rapidité et sa faible consommation. **La piste B (petit LLM) n'a pas été testée** : elle reste un repli si la précision devient insuffisante (enrichir d'abord `emotions_data.py`).

### Phase 3 — Caméra n°1 (WPI408) [terminée le 2026-10-31]
**Objectif** : image et vidéo fonctionnelles.
**Réalisé** : WPI408 reconnue sur `CAM0`, tests CLI (`rpicam-hello`, `rpicam-still`) et Python (`pi/test_cam.py`) OK, serveur de streaming Web Flask `pi/stream_server.py` (port 8080) avec détection d'objets **YOLOv8s** (voir §4 et §9). Les étapes ci-dessous restent la procédure de référence.
1. **Pi éteinte**, brancher la caméra avec le **câble adaptateur 22 → 15 broches** (si la nappe fournie est large aux deux bouts).
2. Redémarrer, tester : `rpicam-hello --list-cameras`
3. Photo : `rpicam-still -o test.jpg`, la récupérer avec `scp simon@NOM.local:test.jpg .`
4. Régler la **mise au point manuelle** (bague de l'objectif), puis la bloquer.
5. Test Python :
```python
from picamera2 import Picamera2
picam2 = Picamera2(0)
picam2.configure(picam2.create_video_configuration(main={"size": (640, 480), "format": "RGB888"}))
picam2.start()
frame = picam2.capture_array()   # tableau numpy exploitable par OpenCV
```
6. Streaming vers le PC (exemple) : sur la Pi `rpicam-vid -t 0 --inline --listen -o tcp://0.0.0.0:8888`, sur le PC `ffplay tcp://NOM.local:8888 -fflags nobuffer -flags low_delay`.
- **Si la caméra n'est pas détectée** : sens et verrouillage de la nappe, connecteur (CAM0/CAM1), `dmesg | grep -i ov5647`.
- **Validation** : image nette récupérée, flux vidéo visible sur le PC.

### Phase 4 — Alimentation et électronique du robot [validée en fonctionnement le 2026-11-03]
**Objectif** : une alimentation fiable avant de brancher les servos.
**Réalisé (2026-11-03)** : gros convertisseur 10 A réglé à 5,55 V (potentiomètre du haut = tension, celui du bas = limite de courant au maximum), LM2596 n°1 à 5,0015 V pour la Pi, câblage selon les schémas du §5, 12 servos alimentés et pilotés sans incident. `[?]` La mesure du courant réel au wattmètre n'est pas notée : à faire avant les premiers pas au sol. Les étapes ci-dessous restent la procédure de référence.
1. Régler chaque convertisseur au multimètre (§5), sans charge.
2. Régler le gros convertisseur 10 A à **5,5 V** (servos DS3218MG : 4,8 à 6,8 V ; 6,0 V seulement si le couple manque) et vérifier qu'il n'y a pas de pic à l'allumage. Alimentation de la Pi : LM2596 n°1 à 5,1 V (ou un convertisseur 5 V ≥ 5 A si la mesure montre que le LM2596 ne suffit pas).
3. Câbler fusible, interrupteur, condensateurs, masses communes (arbre du §5), fils rouges des servos directement sur les convertisseurs.
4. Mesurer la **consommation réelle** (wattmètre XT60 sur la batterie) : un servo seul, puis 3, 6 et 12, d'abord sans charge puis robot sur support. **Si ça approche 10 A, ajouter un 2e convertisseur** et répartir 6 servos par convertisseur (pas prévu à ce jour, budget).
- **Validation** : Pi alimentée par la batterie sans avertissement de sous-tension, tension des servos mesurée correcte.

### Phase 5 — Teensy : servos, IMU, ultrason + liaison Pi ↔ Teensy [en cours]
**Objectif** : un firmware qui commande les servos, lit les capteurs et parle à la Pi.
**État au 2026-11-03** : chaîne `arduino-cli` + `teensy_loader_cli` opérationnelle sur la Pi ; PCA9685 (`0x40`), HC-SR04 et **12 servos validés** (démarrage séquentiel à 90°, micro-marche à ±5°, coupure par OE sur D2). **Reste** : l'**IMU MPU6050** (étape 5g), puis le **protocole série Pi ↔ Teensy avec watchdog** (5h). Les firmwares de test sont dans `teensy/` (voir §7).
1. **PCA9685** : VCC en 3,3 V depuis le Teensy, **V+ non connecté** (fils rouges des servos directement sur le convertisseur 5,5 V). Tester **un seul servo** avec la bibliothèque PCA9685 (Adafruit), pulses 500 à 2500 µs, 50 Hz.
2. **MPU6050** : I2C (SDA 18 / SCL 19), alimenté en 3,3 V. Calibrer les offsets du gyroscope au démarrage, appliquer un **filtre complémentaire ou Madgwick** pour obtenir roll et pitch. Pas de magnétomètre : le **yaw dérive**, ce qui n'est pas gênant pour tenir l'équilibre.
3. **HC-SR04** : alimenté en 5 V, TRIG en sortie, **ECHO via diviseur 1 kΩ / 2,2 kΩ** (§5).
4. Liaison série USB avec la Pi (`/dev/ttyACM0`, `pip install pyserial`) et **protocole simple** documenté dans `docs/protocole.md` (lignes ASCII au départ : commandes Pi → Teensy, mesures IMU et distance Teensy → Pi).
5. **Watchdog** : sans message de la Pi pendant X ms, retour à un état sûr.
- **Validation** : la Pi envoie une commande de servo, le Teensy renvoie l'IMU et la distance, et il coupe tout si on débranche la Pi.

### Phase 6 — Deuxième caméra et profondeur stéréo [en cours]
**Objectif** : carte de profondeur utilisable à courte distance.
1. Choisir/acheter la 2e caméra (même modèle de préférence, voir §9) + 2e câble adaptateur. **[Fait]**
2. Brancher sur l'autre connecteur (CAM0/CAM1), vérifier `rpicam-hello --list-cameras` (2 caméras), ouvrir avec `Picamera2(0)` et `Picamera2(1)`. **[Fait]**
3. **Support rigide imprimé en 3D**, entraxe finalement retenu **$B = 50\text{ mm}$**, caméras parallèles (toute flexion fausse la calibration). **[Fait]**
4. Mesurer le champ réel de la WPI408 sur cible : $D = 40\text{ cm}$, $W = 42\text{ cm}$ ⇒ **HFOV = 55.4°**. **[Fait]**
5. Vérifier l'alignement physique avec `pi/stream_dual.py` (grilles de niveau horizontales). **[Fait]**
6. **Calibration** avec damier et OpenCV : `cv2.findChessboardCorners`, `cv2.stereoCalibrate`, `cv2.stereoRectify`. À refaire après tout changement mécanique.
   - Damier **asymétrique $8 \times 7$ coins (9×8 cases, 22 mm)** pour supprimer l'ambiguïté de rotation 180° (**[Fait]**, voir §9 et §10).
   - Score de validation géométrique en temps réel dans `pi/capture_calibration.py` : seules les paires `[VALIDE]` sont gardées (**[Fait]**).
   - Filtrage d'outliers per-image dans `pi/calibrate_stereo.py` (RMS < 1.5 px) (**[Fait]**) : RMS individuel passé de 5.0 px à **0.681 px** (gauche) et **0.842 px** (droite), RMS stéréo **1.102 px** (obtenu avec 6 paires seulement).
   - **Étape en cours** : capturer **≥ 12 à 15 paires validées** d'angles variés (écran plat, inclinaison < 25°, distances 40 cm à 1,2 m) avec `python pi/capture_calibration.py`, puis lancer `python pi/calibrate_stereo.py` : la baseline calculée doit se fixer autour de **50 mm** réels.
7. Profondeur : `cv2.StereoSGBM_create` sur les images rectifiées (`pi/test_depth.py`, **[Fait]**), test à 0,5 / 1 / 1,5 / 2 m avec une distance mesurée au mètre. **[À faire après calibration]**
8. Si le calcul est trop lourd sur la Pi : réduire la résolution (320×240 à 640×480) ou déporter sur le PC.
- Plage théorique (calcul, **non mesurée**) avec B = 50 mm et HFOV 55.4° à 640×480 : $Z_{min} \approx 0.48\text{ m}$, $Z_{max} \approx 3.0\text{ m}$.
- **Validation** : erreur de distance acceptable à 1 m et 2 m, par rapport à une mesure réelle, et carte de profondeur nette.

### Phase 7 — Détection et suivi d'une personne
**Objectif** : suivre une personne à distance constante.
1. Détecteur de personne : **YOLOv8s déjà en place sur la Pi** (`pi/stream_server.py`, classe `person`, ~10 FPS, phase 3) ; à brancher sur le suivi (YOLO nano ou MediaPipe restent des alternatives).
2. **Cap** : position horizontale de la personne dans l'image → vitesse de rotation.
3. **Distance** : profondeur médiane dans la boîte de détection (phase 6), consigne ~1,5 m → vitesse d'avance.
4. Sortie : commande de vitesse (avancer, tourner) envoyée au Teensy.
5. Gérer : personnes multiples (ré-identification par couleur de vêtements ou marqueur ArUco), **perte de la cible** (s'arrêter, tourner sur place), coupure wifi.
6. Lier avec les émotions : le robot joue un son joyeux quand il repère quelqu'un, etc.
- Version simple possible d'abord : **1 seule caméra**, distance estimée avec la taille de la boîte de détection.
- **Validation** : le robot suit une personne en marchant lentement, s'arrête devant un obstacle.

### Phase 8 — Locomotion par renforcement learning
**Objectif** : une politique de marche déployée sur le robot réel.
1. **Principe** : on simule le robot sur PC, une récompense (avancer, rester droit, peu d'énergie) guide l'apprentissage, et on obtient **un fichier de poids de réseau de neurones** (pas du code C généré).
2. Point de départ : dépôts **spot_mini_mini** (moribots, PyBullet, marche de Bézier + RL, ROS) et **rex-gym** (nicrusso7, environnements Gym pour SpotMicro, PPO). Pour l'inspiration : **microduck_rl** (Pollen Robotics).
3. Adapter le **URDF** à la vraie masse du robot (Pi 5, caméras, batterie, servos).
4. Entraîner, évaluer en simulation, puis robot **sur un support (« on rack »)**, pattes en l'air, avant tout test au sol.
5. Déploiement, au choix :
   - **Sur la Pi** : export ONNX + ONNX Runtime, envoi des angles cibles au Teensy.
   - **Sur le Teensy** : poids exportés en tableaux C + petite multiplication de matrices (réseau de 2-3 couches de ~128 neurones).
6. Calibrer : décalages de zéro des servos, sens de rotation, repère de l'IMU (MPU6050).
- **Validation** : marche stable en simulation, puis sur support, puis au sol sur surface plane.

### Phase 9 — Sécurité
- Ultrason dans la tête → **arrêt immédiat directement sur le Teensy** (sans passer par le wifi).
- Diviseur de tension sur ECHO (le Teensy n'est pas tolérant 5 V).
- Watchdog Pi → Teensy (phase 5), arrêt si perte de communication.
- **Broche OE du PCA9685** (active à l'état bas) reliée à une sortie du Teensy : permet de **couper toutes les sorties servos** instantanément (à confirmer sur le module).
- Servos sur alimentation dédiée, masses communes, fusible.
- Surveillance de la batterie (arrêt propre sous un seuil), bouton d'arrêt d'urgence physique.

### Phase 10 — Intégration, micro sur la Pi, autonomie
- **Micro sur la Pi** (USB ou I2S) à la place du micro du PC, sans changer le reste du code (source audio interchangeable).
- Reconnaissance vocale embarquée (Vosk ou whisper.cpp, petits modèles).
- Lancer tous les programmes au démarrage (services `systemd`).
- Mode dégradé si le wifi ou le PC ne sont pas disponibles : **le PC ne doit plus être essentiel**.
- Journalisation des erreurs, tests de bout en bout.

---

## 9. Décisions techniques et justifications

| Sujet | Décision / recommandation | Pourquoi |
|---|---|---|
| Raspberry Pi | **Pi 5 (8 Go)** | 2 ports caméra natifs (les Pi 3/4 et Zero n'en ont qu'un) |
| OS | **Raspberry Pi OS Lite 64 bits** | support officiel des caméras et du matériel, pas de bureau inutile |
| Modèle texte → émotion | **Piste A retenue** : embeddings `paraphrase-multilingual-MiniLM-L12-v2` + `LogisticRegression`, exécutée sur la Pi 5 | **mesuré** : 88.6 % sur 35 phrases de test, 15.9 ms par phrase, léger en RAM. Piste B (petit LLM) non testée, gardée en repli |
| Transport PC → Pi | **TCP, port 5005** (texte / émotions, lignes UTF-8, réponse JSON) + **HTTP 8080** (vidéo MJPEG) | simple, robuste ; le serveur reçoit du texte quelle que soit l'origine (micro du PC ou, plus tard, micro de la Pi) ; la vidéo s'observe dans un navigateur Web |
| Modèle de vision IA | **YOLOv8s (Small)** sur CPU, `conf=0.15`, classes personne / chat / chien / téléphone, régulation ~10 FPS | plus précis à 2 m que Nano, ~10 FPS sur Pi 5, charge CPU maîtrisée par la régulation de boucle |
| Reconnaissance vocale | **Vosk**, modèle `vosk-model-small-fr-0.22`, sur le PC | léger, français, temps réel ; Vosk local sur la Pi en phase 10 |
| Réseau de la Pi | NetworkManager : `Livebox-63C0` / `Danielandjacobs` priorité 20, hotspot iPhone priorité 10 | bascule automatique selon le lieu |
| Ordre de dev | **émotions d'abord (phase 2 faite avant la phase 1, faute de buzzer), caméras ensuite** | pas encore de caméra stéréo, le buzzer est simple et motivant |
| Buzzer | **passif, sur un GPIO de la Pi**, avec gpiozero | émotions dans le code haut niveau, aucun protocole intermédiaire. Limite : Linux n'est pas temps réel, un son peut hoqueter si la Pi est très chargée |
| Sortie audio | **aucune** (buzzer seul) | choix de design, plus simple |
| Micro | **PC d'abord**, Pi à terme | pas de micro acheté pour l'instant |
| IMU | **MPU6050 sur le Teensy** | lecture rapide et régulière, sécurité indépendante de la Pi. Limites : pas de magnétomètre (yaw qui dérive), sensible aux vibrations (filtre nécessaire), copies bon marché de qualité variable |
| Contrôleur de servos | **PCA9685** en I2C, VCC en 3,3 V | PWM matérielle stable, pas de conversion de niveau |
| Alimentation des servos | **DS3218MG à 5,5 V** via **un seul gros convertisseur 10 A** (6,0 V si le couple manque, jamais > 6,8 V), fils rouges hors PCA9685, condensateur 470 à 2200 µF | décision de budget du 2026-11-01 : un seul convertisseur. 12 servos bloqués = 22 à 31 A théoriques : ne jamais bloquer un servo, limiter vitesse et accélération, démarrage progressif, **mesurer** au wattmètre ; 2e convertisseur seulement si la mesure l'impose |
| Liaison Pi ↔ Teensy | **câble USB direct** (`/dev/ttyACM0`), alimentation du Teensy par l'USB de la Pi | décision du 2026-11-02 : simple, sert aussi à programmer. Alimenter le Teensy par VIN + UART a été écarté (pad à couper, à vérifier sur PJRC) |
| Chaîne de dev Teensy | **`arduino-cli` + `teensy_loader_cli` directement sur la Pi 5** | éditer, compiler et téléverser le C++ du Teensy à distance sans l'IDE graphique du PC |
| Bus I2C Teensy 4.0 | **SDA 18, SCL 19 (`Wire`)**, PCA9685 `0x40` (et `0x70` All-Call), MPU6050 `0x68` | broches I2C par défaut du Teensy 4.0 ; le PCA9685 répond toujours sur ces deux adresses au scan |
| Broches de capteurs du Teensy | **D2 = OE du PCA9685, D3 = TRIG, D4 = ECHO (via diviseur), A0 = tension batterie** | brochage proposé le 2026-11-01, pas encore en firmware (voir §5) |
| Buzzer sonore | **passif sur GPIO 18**, `gpiozero` (`PWMOutputDevice`), **volume 5 %** de rapport cyclique, **35 séquences** (5 variations par émotion) | fréquence et volume réglables ; à 50 % le signal était trop fort et strident ; le robot choisit une déclinaison au hasard pour éviter la répétitivité |
| Mise en route des servos | **démarrage séquentiel à 90°, 500 ms par servo** (`set_all_90`), mouvements **bridés à ±5°** pour les premiers essais (`walk_demo`) | limite l'appel de courant sur le convertisseur 10 A et évite les mouvements brusques |
| Coupure des servos | **OE du PCA9685 sur D2, actif à l'état bas** ; `stop_servos` met OE à `HIGH` | le Teensy peut couper toutes les sorties sans passer par la Pi |
| Cartographie des servos | **4 canaux par patte** : 0 extrémité, 1 milieu, 2 épaule, 3 libre ; AV-G 0-2, AV-D 4-6, AR-G 8-10, AR-D 12-14 | une patte = un groupe de canaux, gauche / droite vues de dessus dans le sens de marche |
| Boucle de marche | sur le robot (Teensy ou Pi) | ne doit pas dépendre du wifi |
| Écart des caméras | **$B = 50\text{ mm}$ entre axes optiques, retenu et installé** (avant : ≈ 47 mm estimé d'après le croquis Onshape, ouverture ≈ 71 × 53 mm, caméras 23 × 23 mm) | l'erreur de distance varie en 1/écart : plage utile théorique 0.48 m à 3.0 m à 640×480 avec le HFOV mesuré de 55.4° (calcul, erreur de corrélation supposée 1 px). Le HC-SR04 (45 × 20 mm) ne tient pas entre les caméras (vide central ≈ 24 mm) : le placer **au-dessus ou en dessous** |
| Inclinaison des caméras | **0° (parallèles), installé** ; ancienne idée : 10-20° chacune | `stereoRectify` rend la disparité (d = f·B/Z) indépendante de l'inclinaison : elle n'apporte **aucune précision**, et réduit le champ commun de la somme des deux angles (10° chacune avec 54° : 34° au lieu de 54°). Elle ne gagne presque pas de place non plus (23 mm → 22,5 mm à 10°). À rediscuter seulement si le champ réel est très large (> 90°) |
| Type de caméra pour la stéréo | focale **fixe**, idéalement **global shutter**, champ **70-90°**, 640×480 à 1280×720 | l'autofocus fausse la calibration ; le rolling shutter se déforme avec les vibrations de la marche |
| WPI408 / OV5647 | **HFOV mesuré = 55.4°** (cible à 40 cm, largeur visible 42 cm), utilisée pour la stéréo avec la 2e OV5647 | focale standard ~3.6 mm, pas de distorsion fisheye ; la fiche annonçant 130° était fausse |
| Motif de calibration | **Damier asymétrique $8 \times 7$ coins (9×8 cases, 22 mm)** | les motifs carrés ou pair/pair (7×7, 9×7 coins) créent une symétrie de rotation à 180° qui trompe OpenCV (RMS > 20 px) ; le motif 8×7 résout le problème à la racine |
| Validation lors de la capture | **Score de disparité Y calculé en temps réel** (`MAX_PAIR_DISPARITY_STD`) | évite d'enregistrer des clichés flous, réfléchis ou trop inclinés (> 25°) |
| Filtrage de calibration | **Filtrage automatique per-image, seuil RMS < 1.5 px** | isole les images géométriquement parfaites ; RMS individuel < 0.85 px et RMS stéréo ≈ 1.1 px atteints |
| Algorithme de disparité | **OpenCV `StereoSGBM`** | plus précis que `StereoBM` sur les scènes réelles complexes et peu texturées |
| Ultrason | sécurité, pas capteur principal | cône étroit, mal adapté aux tissus et surfaces obliques |
| RL | entraînement sur PC, politique embarquée | petit réseau, léger à exécuter |

---

## 10. Pièges connus

- **Pi 5** : connecteurs caméra de 22 broches (adaptateur nécessaire pour une nappe de 15 broches), pas de prise jack audio, 5 V / 5 A recommandés.
- **Wifi en déplacement** : le PC doit être sur le même réseau que la Pi ; `.local` peut ne pas marcher sur un hotspot de téléphone. **L'IP de la Pi change selon le réseau** : mettre à jour `HostName` (`.ssh\config`) et `PI_IP` (`config.py` du PC).
- **Teensy 4.0** : entrées/sorties en **3,3 V uniquement**.
- **PCA9685** : ne pas alimenter VCC en 5 V si l'I2C est relié au Teensy.
- **HC-SR04** : ECHO en 5 V, diviseur de tension obligatoire. Avec 1 kΩ / 2,2 kΩ, D4 voit environ 3,4 V (3,5 V si le 5 V est à 5,1 V) : acceptable mais marge faible sous la limite d'entrée du Teensy (environ 3,6 V, à ma connaissance) ; pour plus de marge, remplacer le 2,2 kΩ par 2 × 1 kΩ en série (3,33 V).
- **LM2596** : 2 A nominal / 3 A max, pas pour les servos. **Gros convertisseur 10 A** : 12 servos DS3218MG bloqués en demandent 22 à 31 A : un servo bloqué peut le faire couper ; ne jamais bloquer un servo, démarrer progressivement, mesurer le courant réel.
- **Calibration stéréo** : à refaire si le support bouge ou si la mise au point change.
- **Symétrie du damier de calibration** : ne **jamais** utiliser un damier pair × pair en carreaux ou impair × impair en coins (7×7, 9×7). Cela provoque des inversions de 180° entre la caméra gauche et la droite, un RMS de 20 à 30 px et une baseline aberrante (> 200 mm). Utiliser le damier asymétrique 8×7 coins.
- **Capture sur écran de PC** : très efficace pour garantir la planéité du damier, mais attention aux inclinaisons trop fortes (> 25°) et aux reflets lumineux, qui dégradent la précision sous-pixel.
- **Nombre minimal de paires validées** : même si le filtrage donne un RMS bas (1.1 px) avec 6 paires, il faut **au moins 12 à 15 paires d'angles variés** pour éviter l'ambiguïté d'échelle sur la distance T (baseline).
- **Champ de la WPI408** : la fiche annonçait 130° mais le champ **mesuré est de 55.4°**, cohérent avec la focale de 3,6 mm. Pour une autre caméra ou un autre mode d'image, **mesurer** plutôt que se fier à la fiche (mur plat à D mm, largeur visible W mm : `python stereo_planner.py --fov-from D W`) ; les modes 1920×1080 recadrent l'image.
- **Un seul serveur sur le port 8080** : `pi/stream_server.py` et `pi/stream_dual.py` utilisent le même port, ne pas les lancer en même temps. Un script de capture et un serveur de streaming ne peuvent pas non plus ouvrir les mêmes caméras simultanément.
- **`arduino-cli` mal placé** : sur ARM64 le script d'installation peut mettre le binaire dans `~/spot-micro/bin/arduino-cli` ; le déplacer dans `/usr/local/bin/`.
- **Chemin du `.hex`** : `arduino-cli` le crée dans un sous-dossier de build profond ; compiler avec `--output-dir .` pour l'avoir à côté du projet avant `teensy_loader_cli`.
- **Bouton de la Teensy** : si `teensy_loader_cli` reste sur *Waiting for Teensy device...*, appuyer une fois sur le petit bouton de la carte.
- **Buzzer trop fort** : ne jamais utiliser la PWM à 50 % ; rapport cyclique de 2 à 5 % en logiciel.
- **Variations d'émotions finissant par `e`** : avant d'isoler le dernier caractère comme lettre de variation, vérifier si le mot entier est une émotion valide (`neutre`, `triste`, `colere`).
- **`rpi-lgpio` sur Pi 5** : demande les paquets système `swig`, `python3-dev` et `liblgpio-dev` pour compiler.
- **Teensy 4.0, VIN et USB** : ne pas alimenter VIN en même temps que l'USB sans avoir lu la page PJRC (pad à couper à ma connaissance, non vérifié).
- **Condensateur des servos** : respecter la polarité (la bande marque le −), tension nominale ≥ 10 V.
- **OE du PCA9685 actif à l'état bas** : le Teensy doit forcer D2 à `LOW` pour activer les sorties et à `HIGH` pour les couper. Ne pas inverser la logique dans le firmware.
- **Mouvements de servos** : premiers essais **bridés (±5°)**, robot sur support, servos démarrés un par un. Ne jamais bloquer un servo (voir §5).
- **Masse du robot** : mettre à jour le URDF dès qu'un composant est ajouté, sinon la marche apprise sera décalée.
- **Buzzer sur Pi** : si le son est instable, utiliser le PWM matériel.

---

## 11. Journal (ordre chronologique, le plus récent en bas)

- **2026-10-24** — Définition du projet : Spot Micro avec 2 caméras (profondeur), micro, voix R2-D2, PC en wifi, RL. Architecture retenue : Raspberry Pi + Teensy 4.0. Comparaison des Pi : la Pi 5 est retenue pour ses 2 ports caméra. Recherche de modèles RL existants pour Spot Micro (spot_mini_mini, rex-gym).
- **2026-10-26** — Acquisition d'une **Pi 5 de 8 Go** et d'une **caméra WPI408**. OS recommandé : Raspberry Pi OS Lite 64 bits. Procédure d'installation par Imager. Gestion du wifi changeant (partage de connexion du téléphone) via `nmcli`/`nmtui`. Point sur le câble adaptateur 22 → 15 broches.
- **2026-10-27** — **Raspberry Pi Connect activé**. Création du README. Décisions : **buzzer passif sur la Pi** (gpiozero, pas sur le Teensy), **pas de sortie audio**, **micro du PC au départ** puis micro sur la Pi, **IMU MPU6050 sur le Teensy**, **PCA9685** pour les servos, **LiPo 3S** avec LM2596 et un gros convertisseur. **Ordre de développement : émotions avant caméras.** Premier démarrage de la Pi en cours avec un chargeur de téléphone USB-C.

- **2026-10-27 (suite)** — Matériel d'alimentation précisé : servos **DS3218MG**, un **DZS 12 A**, plusieurs **LM2596**. Servos à régler à **6,0 V**. Constat : 12 servos peuvent dépasser les 12 A d'un seul convertisseur → 2e DZS 12 A recommandé (6 servos chacun), fils rouges des servos hors du PCA9685, consommation réelle à mesurer.

- **2026-10-27 (suite 2)** — Phase 0 : `apt update && full-upgrade` réussi (21 paquets, dont rpi-connect-lite 2.14, libcamera 0.7.2, rpicam-apps 1.14), puis reboot. Avertissements bénins : un dépôt deb.debian.org injoignable (hotspot lent) et `rehash: skipping ca-certificates.crt`.

- **2026-10-27 (suite 3)** — Phase 0 : installation de `git python3-pip tmux` (python3-venv et htop déjà présents), Python 3.13, git 2.47.3. `loginctl enable-linger` exécuté (pour Raspberry Pi Connect sur Lite).

- **2026-10-27 (suite 4)** — Phase 0 : clé SSH en place (connexion sans mot de passe). VS Code Remote-SSH installé et fonctionnel : `spot.local` ne se résolvait plus sur le hotspot iPhone ("Hôte inconnu"), contourné avec l'IP `172.20.10.2` (bloc `Host spot` dans `C:\Users\nomis\.ssh\config`, HostName 172.20.10.2, User simon). Dossier `/home/simon` ouvert, terminal OK (`hostname` → Spot).

- **2026-10-27 (suite 5)** — Phase 2 démarrée : choix du modèle qui comprend les phrases pour déduire l'émotion. Contraintes précisées par l'utilisateur : tourner de préférence sur la **Pi 5 (8 Go)** avec une faible consommation, micro du PC au début puis micro sur la Pi, une IA basique suffit pour choisir content / triste / etc. Buzzer toujours absent : on affiche l'émotion détectée. Pistes comparées (§8, Phase 2) : embeddings + classifieur (recommandé), petit LLM (repli). **Mise à jour (suite)** : décision de tester A d'abord, puis B, et de garder le meilleur (réponse rapide prioritaire). La Pi ne servira qu'à la profondeur (2 caméras), à la parole + émotion et au buzzer, donc un modèle plus gros est envisageable. Étape en cours : définir la liste fixe des émotions.

- **2026-10-27 (suite 6)** — Liste d'émotions **validée** : `content, triste, curieux, surpris, colere, peur, neutre` (`neutre` = phrases sans émotion). Création de `pi/emotions_data.py` : 20 phrases d'entraînement + 5 phrases de test par émotion (TEST ne sert qu'à mesurer, jamais à entraîner). Prochaine étape : installer `sentence-transformers` et `scikit-learn` (modèle d'embeddings téléchargé d'abord sur le PC, hotspot lent), entraîner le classifieur (piste A) et mesurer précision + temps de réponse sur la Pi.

- **2026-10-27 (soir 2)** — Entraînement et validation de la Piste A (embeddings + LogisticRegression) sur la Pi 5. Résultats sur le jeu TEST (35 phrases) : précision globale 88.6 %, temps d'inférence moyen 15.9 ms par phrase. La Piste A est retenue pour sa rapidité et sa faible consommation.

- **2026-10-28** — **Phase 2 terminée** (2b et 2c). `pi/emotion_server.py` : serveur TCP (port 5005) en arrière-plan sur la Pi, modèle gardé en RAM, reçoit des lignes UTF-8 et renvoie `{"emotion", "confiance", "ms"}` (50-100 ms au total). Côté PC (`C:\Users\nomis\Documents\Spot\`, hors Git) : `config.py` (`PI_IP`, `PORT`), `text_client.py`, `voice_client.py` (micro via `sounddevice` + Vosk `vosk-model-small-fr-0.22`), copie de sauvegarde du modèle MiniLM. Dépôt Git `spot-micro` en place sur la Pi (`.gitignore` : `__pycache__/`, `venv/`, `pi/model_minilm/`). Wi-Fi de la Pi géré par NetworkManager : `Danielandjacobs` priorité 20, hotspot iPhone priorité 10 (secours). Nouvelle IP : `10.20.30.31`. Piste B non testée.

- **2026-10-31** — Phase 6 préparée : choix du support stéréo. Caméras OV5647 5 MP 23 × 23 mm (champ inconnu), ≈ 71 mm d'espace dans la tête. Création de `stereo_planner.py` (PC) : plage de profondeur selon écart, inclinaison de chaque caméra, champ, résolution (interface à curseurs, rapport texte, tableau de comparaison, calcul du champ depuis une mesure). Résultats de calcul (non mesurés) : écart 47 mm, champ 54°, 640 px → distance mini ≈ 232 mm, maxi ≈ 2,95 m à 10 % d'erreur (1 px de corrélation). Recommandation : écart ≈ 47 mm, caméras parallèles, support n°1 réglable.

- **2026-10-31 (suite)** — **Phase 3 terminée**. Caméra WPI408 (OV5647) reconnue sur `CAM0`, tests CLI et Python réussis. Serveur Web Flask `pi/stream_server.py` (port 8080) avec détection d'objets **YOLOv8s** (`conf=0.15`, personnes, chats, chiens, téléphones, ~10 FPS grâce à une régulation de boucle).

- **2026-10-31 (soir)** — **Phase 6b**. Mesure réelle du champ horizontal de la WPI408 : cible à 40 cm, largeur visible 42 cm, **HFOV = 55.4°** (la fiche annonçant 130° est fausse). Validation de l'entraxe **B = 50 mm** à 0° (plage utile théorique 0.48 m à 3.0 m à 640×480).

- **2026-11-01** — **Phases 6c / 6d en cours**. 2e caméra OV5647 branchée sur `CAM1` et détectée. Création de `pi/stream_dual.py` (alignement horizontal), `pi/test_stereo.py`, `pi/capture_calibration.py` (score de validation géométrique) et `pi/test_depth.py` (StereoSGBM). La Pi est maintenant jointe sur le Wi-Fi `Livebox-63C0` / `Danielandjacobs` à l'IP `192.168.1.28` (`PI_IP` du `config.py` PC mis à jour).

- **2026-11-01 (suite)** — Analyse des erreurs de calibration (RMS 20 à 30 px, baseline aberrante) : passage au **damier asymétrique 8 × 7 coins** (9×8 cases, 22 mm) pour supprimer l'ambiguïté de rotation à 180°. Ajout du filtrage per-image (RMS < 1.5 px) dans `pi/calibrate_stereo.py` : RMS individuel abaissé de 5.0 px à **0.681 px** (gauche) et **0.842 px** (droite), RMS stéréo **1.102 px** (avec 6 paires). Reste à accumuler 12 à 15 paires validées pour verrouiller la baseline à 50 mm.

- **2026-11-01 (alimentation)** — Décision budget : **un seul gros convertisseur 10 A** pour les 12 servos (réglé à 5,5 V), **2 × LM2596** (n°1 : Pi à 5,1 V ; n°2 : réserve), pas d'achat d'autre convertisseur. Estimation du courant (non mesurée) : 4 à 6 A debout, 8 à 12 A en pointe. Schémas de câblage (alimentation, signaux) créés, brochage fixé dans §5 (D2 OE, D3 TRIG, D4 ECHO, A0 batterie, I2C 18/19). Condensateur des servos assoupli : idéal 2200 µF, minimum environ 470 µF. Teensy alimenté par l'USB de la Pi (VIN + UART écarté).
- **2026-11-02** — **Phase 1 terminée et boucle vocale complète validée.** Banque `pi/emotions.py` de 35 sons R2-D2 sur GPIO 18 (volume 5 %), bug du `e` final des émotions corrigé, dépendances `swig` / `liblgpio-dev` / `rpi-lgpio` installées. Parole au micro du PC → Pi 5 (MiniLM) → réaction immédiate sur le buzzer.
- **2026-11-02 (soir)** — **Phase 5 démarrée.** Teensy 4.0 vue en USB sur `/dev/ttyACM0`, chaîne `arduino-cli` + `teensy_loader_cli` + règles udev PJRC installée sur la Pi, `teensy/i2c_scanner/i2c_scanner.ino` compilé et téléversé depuis la Pi, **PCA9685 détecté à `0x40`** (et `0x70`). README mis à jour avec les schémas de câblage et le rappel des tensions (§5).

- **2026-11-02 (soudures)** — Ponts diviseurs réellement soudés : **HC-SR04 ECHO : 1 kΩ / 2,2 kΩ** (environ 3,4 V sur D4) et **batterie : 33 kΩ / 10 kΩ** (12,6 V → 2,93 V sur A0, batterie = tension lue × 4,3). Schémas et §5 mis à jour.

- **2026-11-03** — Réglages mesurés au multimètre : **gros convertisseur 10 A = 5,55 V** (cible 5,5 V, servos 4,8 à 6,8 V : OK), **LM2596 n°1 = 5,0015 V** (cible 5,1 V : acceptable à vide, à vérifier sous charge). Question en cours : alimenter la Pi par les broches 5 V du GPIO (pins 2/4 + GND pins 6/9), sans protection de l'entrée USB-C.

- **2026-11-03 (suite)** — Le gros convertisseur a 2 potentiomètres : haut = tension, bas = limite de courant (à mettre au maximum pour les servos).

- **2026-11-03 (électronique validée)** — Toute la partie électronique fonctionne (utilisateur) : alimentation, HC-SR04, PCA9685 et 12 servos. Firmwares ajoutés dans `teensy/` : `test_hcsr04`, `test_servo`, `set_all_90`, `walk_demo`, `stop_servos`. **Cartographie des 12 canaux** : AV-G 0-2, AV-D 4-6, AR-G 8-10, AR-D 12-14 (0 extrémité, 1 milieu, 2 épaule, le 4e canal de chaque groupe est libre). OE sur D2 (`LOW` = actif). **Il ne reste que l'IMU MPU6050 à tester** (puis le protocole série Pi ↔ Teensy).

- **2026-11-04 (audit hors matériel)** — Corrections logicielles et tests hors matériel (`pc/`, `robot/pi/`, `robot/teensy/`, `tests/`, rapport `robot/docs/AUDIT.md`) : cadrage TCP par lignes UTF-8, sécurité `OE` sur D2 (`HIGH` immédiat, `FULL_OFF` 4096 et contrôle I2C avant `LOW`, paliers 500 ms ; recompiler les `.ino` avant usage), compteur persistant et appariement par identifiant pour la stéréo ; aucun test sur le robot réel.

*(Ajouter ici une ligne par étape

---

## 12. Consignes pour les agents IA qui aident sur ce projet

1. **Lire ce README en entier** avant de répondre, et s'appuyer sur la section *Statut*.
2. **Ne pas inventer de matériel ou de config** : tout ce qui est marqué `[?]` ou « à confirmer » doit être vérifié avec l'utilisateur.
3. **Répondre en français**, avec des étapes courtes et des commandes prêtes à copier.
4. **Tester d'abord en petit** : une fonction à la fois, validation avant la phase suivante.
5. **Sécurité avant tout** : robot sur support avant tout test de marche, attention aux tensions (Teensy 3,3 V, ECHO 5 V) et aux alimentations (LiPo 3S).
6. **Après chaque étape** : proposer la mise à jour du *Statut*, du *Journal* et de la *Configuration* de ce fichier.
7. Ne jamais demander ni écrire de mots de passe, clés ou informations personnelles dans le dépôt.
8. Quand un chiffre est une estimation (précision stéréo, performances), **le dire**.

---

## 13. Ressources

- spot_mini_mini (PyBullet, Bézier + RL, ROS) : https://github.com/moribots/spot_mini_mini
- rex-gym (environnements Gym pour SpotMicro, PPO) : dépôt `nicrusso7/rex-gym`
- Microduck : https://github.com/pollen-robotics/microduck et https://github.com/pollen-robotics/microduck_rl
- Projet communautaire SpotMicroAI (simulation et matériel)
- Raspberry Pi Imager, Raspberry Pi Connect, documentation `rpicam-apps` et `picamera2`
- Teensy 4.0 : pages PJRC (alimentation, brochage)
- `arduino-cli` et `teensy_loader_cli` (compilation et téléversement du Teensy depuis la Pi)
- Vosk (modèle français `vosk-model-small-fr-0.22`) et `sounddevice` (micro côté PC)

---

## 14. Notes pour le prochain agent IA (à jour au 2026-11-03)

- **Utilisateur** : Simon, PC **Windows** (PowerShell), débutant sur Linux/Pi : commandes courtes à copier ; **il accepte plusieurs étapes à la fois, mais toujours détaillées** ; lui demander le résultat exact avant de continuer.
- **Réseau** : la Pi est sur le Wi-Fi principal (`Livebox-63C0` / `Danielandjacobs`, priorité 20), IP `192.168.1.28` (2026-11-01) ; hotspot iPhone en secours (IP vue le 2026-10-27 : `172.20.10.2`, `spot.local` ne s'y résolvait pas). Si l'IP change : `hostname -I` (via Raspberry Pi Connect si besoin), puis `HostName` dans `C:\Users\nomis\.ssh\config` et `PI_IP` dans `Spot\config.py`. Le hotspot iPhone est lent (~7 Ko/s vers certains dépôts).
- **Situation** : **Phases 0, 1, 2, 3 et 4 terminées** ; **phase 5 en cours** : PCA9685, HC-SR04 et **12 servos validés**, il reste l'**IMU MPU6050** (5g) et le protocole série Pi ↔ Teensy avec watchdog (5h) ; **phase 6 en cours** (6d : calibration, ≥ 12 paires `[VALIDE]`). Voir §2. Le robot entend (micro du PC + Vosk), classe l'émotion (Pi 5) et s'exprime sur le buzzer (35 sons R2-D2, 5 %). Streaming vidéo + YOLOv8s sur le port 8080. `[?]` `vcgencmd get_throttled` à vérifier ; `[?]` lancement permanent du serveur (`systemd` prévu en phase 10).
- **Matériel manquant** : un micro pour la Pi (plus tard) et le **MPU6050** (seul composant électronique encore à tester). Tout le reste est en place et fonctionne : Pi 5, Teensy 4.0, PCA9685, 12 servos DS3218MG, HC-SR04, buzzer, deux caméras OV5647, LiPo, convertisseur 10 A et 2 LM2596 (pas d'autre convertisseur prévu).
- **Ordre de développement** : phase 2 avant la phase 1 (faute de buzzer), puis caméra (phase 3), stéréo (phase 6), buzzer et boucle vocale complète (phase 1, 2026-11-02), puis Teensy (phase 5). **Objectif immédiat** : voir les lignes Teensy et Stéréo. Ensuite au choix : montage de l'alimentation (phase 4) avec mesure au wattmètre, ou **Phase 7** (suivi de personne, YOLOv8s + profondeur).
- **Phase 2, limites connues** : 88.6 % de précision sur 35 phrases (4 erreurs), piste B non testée. Pour améliorer : enrichir `pi/emotions_data.py` (phrases d'entraînement) avant de changer de modèle.
- **Interface entre modules** : le serveur renvoie le nom de l'émotion (un mot de la liste `content, triste, curieux, surpris, colere, peur, neutre`) en JSON ; `jouer(emotion)` le recevra.
- **Code PC** : l'utilisateur gère son dossier `C:\Users\nomis\Documents\Spot\` lui-même, hors dépôt Git. **Ne pas tenter de le commiter ou de le transférer depuis la Pi.**
- **Stéréo, état au 2026-11-01** : caméras gauche (`CAM0`) et droite (`CAM1`) fonctionnelles, HFOV mesuré 55.4°, support B = 50 mm à 0°. Scripts prêts dans `pi/` : `stream_dual.py`, `capture_calibration.py`, `calibrate_stereo.py`, `test_depth.py`. **Objectif immédiat** : relancer `python pi/capture_calibration.py` pour accumuler 12 à 15 paires marquées `[VALIDE]` (damier asymétrique 8×7 coins à l'écran, écran plat, inclinaison < 25°, distances 40 cm à 1,2 m, éviter les reflets), puis `python pi/calibrate_stereo.py` pour que la baseline calculée se fixe sur 50 mm, puis `python pi/test_depth.py` pour valider la carte de profondeur (test à 0,5 / 1 / 1,5 / 2 m). Les valeurs de `stereo_planner.py` reposent sur une **erreur de corrélation supposée de 1 px**, à remplacer par la valeur mesurée après calibration. Les scripts `pi/` se lancent sur la Pi dans `~/venv`.
- **Alimentation et câblage, état au 2026-11-03** : **validés en fonctionnement par l'utilisateur**. Un seul convertisseur 10 A (5,55 V) pour les 12 servos, LM2596 n°1 (5,0015 V) pour la Pi, LM2596 n°2 en réserve ; Teensy alimenté et relié par l'**USB de la Pi**. Schémas en images dans `docs/` (`schema_alimentation.png`, `schema_signaux.png`, à placer par l'utilisateur) et en texte dans §5. `[?]` courant réel non mesuré au wattmètre. Ne pas recommander l'achat d'un 2e convertisseur sans mesure. Fil rouge des servos **sur le bornier du convertisseur, jamais via le V+ du PCA9685**.
- **Teensy, état au 2026-11-03** : `/dev/ttyACM0`, `arduino-cli` + `teensy_loader_cli` fonctionnels sur la Pi. Firmwares dans `~/spot-micro/teensy/` : `i2c_scanner`, `test_hcsr04`, `test_servo`, `set_all_90`, `walk_demo`, `stop_servos`. OE sur D2 (`LOW` = actif). Cartographie des servos : voir §5 (AV-G 0-2, AV-D 4-6, AR-G 8-10, AR-D 12-14). **Prochaines étapes** : (1) tester le MPU6050 (I2C 18 / 19, `0x68`, offsets du gyroscope, filtre complémentaire ou Madgwick), (2) protocole ASCII Pi ↔ Teensy avec watchdog, (3) tester la mesure de batterie sur A0 (× 4,3).
- **`[?]` Dépôt et dossier PC** : une version du README citait un dossier `pc/voice_client.py` dans le dépôt ; la règle de l'utilisateur reste de **ne pas transférer ni commiter** son dossier PC (`C:\Users\nomis\Documents\Spot\`). À confirmer avec lui avant de toucher à `pc/`.
- **Audit hors matériel (2026-11-04, `robot/docs/AUDIT.md`)** : corrections et tests unitaires (`tests/test_emotion.py`, `tests/test_teensy.py`, `tests/test_stereo_pipeline.py`) intégrés hors matériel ; recompiler impérativement les sketchs `.ino` avant téléversement sur la Teensy (anciens binaires périmés) et noter que `pc/voice_client.py` versionné utilise Google `SpeechRecognition` (et non Vosk).
- **Consigne de l'utilisateur sur ce README** : ne pas le réécrire en entier. Modifier uniquement les parties qui changent et ajouter ici (fin du fichier) les infos importantes pour l'agent suivant.
