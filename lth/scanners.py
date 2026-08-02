"""
Target Management and Scanning Automation Module for LTH

This module provides tools for:
- Environment setup and target directory creation under ~/.lth/<target_name>
- Automatic /etc/hosts DNS mapping using sudo
- Parallel web vulnerability & directory enumeration (Nikto + Gobuster)
- Automated network port scanning (Nmap) and open port parsing
"""

import os
import logging
import subprocess
from typing import List, Tuple
from concurrent.futures import ThreadPoolExecutor
from lth.config import BASE_DIRECTORY, load_registry, save_registry


def start_setup(ip: str, name: str) -> str:
    """
    Prepare the environment for a target machine.
    Creates a target output directory under ~/.lth/<name> and registers the entry in targets.json.

    Args:
        ip (str): IP address of the target machine.
        name (str): Friendly hostname/name of the target machine.

    Returns:
        str: Absolute path to the target's output directory.
    """
    target_dir = os.path.join(BASE_DIRECTORY, name)
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
        logging.info(f"Diretório criado: {target_dir}")
    
    registry = load_registry()
    registry[name] = {"ip": ip, "dir": target_dir}
    save_registry(registry)
    return target_dir


def add_to_etc_hosts(ip: str, name: str) -> None:
    """
    Append target host mapping (IP -> Name) to /etc/hosts if not already present.
    Uses `sudo tee -a /etc/hosts` to safely append entry.

    Args:
        ip (str): Target IP address.
        name (str): Target hostname/domain to map.
    """
    hosts_file = "/etc/hosts"
    entry = f"{ip}\t{name}\n"
    
    # Check if target entry or IP already exists in /etc/hosts
    with open(hosts_file, "r", encoding="utf-8") as file:
        if any(ip in line or name in line for line in file):
            logging.info(f"Alvo {name} já está no /etc/hosts.")
            return

    try:
        # Use sudo tee -a to append host entry without overwriting system file permissions
        cmd = ["sudo", "tee", "-a", hosts_file]
        subprocess.run(cmd, input=entry, text=True, capture_output=True, check=True)
        logging.info(f"Alvo adicionado ao /etc/hosts: {ip} -> {name}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Erro ao adicionar ao /etc/hosts: {e}")


def run_nikto(ip: str, output_file: str) -> None:
    """
    Execute Nikto web server scanner against the target IP.

    Args:
        ip (str): Target IP address.
        output_file (str): File path to save Nikto scan output.
    """
    logging.info(f"Iniciando scan com Nikto em {ip}...")
    try:
        subprocess.run(["nikto", "-h", ip, "-output", output_file], check=True)
        logging.info(f"Nikto concluído! Resultados em: {output_file}")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logging.error(f"Erro no Nikto: {e}")


def run_gobuster(ip: str, output_file: str) -> None:
    """
    Execute Gobuster directory brute-force enumeration against target HTTP service.
    Uses standard wordlist /usr/share/wordlists/dirb/common.txt.

    Args:
        ip (str): Target IP address.
        output_file (str): File path to save Gobuster directory scan output.
    """
    logging.info(f"Iniciando scan com Gobuster em {ip}...")
    try:
        cmd = [
            "gobuster", "dir",
            "-u", f"http://{ip}",
            "-w", "/usr/share/wordlists/dirb/common.txt",
            "-o", output_file
        ]
        subprocess.run(cmd, check=True)
        logging.info(f"Gobuster concluído! Resultados em: {output_file}")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logging.error(f"Erro no Gobuster: {e}")


def run_webscan(ip: str, name: str) -> None:
    """
    Execute web scanners (Nikto and Gobuster) concurrently using a ThreadPoolExecutor.

    Args:
        ip (str): Target IP address.
        name (str): Target name used to identify the target output directory.
    """
    target_dir = os.path.join(BASE_DIRECTORY, name)
    nikto_out = os.path.join(target_dir, f"nikto_{ip}.txt")
    gobuster_out = os.path.join(target_dir, f"gobuster_{ip}.txt")

    logging.info(f"Iniciando scans web em paralelo para {name} ({ip})...")
    with ThreadPoolExecutor(max_workers=2) as executor:
        executor.submit(run_nikto, ip, nikto_out)
        executor.submit(run_gobuster, ip, gobuster_out)


def detect_ports(output_file: str) -> List[Tuple[str, str]]:
    """
    Parse an Nmap output file (-oN format) to extract open TCP ports and service names.

    Args:
        output_file (str): Path to Nmap output file.

    Returns:
        List[Tuple[str, str]]: List of (port_number, service_name) tuples for open TCP ports.
    """
    if not os.path.exists(output_file):
        return []
    ports = []
    with open(output_file, "r", encoding="utf-8") as f:
        for line in f:
            if "/tcp" in line and "open" in line:
                parts = line.split()
                port = parts[0].split("/")[0]
                service = parts[2] if len(parts) > 2 else "unknown"
                ports.append((port, service))
    return ports


def run_nmap(ip: str, name: str) -> None:
    """
    Execute Nmap service detection scan (`sudo nmap -sV -T4 -oN ...`) on target.
    Parses open ports and prompts user to trigger automated webscan if HTTP (port 80) is open.

    Args:
        ip (str): Target IP address.
        name (str): Target name for output file management.
    """
    target_dir = os.path.join(BASE_DIRECTORY, name)
    output_file = os.path.join(target_dir, f"nmap_{ip}.txt")

    logging.info(f"Iniciando nmap em {name} ({ip})")
    try:
        subprocess.run(["sudo", "nmap", "-sV", "-T4", "-oN", output_file, ip], check=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"Erro no Nmap: {e}")

    ports = detect_ports(output_file)
    if ports:
        logging.info(f"Portas abertas: {ports}")
        # Prompt user if HTTP port 80 is active
        if any(port == "80" for port, _ in ports):
            if input("Porta 80 aberta! Rodar webscan agora? (s/n): ").strip().lower() == 's':
                run_webscan(ip, name)