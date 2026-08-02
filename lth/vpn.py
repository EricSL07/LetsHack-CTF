import os
import sys
import time
import shutil
import logging
import subprocess
from lth.config import VPN_PID_FILE, VPN_LOG_FILE, DEFAULT_VPN_FILE

def get_tun0_ip():
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
    cmd = ["sudo", "openvpn", "--config", target_ovpn, "--writepid", VPN_PID_FILE, "--log", VPN_LOG_FILE, "--daemon"]

    try:
        subprocess.run(cmd, check=True)
        logging.info("VPN iniciada em segundo plano. Aguardando atribuição da interface tun0...")
        for _ in range(10):
            time.sleep(1)
            ip = get_tun0_ip()
            if ip:
                logging.info(f"VPN conectada com sucesso! Seu IP (tun0): {ip}")
                return
        logging.warning("VPN iniciada, mas o IP tun0 ainda não foi atribuído.")
    except subprocess.CalledProcessError as e:
        logging.error(f"Erro ao iniciar a VPN: {e}")

def vpn_status():
    ip = get_tun0_ip()
    pid_exists = os.path.exists(VPN_PID_FILE)
    pid = None

    if pid_exists:
        with open(VPN_PID_FILE, "r") as f:
            pid = f.read().strip()
        if not (pid and os.path.exists(f"/proc/{pid}")):
            pid_exists = False

    if pid_exists:
        logging.info(f"STATUS: Conectado (PID: {pid}) | IP tun0: {ip}" if ip else f"STATUS: Processo VPN ativo (PID: {pid}), sem IP.")
    else:
        logging.info(f"STATUS: Interface tun0 ativa (IP: {ip}), não gerenciada." if ip else "STATUS: Desconectado.")

def stop_vpn():
    if not os.path.exists(VPN_PID_FILE):
        ip = get_tun0_ip()
        logging.warning("PID não encontrado, mas tun0 ativa." if ip else "Nenhuma VPN ativa para desconectar.")
        return

    with open(VPN_PID_FILE, "r") as f:
        pid = f.read().strip()

    if pid and os.path.exists(f"/proc/{pid}"):
        try:
            subprocess.run(["sudo", "kill", "-15", pid], check=True)
            logging.info(f"Sinal enviado para a VPN (PID: {pid}).")
            for _ in range(5):
                time.sleep(1)
                if not os.path.exists(f"/proc/{pid}"):
                    break
        except Exception as e:
            logging.error(f"Erro ao encerrar a VPN: {e}")

    if os.path.exists(VPN_PID_FILE):
        os.remove(VPN_PID_FILE)
    logging.info("VPN desconectada.")