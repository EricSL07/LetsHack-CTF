import os
import logging
import subprocess
from concurrent.futures import ThreadPoolExecutor
from lth.config import BASE_DIRECTORY, load_registry, save_registry

def start_setup(ip: str, name: str) -> str:
    target_dir = os.path.join(BASE_DIRECTORY, name)
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
        logging.info(f"Diretório criado: {target_dir}")
    
    registry = load_registry()
    registry[name] = {"ip": ip, "dir": target_dir}
    save_registry(registry)
    return target_dir

def add_to_etc_hosts(ip: str, name: str):
    hosts_file = "/etc/hosts"
    entry = f"{ip}\t{name}\n"
    
    with open(hosts_file, "r") as file:
        if any(ip in line or name in line for line in file):
            logging.info(f"Alvo {name} já está no /etc/hosts.")
            return

    try:
        cmd = ["sudo", "tee", "-a", hosts_file]
        subprocess.run(cmd, input=entry, text=True, capture_output=True, check=True)
        logging.info(f"Alvo adicionado ao /etc/hosts: {ip} -> {name}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Erro ao adicionar ao /etc/hosts: {e}")

def run_nikto(ip: str, output_file: str):
    logging.info(f"Iniciando scan com Nikto em {ip}...")
    try:
        subprocess.run(["nikto", "-h", ip, "-output", output_file], check=True)
        logging.info(f"Nikto concluído! Resultados em: {output_file}")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logging.error(f"Erro no Nikto: {e}")

def run_gobuster(ip: str, output_file: str):
    logging.info(f"Iniciando scan com Gobuster em {ip}...")
    try:
        cmd = ["gobuster", "dir", "-u", f"http://{ip}", "-w", "/usr/share/wordlists/dirb/common.txt", "-o", output_file]
        subprocess.run(cmd, check=True)
        logging.info(f"Gobuster concluído! Resultados em: {output_file}")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logging.error(f"Erro no Gobuster: {e}")

def run_webscan(ip: str, name: str):
    target_dir = os.path.join(BASE_DIRECTORY, name)
    nikto_out = os.path.join(target_dir, f"nikto_{ip}.txt")
    gobuster_out = os.path.join(target_dir, f"gobuster_{ip}.txt")

    logging.info(f"Iniciando scans web em paralelo para {name} ({ip})...")
    with ThreadPoolExecutor(max_workers=2) as executor:
        executor.submit(run_nikto, ip, nikto_out)
        executor.submit(run_gobuster, ip, gobuster_out)

def detect_ports(output_file: str):
    if not os.path.exists(output_file):
        return []
    ports = []
    with open(output_file, "r") as f:
        for line in f:
            if "/tcp" in line and "open" in line:
                parts = line.split()
                port = parts[0].split("/")[0]
                service = parts[2] if len(parts) > 2 else "unknown"
                ports.append((port, service))
    return ports

def run_nmap(ip: str, name: str):
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
        if any(port == "80" for port, _ in ports):
            if input("Porta 80 aberta! Rodar webscan agora? (s/n): ").strip().lower() == 's':
                run_webscan(ip, name)