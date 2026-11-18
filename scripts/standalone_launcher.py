#!/usr/bin/env python
"""NaijaTel Impayés AI — lanceur autonome (aucune installation requise).

Sert la démo (`demo/`) sur un port éphémère localhost et ouvre le navigateur.

  python scripts/standalone_launcher.py            # lancer depuis le projet
  PyInstaller --onefile --windowed --add-data demo:demo scripts/standalone_launcher.py
"""
from __future__ import annotations

import os
import socketserver
import sys
import threading
import webbrowser
from http.server import SimpleHTTPRequestHandler
from pathlib import Path


def find_demo() -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    for cand in (base / "demo", base.parent / "demo",
                 Path(__file__).resolve().parents[1] / "demo",
                 Path.cwd() / "demo"):
        if (cand / "index.html").exists():
            return cand
    raise SystemExit("Dossier demo/ introuvable : lancez depuis la racine du projet.")


DEMO = find_demo()
os.chdir(DEMO)


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class Server(socketserver.TCPServer):
    allow_reuse_address = True


with Server(("127.0.0.1", 0), QuietHandler) as httpd:
    port = httpd.server_address[1]
    url = f"http://127.0.0.1:{port}/"
    threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    print(f"NaijaTel Impayés AI — {url} (Ctrl+C pour quitter)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nArrêt.")
