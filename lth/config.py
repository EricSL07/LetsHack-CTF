import os
import json
import ipaddress

BASE_DIRECTORY = os.path.expanduser("~/.lth")
REGISTRY_FILE = os.path.join(BASE_DIRECTORY, "targets.json")
VPN_PID_FILE = os.path.join(BASE_DIRECTORY, "openvpn.pid")
VPN_LOG_FILE = os.path.join(BASE_DIRECTORY, "openvpn.log")
DEFAULT_VPN_FILE = os.path.join(BASE_DIRECTORY, "default.ovpn")

def ensure_base_dir():
    if not os.path.exists(BASE_DIRECTORY):
        os.makedirs(BASE_DIRECTORY)

def is_valid_ip(ip_str: str) -> bool:
    try:
        ipaddress.ip_address(ip_str)
        return True
    except ValueError:
        return False

def load_registry() -> dict:
    if os.path.exists(REGISTRY_FILE):
        with open(REGISTRY_FILE, "r") as file:
            return json.load(file)
    return {}

def save_registry(data: dict) -> None:
    ensure_base_dir()
    with open(REGISTRY_FILE, "w") as file:
        json.dump(data, file, indent=4)

def resolve_target(target_input: str):
    registry = load_registry()
    if target_input in registry:
        return target_input, registry[target_input]["ip"]
    for name, data in registry.items():
        if data["ip"] == target_input:
            return name, data["ip"]
    return None, None