import os

# Configuration réseau du PC vers la Raspberry Pi
PI_IP = os.environ.get("SPOT_PI_IP", "192.168.1.28")
PORT = int(os.environ.get("SPOT_PI_PORT", "5005"))
