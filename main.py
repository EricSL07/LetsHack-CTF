"""
LetsHack CTF (LTH) - Entry Point

This file serves as the main execution entry point for the LTH command-line interface.
It imports and executes the CLI handler when executed directly.
"""

from lth.cli import run_cli

if __name__ == "__main__":
    run_cli()