#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
clear
echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║        Brother QL-1100 — Diagnostic Report          ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
sudo python3 "$SCRIPT_DIR/brother_ql1100_fix.py" --diag --save-report
echo ""
echo "  Report saved to your Desktop."
echo ""
read -n 1 -s -r -p "  Press any key to close..."
echo ""
