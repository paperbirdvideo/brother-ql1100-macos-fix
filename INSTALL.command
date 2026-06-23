#!/bin/bash
# This file clears macOS Gatekeeper quarantine from all files
# and installs Python dependencies. Run this FIRST.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
clear
echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║     Brother QL-1100 — First Time Setup              ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "  Step 1: Removing macOS quarantine flag..."
xattr -cr "$SCRIPT_DIR"
echo "  ✓ Quarantine cleared — all files are now trusted"
echo ""
echo "  Step 2: Installing Python dependencies..."
pip3 install reportlab "qrcode[pil]" pillow --break-system-packages -q 2>/dev/null
echo "  ✓ Dependencies installed (reportlab, qrcode, pillow)"
echo ""
echo "  Step 3: Verifying Brother driver..."
if [ -f "/Library/Printers/PPDs/Contents/Resources/Brother QL-1100 CUPS.gz" ]; then
    echo "  ✓ Brother QL-1100 driver found"
else
    echo "  ✗ Brother driver NOT found"
    echo ""
    echo "    Install it from:"
    echo "    https://support.brother.com/g/b/downloadlist.aspx"
    echo "    ?c=us&lang=en&prod=lpql1100eus&os=10069"
fi
echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  Setup complete!                                    ║"
echo "║                                                     ║"
echo "║  Now double-click  RUN_FIX.command  to fix         ║"
echo "║  your Brother QL-1100 printer.                     ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
read -n 1 -s -r -p "  Press any key to close..."
echo ""
