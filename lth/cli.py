"""
Command-Line Interface (CLI) Module for LTH

This module parses command-line arguments and dispatches commands to:
- Register new CTF target machines (`add`)
- Perform network scans (`scan`)
- Perform parallel web scans (`webscan`)
- Control OpenVPN connection state (`vpn start|stop|status`)
"""

import sys
import argparse
import logging
import os
from lth.config import is_valid_ip, resolve_target, ensure_base_dir
from lth.scanners import start_setup, add_to_etc_hosts, run_nmap, run_webscan
from lth.vpn import start_vpn, stop_vpn, vpn_status


class CustomArgumentParser(argparse.ArgumentParser):
    """
    Custom ArgumentParser that prints help message automatically whenever
    a command-line syntax error occurs instead of showing a sparse error.
    """
    def error(self, message: str) -> None:
        """
        Handle argument parsing error by printing standard help message to stderr and exiting.

        Args:
            message (str): Error message string.
        """
        self.print_help(sys.stderr)
        sys.exit(2)


def run_cli() -> None:
    """
    Main CLI entry point. Sets up logger, parses argument sub-commands,
    and executes appropriate core functions.
    """
    # Configure root logger output format
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
    
    # Ensure working data directory ~/.lth exists
    ensure_base_dir()

    prog_name = "lth"
    parser = CustomArgumentParser(
        prog=prog_name,
        description="LTH (LetsHack CTF) - Canivete Suíço para Automação de CTFs"
    )
    subparsers = parser.add_subparsers(dest="command", required=True, parser_class=CustomArgumentParser)

    # Sub-command: ADD (Register target and prepare directory + /etc/hosts)
    parser_add = subparsers.add_parser("add", help="Registra um novo alvo e prepara o ambiente")
    parser_add.add_argument("ip", help="IP do alvo (ex: 10.10.10.3)")
    parser_add.add_argument("name", help="Nome da máquina (ex: lame)")

    # Sub-command: SCAN (Run Nmap service enumeration)
    parser_scan = subparsers.add_parser("scan", help="Inicia enumeração Nmap em um alvo conhecido")
    parser_scan.add_argument("target", help="IP ou Nome do alvo já registrado")

    # Sub-command: WEBSCAN (Run Nikto + Gobuster in parallel)
    parser_webscan = subparsers.add_parser("webscan", help="Roda Nikto e Gobuster em paralelo no alvo")
    parser_webscan.add_argument("target", help="IP ou Nome do alvo já registrado")

    # Sub-command: VPN (Manage OpenVPN connection state)
    parser_vpn = subparsers.add_parser("vpn", help="Gerencia a conexão OpenVPN")
    vpn_subparsers = parser_vpn.add_subparsers(dest="vpn_action", required=True, parser_class=CustomArgumentParser)
    
    # VPN actions: start, stop, status
    parser_vpn_start = vpn_subparsers.add_parser("start", help="Inicia a VPN (opcionalmente passando arquivo .ovpn)")
    parser_vpn_start.add_argument("file", nargs="?", default=None, help="Caminho para arquivo .ovpn")
    vpn_subparsers.add_parser("stop", help="Desconecta a VPN ativa")
    vpn_subparsers.add_parser("status", help="Exibe status da conexão VPN e IP tun0")

    # Parse arguments provided by the user
    args = parser.parse_args()

    # Route execution based on command
    if args.command == "add":
        if not is_valid_ip(args.ip):
            logging.error(f"IP inválido '{args.ip}'.")
            sys.exit(1)
        start_setup(args.ip, args.name)
        add_to_etc_hosts(args.ip, args.name)

    elif args.command in ("scan", "webscan"):
        name, ip = resolve_target(args.target)
        if not name:
            logging.error(f"Alvo '{args.target}' não encontrado na lista de alvos.")
            sys.exit(1)
        if args.command == "scan":
            run_nmap(ip, name)
        else:
            run_webscan(ip, name)

    elif args.command == "vpn":
        actions = {
            "start": lambda: start_vpn(args.file),
            "stop": stop_vpn,
            "status": vpn_status
        }
        actions[args.vpn_action]()