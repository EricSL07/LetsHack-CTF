# LetsHack CTF (`lth`) 🚀

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-Linux-lightgrey.svg)](https://www.kernel.org/)

**LetsHack CTF (`lth`)** is an open-source CLI automation tool designed for penetration testers and Capture The Flag (CTF) players (HackTheBox, TryHackMe, VulnHub, etc.). It automates repetitive setup tasks, network port scanning, web vulnerability scanning, directory enumeration, and OpenVPN connection management into simple, fast terminal commands.

---

## ✨ Features

- 🎯 **Target Setup & Management**:
  - Validates IP addresses and registers targets in `~/.lth/targets.json`.
  - Creates structured output folders (`~/.lth/<target_name>/`) for scan results.
  - Automatically appends host mappings to `/etc/hosts` using `sudo`.

- 🔍 **Automated Enumeration**:
  - **Network Scanning**: Runs Nmap (`sudo nmap -sV -T4`) and detects open ports. Automatically prompts to launch web scans when HTTP (Port 80) is detected.
  - **Parallel Web Scanning**: Executes [Nikto](https://cirt.net/Nikto2) and [Gobuster](https://github.com/OJ/gobuster) simultaneously using Python's `ThreadPoolExecutor` for maximum speed.

- 🔒 **OpenVPN Lifecycle Management**:
  - Launches OpenVPN connections in background daemon mode.
  - Saves your default `.ovpn` configuration file so you don't need to specify it every time.
  - Monitors connection progress and displays assigned `tun0` interface IPv4 address.
  - Gracefully stops VPN daemon processes using PID tracking.

---

## 🛠 Prerequsite Tools

`lth` interacts with standard Linux security utilities. Ensure the following tools are installed on your system:

- **Python 3.8+**
- **Nmap** (`sudo apt install nmap`)
- **Gobuster** (`sudo apt install gobuster`)
- **Nikto** (`sudo apt install nikto`)
- **OpenVPN** (`sudo apt install openvpn`)
- Wordlist at `/usr/share/wordlists/dirb/common.txt` (or update in `lth/scanners.py`)

---

## 📦 Installation & Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/EricSL07/LetsHack-CTF.git
   cd LetsHack-CTF
   ```

2. **Make the main script executable & create a command alias/symlink**:
   ```bash
   chmod +x main.py
   
   # Optional: Create a symlink to run 'lth' from anywhere on your system
   sudo ln -s "$(pwd)/main.py" /usr/local/bin/lth
   ```

3. **Verify installation**:
   ```bash
   lth --help
   ```

---

## 📖 Usage & Commands

```
usage: lth [-h] {add,scan,webscan,vpn} ...

LTH (LetsHack CTF) - Canivete Suíço para Automação de CTFs

positional arguments:
  {add,scan,webscan,vpn}
    add                  Registra um novo alvo e prepara o ambiente
    scan                 Inicia enumeração Nmap em um alvo conhecido
    webscan              Roda Nikto e Gobuster em paralelo no alvo
    vpn                  Gerencia a conexão OpenVPN
```

### 1. Register a Target (`add`)
Registers a machine IP and hostname, creates output directory `~/.lth/<name>`, and appends entry to `/etc/hosts`.

```bash
lth add 10.10.10.3 lame
```

### 2. Run Nmap Service Scan (`scan`)
Executes an Nmap service scan on the target. If port 80 (HTTP) is found open, `lth` will prompt to launch a webscan immediately.

```bash
lth scan lame
# OR by IP address
lth scan 10.10.10.3
```

### 3. Run Web Vulnerability & Directory Scans (`webscan`)
Runs Nikto vulnerability scanner and Gobuster directory brute-forcer concurrently.

```bash
lth webscan lame
```

### 4. Manage OpenVPN Connection (`vpn`)

- **Start VPN connection**:
  ```bash
  # Start and set default .ovpn file:
  lth vpn start ~/htb_profile.ovpn

  # Start using previously saved default .ovpn file:
  lth vpn start
  ```

- **Check VPN Status**:
  ```bash
  lth vpn status
  ```
  *Output:* `STATUS: Conectado (PID: 12345) | IP tun0: 10.10.14.5`

- **Stop VPN connection**:
  ```bash
  lth vpn stop
  ```

---

## 📁 File Structure & Storage Layout

When you use `lth`, it stores configuration and scan outputs in `~/.lth/`:

```
~/.lth/
├── targets.json         # Central JSON database of registered targets
├── default.ovpn         # Saved default OpenVPN profile
├── openvpn.pid          # Active OpenVPN daemon PID tracker
├── openvpn.log          # OpenVPN daemon log output
└── <target_name>/       # Per-target scan directory
    ├── nmap_<IP>.txt    # Nmap scan results
    ├── nikto_<IP>.txt   # Nikto web scan results
    └── gobuster_<IP>.txt# Gobuster directory brute-force results
```

---

## 🏗 Project Architecture

```
LetsHack-CTF-/
├── main.py              # Main execution entry point
├── lth/                 # Core Python package
│   ├── __init__.py      # Package metadata
│   ├── cli.py           # Command-line argument parser & router
│   ├── config.py        # Config paths, IP validation & JSON registry persistence
│   ├── scanners.py      # Nmap, Nikto, Gobuster & /etc/hosts helpers
│   └── vpn.py           # OpenVPN daemon lifecycle & tun0 IP detector
├── LICENSE              # MIT License
└── README.md            # Documentation
```

---

## 🤝 Contributing

Contributions, feature requests, and bug reports are welcome!
1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for details.
