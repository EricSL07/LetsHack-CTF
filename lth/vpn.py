"""
OpenVPN Lifecycle and Network Interface Management Module for LTH

This module provides functions to:
- Retrieve assigned IPv4 address on the `tun0` virtual network interface
- Start an OpenVPN daemon process, saving default .ovpn profiles
- Monitor connection initialization and IP allocation
- Check connection status (PID state + interface presence)
- Gracefully stop active OpenVPN background processes
"""

import os
import sys
import time
import shutil
import logging
import subprocess
from typing import Optional
from lth.config import VPN_PID_FILE, VPN_LOG_FILE, DEFAULT_VPN_FILE


def get_tun0_ip() -> Optional[str]:
    """
    Retrieve the current IPv4 address assigned to the `tun0` network interface.

    Returns:
        Optional[str]: IP address string if `tun0` is active and has an IPv4 address assigned,
                       or None if interface is down / not found.
    """
    try:
        output = subprocess.check_output(
            ["ip", "-4", "addr", "show", "dev", "tun0"],
            text=True,
            stderr=subprocess.DEVNULL
        )
        for line in output.splitlines():
            line = line.strip()
            if line.startswith("inet "):
                # Line format: "inet 10.10.14.5/24 scope global tun0"
                return line.split()[1].split('/')[0]
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return None 


def start_vpn(ovpn_path: Optional[str] = None) -> None:
    """
    Start the OpenVPN daemon background process using a specified or saved configuration file.

    Args:
        ovpn_path (Optional[str]): Path to .ovpn profile file. If provided, copies it to
                                    `~/.lth/default.ovpn` for default future connections.
    """
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

    # Check if a VPN process is already running via PID file validation
    if os.path.exists(VPN_PID_FILE):
        with open(VPN_PID_FILE, "r", encoding="utf-8") as f:
            pid = f.read().strip()
        if pid and os.path.exists(f"/proc/{pid}"):
            logging.warning(f"VPN já está rodando (PID: {pid}). Use 'lth vpn stop' para desconectar.")
            return
        else:
            # Stale PID file; clean it up
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
        logging.info("VPN iniciada em segundo plano. Aguardando atribuição da interface tun0...")
        
        # Poll up to 10 seconds for tun0 interface IP allocation
        for _ in range(10):
            time.sleep(1)
            ip = get_tun0_ip()
            if ip:
                logging.info(f"VPN conectada com sucesso! Seu IP (tun0): {ip}")
                return
        logging.warning("VPN iniciada, mas o IP tun0 ainda não foi atribuído.")
    except subprocess.CalledProcessError as e:
        logging.error(f"Erro ao iniciar a VPN: {e}")


def vpn_status() -> None:
    """
    Check and report the current status of the VPN connection.
    Displays whether the PID process is running and whether `tun0` IP is assigned.
    """
    ip = get_tun0_ip()
    pid_exists = os.path.exists(VPN_PID_FILE)
    pid = None

    if pid_exists:
        with open(VPN_PID_FILE, "r", encoding="utf-8") as f:
            pid = f.read().strip()
        # Verify process actually exists under /proc/<pid>
        if not (pid and os.path.exists(f"/proc/{pid}")):
            pid_exists = False

    if pid_exists:
        logging.info(f"STATUS: Conectado (PID: {pid}) | IP tun0: {ip}" if ip else f"STATUS: Processo VPN ativo (PID: {pid}), sem IP.")
    else:
        logging.info(f"STATUS: Interface tun0 ativa (IP: {ip}), não gerenciada." if ip else "STATUS: Desconectado.")


def stop_vpn() -> None:
    """
    Gracefully terminate the running OpenVPN process using SIGTERM (kill -15).
    Removes the PID tracking file after process termination.
    """
    if not os.path.exists(VPN_PID_FILE):
        ip = get_tun0_ip()
        logging.warning("PID não encontrado, mas tun0 ativa." if ip else "Nenhuma VPN ativa para desconectar.")
        return

    with open(VPN_PID_FILE, "r", encoding="utf-8") as f:
        pid = f.read().strip()

    if pid and os.path.exists(f"/proc/{pid}"):
        try:
            # Send SIGTERM signal to OpenVPN daemon
            subprocess.run(["sudo", "kill", "-15", pid], check=True)
            logging.info(f"Sinal enviado para a VPN (PID: {pid}).")
            
            # Wait up to 5 seconds for process termination
            for _ in range(5):
                time.sleep(1)
                if not os.path.exists(f"/proc/{pid}"):
                    break
        except Exception as e:
            logging.error(f"Erro ao encerrar a VPN: {e}")

    # Remove PID tracking file
    if os.path.exists(VPN_PID_FILE):
        os.remove(VPN_PID_FILE)
    logging.info("VPN desconectada.")