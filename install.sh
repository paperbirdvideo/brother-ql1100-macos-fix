#!/bin/bash
# ══════════════════════════════════════════════════════════════════
#  Brother QL-1100 macOS Fix — One-Line Installer
#  Usage: curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/brother-ql1100-macos-fix/main/install.sh | bash
# ══════════════════════════════════════════════════════════════════

set -e

G="\033[92m"; R="\033[91m"; B="\033[94m"; Y="\033[93m"; BOLD="\033[1m"; X="\033[0m"
ok()   { echo -e "  ${G}[OK]${X}  $1"; }
bad()  { echo -e "  ${R}[!!]${X}  $1"; }
info() { echo -e "  ${B}[--]${X}  $1"; }
warn() { echo -e "  ${Y}[??]${X}  $1"; }

echo ""
echo -e "${BOLD}══════════════════════════════════════════════════════════════${X}"
echo -e "  Brother QL-1100 macOS Fix — Installer"
echo -e "${BOLD}══════════════════════════════════════════════════════════════${X}"
echo ""

# ── Check macOS ──────────────────────────────────────────────────
if [[ "$(uname)" != "Darwin" ]]; then
    bad "This script is for macOS only."
    exit 1
fi
ok "macOS detected: $(sw_vers -productVersion) ($(uname -m))"

# ── Check Python 3 ───────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    bad "Python 3 not found."
    info "Install via: xcode-select --install"
    exit 1
fi
PY_VER=$(python3 --version 2>&1)
ok "Python: $PY_VER"

# ── Install directory ─────────────────────────────────────────────
INSTALL_DIR="$HOME/brother-ql1100-macos-fix"
mkdir -p "$INSTALL_DIR"
ok "Install directory: $INSTALL_DIR"

# ── Download files ────────────────────────────────────────────────
BASE_URL="https://raw.githubusercontent.com/YOUR_USERNAME/brother-ql1100-macos-fix/main"

info "Downloading fix script..."
curl -fsSL "$BASE_URL/brother_ql1100_fix.py" -o "$INSTALL_DIR/brother_ql1100_fix.py"
ok "Downloaded: brother_ql1100_fix.py"

info "Downloading requirements..."
curl -fsSL "$BASE_URL/requirements.txt" -o "$INSTALL_DIR/requirements.txt"
ok "Downloaded: requirements.txt"

info "Downloading MEDIA_CODES reference..."
curl -fsSL "$BASE_URL/MEDIA_CODES.md" -o "$INSTALL_DIR/MEDIA_CODES.md"
ok "Downloaded: MEDIA_CODES.md"

# ── Make executable ───────────────────────────────────────────────
chmod +x "$INSTALL_DIR/brother_ql1100_fix.py"

# ── Install Python deps ───────────────────────────────────────────
info "Installing Python dependencies (reportlab, qrcode)..."
pip3 install -r "$INSTALL_DIR/requirements.txt" --break-system-packages -q 2>/dev/null \
    || pip3 install reportlab "qrcode[pil]" --break-system-packages -q 2>/dev/null \
    || warn "Could not install deps automatically — script will install on first run"
ok "Python dependencies installed"

# ── Create shell alias ────────────────────────────────────────────
ALIAS_LINE="alias brother-fix='sudo python3 $INSTALL_DIR/brother_ql1100_fix.py'"
SHELL_RC=""

if [[ "$SHELL" == *"zsh"* ]]; then
    SHELL_RC="$HOME/.zshrc"
elif [[ "$SHELL" == *"bash"* ]]; then
    SHELL_RC="$HOME/.bash_profile"
fi

if [[ -n "$SHELL_RC" ]]; then
    if ! grep -q "brother-fix" "$SHELL_RC" 2>/dev/null; then
        echo "" >> "$SHELL_RC"
        echo "# Brother QL-1100 fix alias" >> "$SHELL_RC"
        echo "$ALIAS_LINE" >> "$SHELL_RC"
        ok "Added alias 'brother-fix' to $SHELL_RC"
    else
        ok "Alias 'brother-fix' already in $SHELL_RC"
    fi
fi

# ── Check if Brother driver is installed ─────────────────────────
PPD="/Library/Printers/PPDs/Contents/Resources/Brother QL-1100 CUPS.gz"
if [[ -f "$PPD" ]]; then
    ok "Brother QL-1100 driver detected"
else
    warn "Brother driver NOT installed."
    echo ""
    echo -e "  ${BOLD}Install the driver before running the fix:${X}"
    echo -e "  ${B}https://support.brother.com/g/b/downloadlist.aspx${X}"
    echo -e "  ${B}?c=us&lang=en&prod=lpql1100eus&os=10069${X}"
    echo ""
fi

# ── Done ─────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}══════════════════════════════════════════════════════════════${X}"
echo -e "  ${G}Installation complete!${X}"
echo -e "${BOLD}══════════════════════════════════════════════════════════════${X}"
echo ""
echo -e "  ${BOLD}Run the full fix:${X}"
echo -e "    sudo python3 $INSTALL_DIR/brother_ql1100_fix.py"
echo ""
echo -e "  ${BOLD}Or if alias loaded (new terminal):${X}"
echo -e "    brother-fix"
echo ""
echo -e "  ${BOLD}Other commands:${X}"
echo -e "    ${B}sudo python3 $INSTALL_DIR/brother_ql1100_fix.py --diag${X}"
echo -e "    ${B}sudo python3 $INSTALL_DIR/brother_ql1100_fix.py --shipping${X}"
echo -e "    ${B}sudo python3 $INSTALL_DIR/brother_ql1100_fix.py --watch ~/Desktop/labels${X}"
echo -e "    ${B}sudo python3 $INSTALL_DIR/brother_ql1100_fix.py --list-media${X}"
echo ""
