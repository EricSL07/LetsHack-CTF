import argparse
import subprocess
import logging
import os
import sys
import json
import ipaddress

# Diretório base para armazenar dados da ferramenta
BASE_DIRECTORY = os.path.expanduser("~/.lth")

# Arquivo onde a ferramenta vai guardar a memória dos alvos
REGISTRY_FILE = os.path.join(BASE_DIRECTORY, "targets.json")

# --- GERENCIAMENTO DE ESTADO ---

def is_valid_ip(ip_str):
    """Verifica se a string é um endereço IPv4 ou IPv6 válido."""
    try:
        ipaddress.ip_address(ip_str)
        return True
    except ValueError:
        return False

def load_registry():
    """Carrega o banco de dados de alvos conhecidos."""
    if os.path.exists(REGISTRY_FILE):
        with open(REGISTRY_FILE, "r") as file:
            return json.load(file)
    return {}

def save_registry(data):
    """Salva o dicionário no arquivo JSON."""
    with open(REGISTRY_FILE, "w") as file:
        json.dump(data, file, indent=4)

def resolve_target(target_input):
    """Descobre quem é o alvo, permitindo que o usuário digite o IP ou o Nome."""
    registry = load_registry()
    
    # 1. Tenta buscar pelo nome (ex: "maquina-alvo")
    if target_input in registry:
        return target_input, registry[target_input]["ip"]
    
    # 2. Tenta buscar pelo IP (ex: "10.10.10.5")
    for name, data in registry.items():
        if data["ip"] == target_input:
            return name, data["ip"]
            
    return None, None

# --- FUNÇÕES CORE ---

def check_privileges():
    if os.geteuid() != 0:
        logging.warning("Elevando privilégios via sudo...")
        os.execvp("sudo", ["sudo", sys.executable] + sys.argv)

def start_setup(ip, name):
    target_dir = os.path.join(BASE_DIRECTORY, name)
    
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
        logging.info(f"Diretório criado: {target_dir}")
    
    # Atualiza o arquivo de estado JSON
    registry = load_registry()
    registry[name] = {"ip": ip, "dir": target_dir}
    save_registry(registry)
    
    return target_dir

def add_to_etc_hosts(ip, name):
    hosts_file = "/etc/hosts"
    entry = f"{ip}\t{name}\n"
    
    with open(hosts_file, "r") as file:
        if any(ip in line or name in line for line in file):
            logging.info(f"Alvo {name} já está no /etc/hosts.")
            return

    with open(hosts_file, "a") as file:
        file.write(entry)
    logging.info(f"Alvo adicionado ao /etc/hosts: {ip} -> {name}")

def run_enum(ip, name):
    # Recalcula o diretório baseado no nome
    target_dir = os.path.join(BASE_DIRECTORY, name)
    output_file = os.path.join(target_dir, f"nmap_{ip}.txt")

    logging.info(f"Iniciando enumeração em {name} ({ip})")
    nmap_command = ["nmap", "-sV", "-T4", "-oN", output_file, ip]

    try:
        subprocess.run(nmap_command, capture_output=True, text=True, check=True)
        logging.info(f"Scan concluído! Resultados em: {output_file}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Erro ao executar o nmap: {e}")

class CustomArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        sys.exit(2)

# --- INTERFACE CLI ---

def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
    
    # Cria o diretório base se não existir (necessário para salvar o targets.json na primeira vez)
    if not os.path.exists(BASE_DIRECTORY):
        os.makedirs(BASE_DIRECTORY)

    parser = CustomArgumentParser(description="LTH - Canivete Suíço para CTFs")
    # Dest="command" cria uma variável args.command que guarda qual subcomando foi chamado
    subparsers = parser.add_subparsers(dest="command", required=True, parser_class=CustomArgumentParser)

    # Subcomando: ADD (Adiciona o alvo ao banco de dados e /etc/hosts)
    parser_add = subparsers.add_parser("add", help="Registra um novo alvo e prepara o ambiente")
    parser_add.add_argument("ip", help="IP do alvo")
    parser_add.add_argument("name", help="Nome da máquina")

    # Subcomando: SCAN (Roda o Nmap buscando pelo IP ou Nome)
    parser_scan = subparsers.add_parser("scan", help="Inicia enumeração em um alvo conhecido")
    parser_scan.add_argument("target", help="IP ou Nome do alvo já registrado")

    args = parser.parse_args()

    # Roteamento da Lógica
    if args.command == "add":
        if not is_valid_ip(args.ip):
            logging.error(f"IP inválido '{args.ip}'. Por favor, forneça um endereço IP (IPv4/IPv6) válido.")
            sys.exit(1)
        check_privileges()
        start_setup(args.ip, args.name)
        add_to_etc_hosts(args.ip, args.name)
        logging.info("Setup concluído. Você já pode rodar 'lth scan <nome>'")
        
    elif args.command == "scan":
        name, ip = resolve_target(args.target)
        
        if not name:
            logging.error(f"Alvo '{args.target}' não encontrado. Use 'lth add <ip> <nome>' primeiro.")
            sys.exit(1)
            
        check_privileges()
        run_enum(ip, name)

if __name__ == "__main__":
    main()