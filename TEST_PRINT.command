#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
clear
echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║        Brother QL-1100 — Send Test Label            ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
sudo python3 "$SCRIPT_DIR/brother_ql1100_fix.py" --test-print
echo ""
read -n 1 -s -r -p "  Press any key to close..."
echo ""
