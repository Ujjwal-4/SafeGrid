#!/usr/bin/env python3
"""
app.py
Root launcher for the platform server.
"""
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from server.app import run_server

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"Starting Intel Ingestion Platform on http://{host}:{port}...")
    run_server(host=host, port=port)
