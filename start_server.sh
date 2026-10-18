#!/bin/bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "============================================================"
echo "  Iniciando MacroEngine Server (Linux/macOS)"
echo "============================================================"
echo ""

echo "[1/2] Verificando dependências Python..."
python3 -m pip install -r requirements.txt --quiet

echo ""
echo "[2/2] Iniciando Servidor..."
echo ""
python3 server.py
