import sys
import argparse
import logging
import os
from lth.config import is_valid_ip, resolve_target, ensure_base_dir
from lth.scanners import start_setup, add_to_etc_hosts, run_nmap, run_webscan
from lth.vpn import start_vpn, stop_vpn, vpn_status

class CustomArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        self.print_help(sys.stderr)
        sys.exit(2)

def run_cli():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
    ensure_base_dir()

    prog_name = "lth"
    parser = CustomArgumentParser(prog=prog_name, description="LTH - Canivete Suíço para CTFs")
    subparsers = parser.add_subparsers(dest="command", required=True, parser_class=CustomArgumentParser)

    # ADD
    parser_add = subparsers.add_parser("add", help="Registra um novo alvo e prepara o ambiente")
    parser_add.add_argument("ip", help="IP do alvo")
    parser_add.add_argument("name", help="Nome da máquina")

    # SCAN
    parser_scan = subparsers.add_parser("scan", help="Inicia enumeração em um alvo conhecido")
    parser_scan.add_argument("target", help="IP ou Nome do alvo já registrado")

    # WEBSCAN
    parser_webscan = subparsers.add_parser("webscan", help="Roda Nikto e Gobuster em paralelo")
    parser_webscan.add_argument("target", help="IP ou Nome do alvo já registrado")

    # VPN
    parser_vpn = subparsers.add_parser("vpn", help="Gerencia a conexão OpenVPN")
    vpn_subparsers = parser_vpn.add_subparsers(dest="vpn_action", required=True, parser_class=CustomArgumentParser)
    
    parser_vpn_start = vpn_subparsers.add_parser("start", help="Inicia a VPN")
    parser_vpn_start.add_argument("file", nargs="?", default=None, help="Caminho para arquivo .ovpn")
    vpn_subparsers.add_parser("stop", help="Desconecta a VPN")
    vpn_subparsers.add_parser("status", help="Status da VPN")

    args = parser.parse_args()

    if args.command == "add":
        if not is_valid_ip(args.ip):
            logging.error(f"IP inválido '{args.ip}'.")
            sys.exit(1)
        start_setup(args.ip, args.name)
        add_to_etc_hosts(args.ip, args.name)

    elif args.command in ("scan", "webscan"):
        name, ip = resolve_target(args.target)
        if not name:
            logging.error(f"Alvo '{args.target}' não encontrado.")
            sys.exit(1)
        if args.command == "scan":
            run_nmap(ip, name)
        else:
            run_webscan(ip, name)

    elif args.command == "vpn":
        actions = {"start": lambda: start_vpn(args.file), "stop": stop_vpn, "status": vpn_status}
        actions[args.vpn_action]()