#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
clear
echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║        Brother QL-1100 — Fix P-touch Editor         ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
python3 "$SCRIPT_DIR/brother_ql1100_fix.py" --clean-ptouch
echo ""
echo "  Reopen P-touch Editor — duplicates should be gone."
echo ""
read -n 1 -s -r -p "  Press any key to close..."
echo ""
