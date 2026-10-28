# Spot Micro R2-D2 — journal de bord et feuille de route

> **Ce fichier est la source de vérité du projet.** Il récapitule la config, les décisions et ce qui a été fait, pour qu'une personne ou un agent IA puisse reprendre le travail sans tout redemander.
> **Règle : après chaque étape terminée, mettre à jour la section *Statut*, la section *Journal* et, si besoin, la section *Configuration*.**

Dernière mise à jour : 2026-10-28

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
- [x] Caméra Whadda WPI408 acquise (1 seule pour l'instant)
- [x] Raspberry Pi Connect activé
- [x] OS écrit sur la microSD, utilisateur `simon`, SSH activé (hôte à retrouver, voir §5)
- [x] **Premier démarrage de la Pi** (chargeur de téléphone USB-C), connexion SSH réussie le 2026-10-27
- [x] Phase 0 : base système et dev à distance (SSH, mise à jour, outils, `enable-linger`, clé SSH et VS Code Remote-SSH faits ; dépôt Git `spot-micro` en place sur la Pi ; `[?]` vérif `vcgencmd get_throttled` non notée dans le journal)
- [x] Réseau Wi-Fi de la Pi (NetworkManager) : `Danielandjacobs` priorité 20 (principal), hotspot iPhone priorité 10 (secours)
- [ ] Phase 1 : buzzer passif et émotions (sur la Pi)
- [x] Phase 2 : parole via le micro du PC → humeur (terminée le 2026-10-28)
  - [x] 2a : modèle Piste A validé (embeddings `paraphrase-multilingual-MiniLM-L12-v2` + `LogisticRegression`, précision 88.6 % sur 35 phrases de test, 15.9 ms/phrase sur Pi 5) ; piste B (petit LLM) non testée
  - [x] 2b : serveur TCP `pi/emotion_server.py` sur la Pi (port 5005, modèle gardé en RAM, 50-100 ms au total)
  - [x] 2c : client vocal PC `voice_client.py` (Vosk `vosk-model-small-fr-0.22` + `sounddevice`), configuration IP centralisée dans `config.py` (côté PC)
- [ ] Phase 3 : caméra n°1
- [ ] Phase 4 : alimentation et électronique du robot
- [ ] Phase 5 : Teensy (servos, IMU, ultrason) + liaison Pi ↔ Teensy
- [ ] Phase 6 : 2e caméra et profondeur stéréo
- [ ] Phase 7 : détection et suivi d'une personne
- [ ] Phase 8 : locomotion par RL
- [ ] Phase 9 : sécurité
- [ ] Phase 10 : intégration, micro sur la Pi, autonomie sans PC

---

## 3. Matériel

| Élément | Détail | Statut |
|---|---|---|
| Ordinateur embarqué | **Raspberry Pi 5, 8 Go** | possédé |
| Microcontrôleur | **Teensy 4.0** (Cortex-M7 600 MHz, **3,3 V, entrées non tolérantes 5 V**) | prévu |
| Buzzer | **passif**, branché sur un GPIO de la **Pi** (pas sur le Teensy) | à acheter |
| Sortie audio (haut-parleur) | **non utilisée**, seul le buzzer s'exprime | abandonnée |
| Micro | **micro du PC** au départ, micro sur la Pi à terme (USB ou I2S) | à acheter plus tard |
| IMU | **MPU6050** (module GY-521) sur le **Teensy**, I2C | prévu |
| Contrôleur de servos | **PCA9685** (16 canaux, I2C) | possédé (à confirmer) |
| Servos | **DS3218MG** × 12 : numérique, engrenages métal, **4,8 à 6,8 V**, couple 19 kg·cm à 5 V, **courant à l'arrêt (rotor bloqué) 1,8 à 2,6 A**, impulsions 500-2500 µs (neutre 1500 µs), version **180° ou 270° à vérifier** | possédés (nombre à confirmer) |
| Batterie | **LiPo 3S** (11,1 V nominal, 12,6 V pleine charge) | possédée |
| Convertisseurs | **DZS Elec 12 A** × 1 (buck 4,5-30 V → 0,8-30 V, 12 A max, protections thermique et court-circuit) ; **LM2596** × plusieurs (2 A nominal, 3 A max avec dissipateur) | possédés |
| Ultrason | **HC-SR04** (ou **HC-SR05**, à confirmer), dans la tête, pour la sécurité | possédé (à confirmer) |
| Caméra n°1 | **Whadda WPI408** : capteur OV5647 5 Mpx, champ 130°, mise au point manuelle, 2 LED infrarouges, nappe 15 broches | possédée |
| Caméra n°2 | à choisir (voir §9) | à acheter |
| Câble caméra | adaptateur **22 broches (Pi 5) → 15 broches (caméra)**, 1 par caméra | [?] |
| PC | machine d'entraînement RL, micro, développement | possédé |

---

## 4. Architecture

```
      wifi (NetworkManager : Danielandjacobs prio 20 / hotspot iPhone prio 10)
   ┌────────────┐ <──────────────────────────────> ┌──────────────────┐
   │     PC     │   SSH / VS Code / voix (TCP 5005) │  Raspberry Pi 5  │
   │ micro (au  │   audio et vidéo / commandes      │ buzzer (GPIO),   │
   │ début), RL,│                                   │ caméras, micro   │
   │ calculs    │                                   │ (à terme),       │
   │ lourds     │                                   │ décisions        │
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
3. **`pi/emotions.py`** (à faire, phase 1) : reçoit l'émotion et joue la séquence R2-D2 sur le buzzer passif (GPIO 18).
4. **Liaison série USB `/dev/ttyACM0`** (à faire, phase 5) : état émotionnel et commandes de déplacement vers le Teensy 4.0.

Règles d'architecture :
1. **La boucle de marche (politique RL + asservissement des servos) tourne sur le robot** (Teensy, ou Pi), jamais dépendante du wifi ni du PC.
2. Le wifi et le PC servent au développement, au streaming et à des calculs optionnels. Si le wifi coupe, le robot doit rester debout ou s'asseoir.
3. **Le Teensy a le dernier mot sur la sécurité** : arrêt si l'ultrason détecte un obstacle proche, ou s'il ne reçoit plus d'ordre du Pi pendant un délai fixé (watchdog).
4. **Source audio interchangeable** : le code de reconnaissance vocale lit un flux « micro » abstrait, qui vient du PC au début et du micro local de la Pi à terme, sans changer le reste.
5. Le Teensy ne gère **pas** le buzzer : les émotions sonores sont jouées par la Pi.

---

## 5. Alimentation et électronique

### Arbre d'alimentation (proposition)
```
LiPo 3S (9 à 12,6 V)  ── fusible ── interrupteur
   │
   ├─► [DZS 12 A réglé à 6,0 V] ─► servos 1 à 6 (fils rouges directement, pas via le PCA9685)
   ├─► [2e DZS 12 A, 6,0 V, recommandé] ─► servos 7 à 12
   │
   ├─► [LM2596 à 5,1 V pour les essais, ou convertisseur 5 V ≥ 5 A] ─► Raspberry Pi 5
   │                                                          │
   │                                                          ├─ USB ─► Teensy 4.0 (5 V + données)
   │                                                          │            └─ broche 3,3 V ─► PCA9685 (VCC) + MPU6050
   │                                                          └─ GPIO ─► buzzer passif
   └─ HC-SR04 : alimenté par le 5 V de la Pi (broche 2 ou 4 du GPIO), environ 15 mA, donc pas de convertisseur dédié

Toutes les masses (GND) sont reliées entre elles.
```

### Conversions de tension : ce qui est nécessaire et ce qui ne l'est pas
- **5 V → 3,3 V pour le Teensy : aucun convertisseur à ajouter.** Le Teensy 4.0 a son régulateur 3,3 V intégré. Il peut être alimenté en 5 V par le câble USB de la Pi. Sa broche **3,3 V** sert ensuite à alimenter les petits modules 3,3 V (MPU6050, côté logique du PCA9685).
- **PCA9685** : alimenter sa broche **VCC à 3,3 V** (pas 5 V), car ses résistances de rappel I2C sont reliées à VCC et un VCC à 5 V enverrait du 5 V sur le bus I2C du Teensy. Le **V+** (alimentation des servos) vient du gros convertisseur. Le signal de commande des servos sortira en 3,3 V, ce qui est normalement accepté par les servos (**à tester sur un servo avant de tout brancher**).
- **MPU6050** : module GY-521 alimenté en 3,3 V, I2C du Teensy (**broches SDA 18 / SCL 19** de `Wire`). Même bus que le PCA9685, adresses différentes (0x68 et 0x40 par défaut).
- **HC-SR04 / HC-SR05** : alimentés en **5 V**. **TRIG** (sortie du Teensy, 3,3 V) est en général accepté tel quel. **ECHO** sort en **5 V** et **le Teensy 4.0 n'est pas tolérant 5 V** : mettre un **diviseur de tension** (ECHO → 1 kΩ → point milieu vers le Teensy → 2 kΩ → GND, ce qui donne environ 3,3 V), ou utiliser un capteur 3,3 V (HC-SR04P, etc.).
- **Servos DS3218MG** : plage **4,8 à 6,8 V**. Régler les convertisseurs des servos à **6,0 V** (marge sous 6,8 V, **ne jamais dépasser 6,8 V**). Courant à l'arrêt **1,8 à 2,6 A par servo** : 12 servos bloqués = **22 à 31 A** théoriques, contre **12 A max par convertisseur DZS** (limitation à 14 A). La consommation réelle en marche est **à mesurer** (wattmètre sur la batterie), mais un seul convertisseur sera juste : **prévoir un 2e DZS 12 A** et répartir **6 servos par convertisseur** (par exemple pattes gauches / pattes droites).
- **DZS 12 A** : le rendement baisse avec le courant (environ 81 % à 5 V / 10 A selon une fiche), prévoir un dissipateur et, au-delà d'environ 8 A en continu, un petit ventilateur. Les fiches se contredisent sur la **protection contre l'inversion de polarité** : fusible + connecteurs XT60 détrompés. Protections thermique et court-circuit présentes.
- **LM2596** : **2 A nominal, 3 A max avec dissipateur**. **Pas adapté aux servos**. Convient aux petites charges et, avec précaution, à la Pi 5 pour des essais (régler à 5,1 V, mesurer la consommation réelle : la Pi 5 peut dépasser 2 A en charge).
- **Pi 5** : alimentation officielle 5 V / 5 A. Alimentée par un convertisseur, elle peut signaler une alimentation insuffisante si elle ne détecte pas 5 A. À régler au moment de l'intégration.

### Règles de câblage
1. **Régler chaque convertisseur au multimètre avant de brancher quoi que ce soit** dessus.
2. **Servos sur leur propre alimentation**, jamais depuis la Pi. **Fils rouges des servos reliés directement à la sortie des convertisseurs** (bornier ou carte de distribution), pas à travers les pistes du PCA9685 : le PCA9685 ne fournit que le **signal** et la **masse**. Un condensateur de 2200 à 4700 µF (10 V minimum, faible ESR) sur chaque sortie de convertisseur des servos.
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
| Nom d'hôte | `spot` (connexion : `ssh simon@spot.local`, fonctionne depuis PowerShell Windows) |
| Utilisateur | `simon` |
| SSH | activé |
| Adresse IP | `10.20.30.31` sur `Danielandjacobs` (2026-10-28). Variable selon le réseau (sur le hotspot iPhone : `172.20.10.2` le 2026-10-27) → voir §7 |
| Réseaux Wi-Fi | NetworkManager : `Danielandjacobs` (priorité 20, principal) ; `netplan-wlan0-iPhone de Simon` (priorité 10, secours) |
| Serveur d'émotions | `pi/emotion_server.py`, port TCP **5005**, tourne en arrière-plan (méthode de lancement permanent `[?]` à confirmer ; services `systemd` prévus en phase 10) |
| Raspberry Pi Connect | activé le 2026-10-27 (sur Lite : accès par **shell distant**, à confirmer) |
| Alimentation du premier démarrage | chargeur de téléphone USB-C (suffisant pour démarrer, à remplacer à terme) |
| Caméra n°1 | WPI408 (branchement à confirmer) |
| Python | paquets système : `python3-picamera2`, `python3-opencv` |
| Environnement Python | `python3 -m venv --system-site-packages ~/venv` |

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
- **Réseaux actuels** : `Danielandjacobs` (priorité 20, tenté en premier), puis `netplan-wlan0-iPhone de Simon` (priorité 10, secours).
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
- Programmer le **Teensy depuis le PC** (Arduino IDE + Teensyduino, ou PlatformIO).

### Arborescence du dépôt Git (sur la Pi, `/home/simon/spot-micro/`)
```
spot-micro/
├── .gitignore                    ← ignore __pycache__/, venv/, pi/model_minilm/
├── README.md                     ← ce fichier
├── pi/                           ← code exécuté sur la Pi
│   ├── emotions_data.py          ← jeu de données TRAIN/TEST (7 émotions)
│   ├── train_emotion_model.py    ← entraînement de la régression logistique
│   ├── predict_emotion.py        ← testeur interactif local (CLI)
│   ├── emotion_server.py         ← serveur TCP, port 5005
│   ├── emotion_classifier.joblib ← classifieur entraîné
│   └── model_minilm/             ← modèle d'embeddings local (~450 Mo, hors Git)
├── teensy/                       ← firmware du Teensy (servos, IMU, ultrason, sécurité)
├── docs/                         ← schémas de câblage, notes de calibration, photos
└── hardware/                     ← CAO, URDF (masses des composants à jour)
```

### Dossier du PC Windows (hors dépôt Git : `C:\Users\nomis\Documents\Spot\`)
```
Spot/
├── config.py          ← réseau : PI_IP = "10.20.30.31", PORT = 5005
├── text_client.py     ← client de test au clavier
├── voice_client.py    ← micro du PC (sounddevice) + Vosk, envoi du texte à la Pi
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

### Phase 1 — Buzzer passif et émotions R2-D2 (sur la Pi)
**Objectif** : une bibliothèque d'émotions sonores jouées par la Pi.
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
4. **Fait pour l'envoi** : le PC envoie le texte à la Pi par TCP (`pi/emotion_server.py`, port 5005, réponse JSON `{"emotion", "confiance", "ms"}`, 50-100 ms au total). **Reste (phase 1)** : relier le résultat à `jouer(emotion)` quand le buzzer sera là ; en attendant, l'émotion détectée est affichée.
5. Écrire le code avec une **source audio interchangeable** (flux du PC / micro local), pour la phase 10.
- **Validation atteinte** : une phrase prononcée devant le micro du PC est transcrite, et l'émotion est renvoyée par la Pi en moins de 100 ms. La partie « son du robot » sera validée en phase 1.

**Choix du modèle texte → émotion (terminé : piste A retenue, 2026-10-27)** — contraintes : tourne sur la Pi 5 (8 Go), faible consommation, comprend des phrases complexes (« mon chat est mort » → triste). Les durées et tailles du tableau étaient des **estimations** faites avant les mesures ; seule la piste A a été mesurée (voir Résultat).
| Piste | Principe | Avantages | Limites |
|---|---|---|---|
| **A. Embeddings multilingues + classifieur léger** (ex. `paraphrase-multilingual-MiniLM-L12-v2`, ~118 M de paramètres, + régression logistique) | la phrase devient un vecteur, un classifieur appris sur quelques dizaines de phrases d'exemple par émotion choisit l'émotion | léger, rapide (quelques dizaines de ms estimées), RAM < 1 Go estimée, comprend le sens | il faut écrire les phrases d'exemple ; négations et sarcasme mal gérés |
| **B. Petit LLM quantifié** (ex. Qwen2.5 0.5B ou 1.5B Instruct, llama.cpp) | prompt « réponds par un seul mot parmi : content, triste… » | aucune donnée à préparer, meilleure compréhension | plus lent (de l'ordre de 1 à 3 s estimées), plus de RAM et de CPU, donc plus de consommation |
| **C. Mots-clés** | règles écrites à la main | trivial | écarté : ne comprend pas le sens |
- **Piste recommandée** : **A en premier**, **B en repli** si A se trompe trop. Ne lancer le modèle qu'**après détection de parole** (pour ne pas charger le CPU en continu). **Décision de l'utilisateur (2026-10-27)** : tester A d'abord, puis B, garder le meilleur ; la **rapidité de réponse prime**. La Pi n'a pas d'autre charge lourde prévue (profondeur 2 caméras, parole + émotion, buzzer) : un modèle plus gros que prévu est envisageable. Méthode : le même jeu de phrases de test sert à comparer A et B (précision et temps de réponse mesurés sur la Pi).
- **Reconnaissance vocale** (transcription) : Vosk avec un petit modèle français (léger) ou whisper.cpp (plus précis, plus lourd). Au début, le micro du PC envoie le texte ou l'audio à la Pi ; développer d'abord avec du **texte tapé au clavier**. **Réalisé** : `text_client.py` (clavier), puis `voice_client.py` (micro + Vosk).
- **Résultat (2026-10-27 soir, mesuré sur la Pi 5)** : piste A, **88.6 % de précision sur les 35 phrases de test** (31/35), **15.9 ms par phrase**. Retenue pour sa rapidité et sa faible consommation. **La piste B (petit LLM) n'a pas été testée** : elle reste un repli si la précision devient insuffisante (enrichir d'abord `emotions_data.py`).

### Phase 3 — Caméra n°1 (WPI408)
**Objectif** : image et vidéo fonctionnelles.
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

### Phase 4 — Alimentation et électronique du robot
**Objectif** : une alimentation fiable avant de brancher les servos.
1. Régler chaque convertisseur au multimètre (§5), sans charge.
2. Régler le DZS 12 A à **6,0 V** (servos DS3218MG : 4,8 à 6,8 V) et vérifier qu'il n'y a pas de pic à l'allumage. Alimentation de la Pi : LM2596 à 5,1 V pour les essais, convertisseur 5 V ≥ 5 A à terme.
3. Câbler fusible, interrupteur, condensateurs, masses communes (arbre du §5), fils rouges des servos directement sur les convertisseurs.
4. Mesurer la **consommation réelle** (wattmètre) : un servo seul, puis 3, 6 et 12, d'abord sans charge puis robot sur support. **Si ça approche 10 A, ajouter un 2e DZS 12 A** et répartir 6 servos par convertisseur.
- **Validation** : Pi alimentée par la batterie sans avertissement de sous-tension, tension des servos mesurée correcte.

### Phase 5 — Teensy : servos, IMU, ultrason + liaison Pi ↔ Teensy
**Objectif** : un firmware qui commande les servos, lit les capteurs et parle à la Pi.
1. **PCA9685** : VCC en 3,3 V depuis le Teensy, V+ sur l'alimentation des servos. Tester **un seul servo** avec la bibliothèque PCA9685 (Adafruit), pulses 500 à 2500 µs, 50 Hz.
2. **MPU6050** : I2C (SDA 18 / SCL 19), alimenté en 3,3 V. Calibrer les offsets du gyroscope au démarrage, appliquer un **filtre complémentaire ou Madgwick** pour obtenir roll et pitch. Pas de magnétomètre : le **yaw dérive**, ce qui n'est pas gênant pour tenir l'équilibre.
3. **HC-SR04** : alimenté en 5 V, TRIG en sortie, **ECHO via diviseur 1 kΩ / 2 kΩ** (§5).
4. Liaison série USB avec la Pi (`/dev/ttyACM0`, `pip install pyserial`) et **protocole simple** documenté dans `docs/protocole.md` (lignes ASCII au départ : commandes Pi → Teensy, mesures IMU et distance Teensy → Pi).
5. **Watchdog** : sans message de la Pi pendant X ms, retour à un état sûr.
- **Validation** : la Pi envoie une commande de servo, le Teensy renvoie l'IMU et la distance, et il coupe tout si on débranche la Pi.

### Phase 6 — Deuxième caméra et profondeur stéréo
**Objectif** : carte de profondeur utilisable à courte distance.
1. Choisir/acheter la 2e caméra (même modèle de préférence, voir §9) + 2e câble adaptateur.
2. Brancher sur l'autre connecteur (CAM0/CAM1), vérifier `rpicam-hello --list-cameras` (2 caméras), ouvrir avec `Picamera2(0)` et `Picamera2(1)`.
3. **Support rigide imprimé en 3D**, écart prévu **3-5 cm** (toute flexion fausse la calibration).
4. **Calibration** avec damier et OpenCV : `cv2.findChessboardCorners`, `cv2.stereoCalibrate`, `cv2.stereoRectify`. À refaire après tout changement mécanique.
5. Profondeur : `cv2.StereoSGBM_create` sur les images rectifiées, test à 0,5 / 1 / 1,5 / 2 m avec une distance mesurée au mètre.
6. Si le calcul est trop lourd sur la Pi : réduire la résolution (320×240 à 640×480) ou déporter sur le PC.
- Estimation (calcul théorique, **non mesurée**) : avec 4 cm d'écart, profondeur exploitable jusqu'à environ 2 m.
- **Validation** : erreur de distance acceptable à 1 m et 2 m, par rapport à une mesure réelle.

### Phase 7 — Détection et suivi d'une personne
**Objectif** : suivre une personne à distance constante.
1. Détecteur de personne (YOLO nano ou MediaPipe), sur le PC d'abord, puis sur la Pi si la fréquence d'images suffit.
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
| Transport PC → Pi | **TCP, port 5005**, lignes de texte UTF-8, réponse JSON | simple ; le serveur reçoit du texte quelle que soit l'origine (micro du PC ou, plus tard, micro de la Pi) |
| Reconnaissance vocale | **Vosk**, modèle `vosk-model-small-fr-0.22`, sur le PC | léger, français, temps réel ; Vosk local sur la Pi en phase 10 |
| Réseau de la Pi | NetworkManager : `Danielandjacobs` priorité 20, hotspot iPhone priorité 10 | bascule automatique selon le lieu |
| Ordre de dev | **émotions d'abord (phase 2 faite avant la phase 1, faute de buzzer), caméras ensuite** | pas encore de caméra stéréo, le buzzer est simple et motivant |
| Buzzer | **passif, sur un GPIO de la Pi**, avec gpiozero | émotions dans le code haut niveau, aucun protocole intermédiaire. Limite : Linux n'est pas temps réel, un son peut hoqueter si la Pi est très chargée |
| Sortie audio | **aucune** (buzzer seul) | choix de design, plus simple |
| Micro | **PC d'abord**, Pi à terme | pas de micro acheté pour l'instant |
| IMU | **MPU6050 sur le Teensy** | lecture rapide et régulière, sécurité indépendante de la Pi. Limites : pas de magnétomètre (yaw qui dérive), sensible aux vibrations (filtre nécessaire), copies bon marché de qualité variable |
| Contrôleur de servos | **PCA9685** en I2C, VCC en 3,3 V | PWM matérielle stable, pas de conversion de niveau |
| Alimentation des servos | **DS3218MG à 6,0 V** via DZS 12 A ; recommandé : 2 convertisseurs (6 servos chacun), fils rouges hors PCA9685 | 12 servos bloqués peuvent tirer 22 à 31 A (1,8 à 2,6 A chacun) contre 12 A max par convertisseur |
| Boucle de marche | sur le robot (Teensy ou Pi) | ne doit pas dépendre du wifi |
| Écart des caméras | prévu 3-5 cm | contrainte de taille de la tête |
| Inclinaison des caméras | **prévue 10-20° chacune**, recommandation **0-10° maximum** | une forte inclinaison réduit la zone vue par les deux caméras ; à trancher, rectifier avec `stereoRectify` |
| Type de caméra pour la stéréo | focale **fixe**, idéalement **global shutter**, champ **70-90°**, 640×480 à 1280×720 | l'autofocus fausse la calibration ; le rolling shutter se déforme avec les vibrations de la marche |
| WPI408 | utilisable pour tester ; 130° est large pour la stéréo | précision de profondeur réduite, plus de distorsion |
| Ultrason | sécurité, pas capteur principal | cône étroit, mal adapté aux tissus et surfaces obliques |
| RL | entraînement sur PC, politique embarquée | petit réseau, léger à exécuter |

---

## 10. Pièges connus

- **Pi 5** : connecteurs caméra de 22 broches (adaptateur nécessaire pour une nappe de 15 broches), pas de prise jack audio, 5 V / 5 A recommandés.
- **Wifi en déplacement** : le PC doit être sur le même réseau que la Pi ; `.local` peut ne pas marcher sur un hotspot de téléphone. **L'IP de la Pi change selon le réseau** : mettre à jour `HostName` (`.ssh\config`) et `PI_IP` (`config.py` du PC).
- **Teensy 4.0** : entrées/sorties en **3,3 V uniquement**.
- **PCA9685** : ne pas alimenter VCC en 5 V si l'I2C est relié au Teensy.
- **HC-SR04** : ECHO en 5 V, diviseur de tension obligatoire.
- **LM2596** : 2 A nominal / 3 A max, pas pour les servos. **DZS 12 A** : 12 A max seulement, alors que 12 servos DS3218MG bloqués en demandent 22 à 31 A.
- **Calibration stéréo** : à refaire si le support bouge ou si la mise au point change.
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

*(Ajouter ici une ligne par étape : date, ce qui a été fait, ce qui a marché ou non, commandes ou fichiers importants.)*

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
- Vosk (modèle français `vosk-model-small-fr-0.22`) et `sounddevice` (micro côté PC)

---

## 14. Notes pour le prochain agent IA (à jour au 2026-10-28)

- **Utilisateur** : Simon, PC **Windows** (PowerShell), débutant sur Linux/Pi : commandes courtes à copier ; **il accepte plusieurs étapes à la fois, mais toujours détaillées** ; lui demander le résultat exact avant de continuer.
- **Réseau** : la Pi est sur `Danielandjacobs` (IP `10.20.30.31`), hotspot iPhone en secours (IP vue le 2026-10-27 : `172.20.10.2`, `spot.local` ne s'y résolvait pas). Si l'IP change : `hostname -I` (via Raspberry Pi Connect si besoin), puis `HostName` dans `C:\Users\nomis\.ssh\config` et `PI_IP` dans `Spot\config.py`. Le hotspot iPhone est lent (~7 Ko/s vers certains dépôts).
- **Situation** : **Phases 0 et 2 terminées** (voir §2). Serveur d'émotions fonctionnel sur la Pi (port 5005), client vocal PC opérationnel (Vosk). `[?]` `vcgencmd get_throttled` à vérifier s'il ne l'a pas été ; `[?]` méthode de lancement permanent du serveur (à confirmer, `systemd` prévu en phase 10).
- **Matériel manquant** : le buzzer passif, un micro pour la Pi, la 2e caméra. Il a la Pi 5, la caméra WPI408 (non branchée à ce jour), les servos, la LiPo et les convertisseurs.
- **Ordre de développement** : la compréhension des phrases (Phase 2) a été faite **avant** le buzzer (Phase 1), faute de matériel. **Prochaines étapes au choix** : **Phase 3** (caméra WPI408 : brancher la nappe 22 → 15 broches **Pi éteinte**, `rpicam-hello --list-cameras`, `picamera2`) ; ou **Phase 1** dès réception du buzzer (`pi/emotions.py`, puis brancher `jouer(emotion)` sur `emotion_server.py`).
- **Phase 2, limites connues** : 88.6 % de précision sur 35 phrases (4 erreurs), piste B non testée. Pour améliorer : enrichir `pi/emotions_data.py` (phrases d'entraînement) avant de changer de modèle.
- **Interface entre modules** : le serveur renvoie le nom de l'émotion (un mot de la liste `content, triste, curieux, surpris, colere, peur, neutre`) en JSON ; `jouer(emotion)` le recevra.
- **Code PC** : l'utilisateur gère son dossier `C:\Users\nomis\Documents\Spot\` lui-même, hors dépôt Git. **Ne pas tenter de le commiter ou de le transférer depuis la Pi.**
- **Consigne de l'utilisateur sur ce README** : ne pas le réécrire en entier. Modifier uniquement les parties qui changent et ajouter ici (fin du fichier) les infos importantes pour l'agent suivant.
