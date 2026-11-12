# -*- coding: utf-8 -*-
import pybullet as p
import pybullet_data
import time

# 1. Connexion au moteur physique
physicsClient = p.connect(p.GUI)
p.setAdditionalSearchPath(pybullet_data.getDataPath())
p.setGravity(0, 0, -9.81)

# 2. Charger le sol et le robot
planeId = p.loadURDF("plane.urdf")
robotStartPos = [0, 0, 0.25]
robotStartOrientation = p.getQuaternionFromEuler([0, 0, 0])

robotId = p.loadURDF("spot_micro.urdf", robotStartPos, robotStartOrientation)

print("[OK] Robot charge avec succes. ID:", robotId)
print("Nombre d articulations detectees:", p.getNumJoints(robotId))

# 3. Boucle de simulation (1000 pas de temps)
for i in range(1000):
    p.stepSimulation()
    time.sleep(1.0 / 240.0)

p.disconnect()
