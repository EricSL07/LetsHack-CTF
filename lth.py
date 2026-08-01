import argparse
import subprocess
import logging
import os
import sys
import json
import ipaddress
import time
import shutil

# Diretório base para armazenar dados da ferramenta (sempre na home do usuário comum)
BASE_DIRECTORY = os.path.expanduser("~/.lth")

# Arquivo onde a ferramenta vai guardar a memória dos alvos
REGISTRY_FILE = os.path.join(BASE_DIRECTORY, "targets.json")

# Arquivos de controle da VPN
VPN_PID_FILE = os.path.join(BASE_DIRECTORY, "openvpn.pid")
VPN_LOG_FILE = os.path.join(BASE_DIRECTORY, "openvpn.log")
DEFAULT_VPN_FILE = os.path.join(BASE_DIRECTORY, "default.ovpn")

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

# --- GERENCIAMENTO DE VPN ---

def get_tun0_ip():
    """Extrai o endereço IPv4 da interface tun0, se ativa."""
    try:
        output = subprocess.check_output(["ip", "-4", "addr", "show", "dev", "tun0"], text=True, stderr=subprocess.DEVNULL)
        for line in output.splitlines():
            line = line.strip()
            if line.startswith("inet "):
                return line.split()[1].split('/')[0]
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return None 

def start_vpn(ovpn_path=None):
    """Inicia o OpenVPN em modo daemon (segundo plano) via sudo."""
    if ovpn_path:
        if not os.path.exists(ovpn_path):
            logging.error(f"Arquivo OVPN não encontrado: {ovpn_path}")
            sys.exit(1)
        abs_ovpn_path = os.path.abspath(ovpn_path)
        shutil.copyfile(abs_ovpn_path, DEFAULT_VPN_FILE)
        logging.info(f"VPN '{abs_ovpn_path}' definida e salva como padrão em ~/.lth/default.ovpn")
        target_ovpn = DEFAULT_VPN_FILE
    else:
        if not os.path.exists(DEFAULT_VPN_FILE):
            logging.error("Nenhum arquivo OVPN fornecido e nenhuma VPN padrão cadastrada.")
            logging.error("Forneça o arquivo na primeira execução: 'lth vpn start <arquivo.ovpn>'")
            sys.exit(1)
        target_ovpn = DEFAULT_VPN_FILE
        logging.info("Usando VPN padrão (~/.lth/default.ovpn)...")

    if os.path.exists(VPN_PID_FILE):
        with open(VPN_PID_FILE, "r") as f:
            pid = f.read().strip()
        if pid and os.path.exists(f"/proc/{pid}"):
            logging.warning(f"VPN já está rodando (PID: {pid}). Use 'lth vpn stop' para desconectar.")
            return
        else:
            os.remove(VPN_PID_FILE)

    logging.info(f"Iniciando VPN com {target_ovpn}...")

    cmd = [
        "sudo", "openvpn",
        "--config", target_ovpn,
        "--writepid", VPN_PID_FILE,
        "--log", VPN_LOG_FILE,
        "--daemon"
    ]

    try:
        subprocess.run(cmd, check=True)
        logging.info("VPN iniciada em segundo plano.")
        logging.info("Aguardando atribuição da interface tun0...")

        for _ in range(10):
            time.sleep(1)
            ip = get_tun0_ip()
            if ip:
                logging.info(f"VPN conectada com sucesso! Seu IP (tun0): {ip}")
                return

        logging.warning("VPN iniciada, mas o IP tun0 ainda não foi atribuído. Verifique o log em ~/.lth/openvpn.log")
    except subprocess.CalledProcessError as e:
        logging.error(f"Erro ao iniciar a VPN: {e}")
    except FileNotFoundError:
        logging.error("O utilitário 'openvpn' ou 'sudo' não foi encontrado no sistema.")

def vpn_status():
    """Exibe o status da conexão VPN e o IP tun0."""
    ip = get_tun0_ip()
    pid_exists = os.path.exists(VPN_PID_FILE)
    pid = None

    if pid_exists:
        with open(VPN_PID_FILE, "r") as f:
            pid = f.read().strip()
        if not (pid and os.path.exists(f"/proc/{pid}")):
            pid_exists = False

    if pid_exists:
        if ip:
            logging.info(f"STATUS: Conectado (PID: {pid}) | IP tun0: {ip}")
        else:
            logging.warning(f"STATUS: Processo VPN ativo (PID: {pid}), mas tun0 ainda não obteve IP.")
    else:
        if ip:
            logging.info(f"STATUS: Interface tun0 ativa (IP: {ip}), mas não foi gerenciada pelo LTH.")
        else:
            logging.info("STATUS: Desconectado.")

def stop_vpn():
    """Encerra graciosamente o processo OpenVPN via sudo."""
    if not os.path.exists(VPN_PID_FILE):
        ip = get_tun0_ip()
        if ip:
            logging.warning("PID da VPN não encontrado em ~/.lth/openvpn.pid, mas a interface tun0 está ativa.")
        else:
            logging.info("Nenhuma VPN ativa para desconectar.")
        return

    with open(VPN_PID_FILE, "r") as f:
        pid = f.read().strip()

    if pid and os.path.exists(f"/proc/{pid}"):
        try:
            subprocess.run(["sudo", "kill", "-15", pid], check=True)
            logging.info(f"Sinal de encerramento enviado para a VPN (PID: {pid}).")
            for _ in range(5):
                time.sleep(1)
                if not os.path.exists(f"/proc/{pid}"):
                    break
        except Exception as e:
            logging.error(f"Erro ao encerrar a VPN: {e}")
    else:
        logging.warning("Processo da VPN não encontrado em execução.")

    if os.path.exists(VPN_PID_FILE):
        os.remove(VPN_PID_FILE)
    logging.info("VPN desconectada.")

# --- FUNÇÕES CORE ---

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

    try:
        cmd = ["sudo", "tee", "-a", hosts_file]
        subprocess.run(cmd, input=entry, text=True, capture_output=True, check=True)
        logging.info(f"Alvo adicionado ao /etc/hosts: {ip} -> {name}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Erro ao adicionar ao /etc/hosts: {e}")

def run_nmap(ip, name):
    target_dir = os.path.join(BASE_DIRECTORY, name)
    output_file = os.path.join(target_dir, f"nmap_{ip}.txt")

    logging.info(f"Iniciando scan com o nmap em {name} ({ip})")
    nmap_command = ["sudo", "nmap", "-sV", "-T4", "-oN", output_file, ip]

    try:
        subprocess.run(nmap_command, check=True)
        logging.info(f"Scan concluído! Resultados em: {output_file}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Erro ao executar o nmap: {e}")

    detect_ports(output_file)

def detect_ports(output_file):
    if not os.path.exists(output_file):
        return
    ports = []
    with open(output_file, "r") as f:
        content = f.read()

    for line in content.splitlines():
        if "/tcp" in line and "open" in line:
            parts = line.split()
            port = parts[0].split("/")[0]
            service = parts[2] if len(parts) > 2 else "unknown"
            ports.append((port, service))

    if ports:
        logging.info(f"Portas abertas encontradas: {ports}")

class CustomArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        self.print_help(sys.stderr)
        sys.exit(2)

# --- INTERFACE CLI ---

def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
    
    # Cria o diretório base se não existir (necessário para salvar o targets.json na primeira vez)
    if not os.path.exists(BASE_DIRECTORY):
        os.makedirs(BASE_DIRECTORY)

    prog_name = os.path.basename(sys.argv[0])
    if prog_name.endswith(".py"):
        prog_name = prog_name[:-3]

    parser = CustomArgumentParser(prog=prog_name, description="LTH - Canivete Suíço para CTFs")
    # Dest="command" cria uma variável args.command que guarda qual subcomando foi chamado
    subparsers = parser.add_subparsers(dest="command", required=True, parser_class=CustomArgumentParser)

    # Subcomando: ADD (Adiciona o alvo ao banco de dados e /etc/hosts)
    parser_add = subparsers.add_parser("add", help="Registra um novo alvo e prepara o ambiente")
    parser_add.add_argument("ip", help="IP do alvo")
    parser_add.add_argument("name", help="Nome da máquina")

    # Subcomando: SCAN (Roda o Nmap buscando pelo IP ou Nome)
    parser_scan = subparsers.add_parser("scan", help="Inicia enumeração em um alvo conhecido")
    parser_scan.add_argument("target", help="IP ou Nome do alvo já registrado")

    # Subcomando: VPN (Gerencia a conexão OpenVPN)
    parser_vpn = subparsers.add_parser("vpn", help="Gerencia a conexão OpenVPN (start, stop, status)")
    vpn_subparsers = parser_vpn.add_subparsers(dest="vpn_action", required=True, parser_class=CustomArgumentParser)

    # Subcomando: vpn start
    parser_vpn_start = vpn_subparsers.add_parser("start", help="Inicia a conexão VPN (usa o padrão se nenhum arquivo for fornecido)")
    parser_vpn_start.add_argument("file", nargs="?", default=None, help="Caminho para o arquivo .ovpn (opcional se já houver um padrão salvo)")

    # Subcomando: vpn stop
    parser_vpn_stop = vpn_subparsers.add_parser("stop", help="Desconecta a VPN ativa")

    # Subcomando: vpn status
    parser_vpn_status = vpn_subparsers.add_parser("status", help="Verifica o status da VPN e o IP da interface tun0")

    args = parser.parse_args()

    # Roteamento da Lógica
    if args.command == "add":
        if not is_valid_ip(args.ip):
            logging.error(f"IP inválido '{args.ip}'. Por favor, forneça um endereço IP (IPv4/IPv6) válido.")
            sys.exit(1)
        start_setup(args.ip, args.name)
        add_to_etc_hosts(args.ip, args.name)
        logging.info("Setup concluído. Você já pode rodar 'lth scan <nome>'")
        
    elif args.command == "scan":
        name, ip = resolve_target(args.target)
        
        if not name:
            logging.error(f"Alvo '{args.target}' não encontrado. Use 'lth add <ip> <nome>' primeiro.")
            sys.exit(1)
            
        run_nmap(ip, name)

    elif args.command == "vpn":
        if args.vpn_action == "start":
            start_vpn(args.file)
        elif args.vpn_action == "stop":
            stop_vpn()
        elif args.vpn_action == "status":
            vpn_status()

if __name__ == "__main__":
    main()