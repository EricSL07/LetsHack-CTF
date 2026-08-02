"""
Configuration and Persistence Module for LTH

This module defines global paths, handles file system initialization (under ~/.lth),
validates IP addresses, and manages the JSON target registry.
"""

import os
import json
import ipaddress
from typing import Tuple, Optional, Dict, Any

# Base working directory for LTH data storage (~/.lth)
BASE_DIRECTORY: str = os.path.expanduser("~/.lth")

# Path to the target registry JSON file
REGISTRY_FILE: str = os.path.join(BASE_DIRECTORY, "targets.json")

# OpenVPN process management files
VPN_PID_FILE: str = os.path.join(BASE_DIRECTORY, "openvpn.pid")
VPN_LOG_FILE: str = os.path.join(BASE_DIRECTORY, "openvpn.log")
DEFAULT_VPN_FILE: str = os.path.join(BASE_DIRECTORY, "default.ovpn")


def ensure_base_dir() -> None:
    """
    Ensure that the base LTH directory (~/.lth) exists.
    Creates directory recursively if it does not exist.
    """
    if not os.path.exists(BASE_DIRECTORY):
        os.makedirs(BASE_DIRECTORY)


def is_valid_ip(ip_str: str) -> bool:
    """
    Validate whether a given string is a valid IPv4 or IPv6 address.

    Args:
        ip_str (str): The IP address string to validate.

    Returns:
        bool: True if valid IP address, False otherwise.
    """
    try:
        ipaddress.ip_address(ip_str)
        return True
    except ValueError:
        return False


def load_registry() -> Dict[str, Any]:
    """
    Load registered targets from the JSON registry file (~/.lth/targets.json).

    Returns:
        Dict[str, Any]: Dictionary mapping target names to target metadata (IP, directory path).
    """
    if os.path.exists(REGISTRY_FILE):
        with open(REGISTRY_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    return {}


def save_registry(data: Dict[str, Any]) -> None:
    """
    Save the target registry dictionary into the JSON registry file (~/.lth/targets.json).

    Args:
        data (Dict[str, Any]): Dictionary of target names and metadata to persist.
    """
    ensure_base_dir()
    with open(REGISTRY_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)


def resolve_target(target_input: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Resolve a target identifier (either target name or IP address) to (name, ip).

    Args:
        target_input (str): Target name (e.g. 'lame') or IP address (e.g. '10.10.10.3').

    Returns:
        Tuple[Optional[str], Optional[str]]: Tuple containing (target_name, target_ip) if found,
                                            or (None, None) if not registered.
    """
    registry = load_registry()
    
    # Check direct match by target name
    if target_input in registry:
        return target_input, registry[target_input]["ip"]
    
    # Check match by IP address lookup
    for name, data in registry.items():
        if data.get("ip") == target_input:
            return name, data["ip"]
            
    return None, None