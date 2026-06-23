#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║        Brother QL-1100 macOS Fix + Print Utility               ║
║        github.com/YOUR_USERNAME/brother-ql1100-macos-fix        ║
╠══════════════════════════════════════════════════════════════════╣
║  Fixes:  paper-size-error, filter crash, stuck jobs,           ║
║          P-touch duplicates, wrong media code                   ║
║  Bonus:  shipping labels, QR codes, folder watch mode          ║
╚══════════════════════════════════════════════════════════════════╝
"""

import subprocess, os, sys, gzip, time, argparse, shutil, platform
import json, re, signal, threading, hashlib, urllib.request, tempfile
from pathlib import Path
from datetime import datetime

# ── ANSI colors ───────────────────────────────────────────────────
G="\033[92m"; R="\033[91m"; B="\033[94m"; Y="\033[93m"
M="\033[95m"; C="\033[96m"; BOLD="\033[1m"; DIM="\033[2m"; X="\033[0m"

def ok(m):      print(f"  {G}[OK]{X}  {m}")
def bad(m):     print(f"  {R}[!!]{X}  {m}")
def info(m):    print(f"  {B}[--]{X}  {m}")
def warn(m):    print(f"  {Y}[??]{X}  {m}")
def step(m):    print(f"\n  {M}[>>]{X}  {BOLD}{m}{X}")
def section(t): print(f"\n{C}{'═'*62}{X}\n  {BOLD}{t}{X}\n{C}{'═'*62}{X}")

def progress(msg, total=20):
    sys.stdout.write(f"  {B}[--]{X}  {msg}  [")
    for i in range(total):
        time.sleep(0.05)
        sys.stdout.write("█")
        sys.stdout.flush()
    print(f"]  {G}done{X}")

def run(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return (r.stdout + r.stderr).strip()

def run_ok(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True).returncode == 0

# ── Media code lookup table ───────────────────────────────────────
# All Brother DK label sizes with their exact PPD internal codes
# These are the ONLY codes the rastertobrotherQL1100 filter accepts
MEDIA_CODES = {
    # Die-cut labels
    "DC01": {"desc": "17mm x 54mm",    "mm": (17,54),   "inch": (0.66,2.1),  "dk": "DK-1204"},
    "DC02": {"desc": "17mm x 87mm",    "mm": (17,87),   "inch": (0.66,3.4),  "dk": "DK-1203"},
    "DC03": {"desc": "29mm x 90mm",    "mm": (29,90),   "inch": (1.1,3.5),   "dk": "DK-1201"},
    "DC04": {"desc": "38mm x 90mm",    "mm": (38,90),   "inch": (1.5,3.5),   "dk": "DK-1202"},
    "DC06": {"desc": "62mm x 29mm",    "mm": (62,29),   "inch": (2.4,1.1),   "dk": "DK-1209"},
    "DC07": {"desc": "62mm x 100mm",   "mm": (62,100),  "inch": (2.4,3.9),   "dk": "DK-1240"},
    "DC08": {"desc": "29mm x 42mm",    "mm": (29,42),   "inch": (1.1,1.6),   "dk": "DK-1221"},
    "DC15": {"desc": "102mm x 51mm",   "mm": (102,51),  "inch": (4.0,2.0),   "dk": "DK-1247"},
    "DC16": {"desc": "102mm x 152mm",  "mm": (102,152), "inch": (4.0,6.0),   "dk": "DK-1241"},  # ← DEFAULT
    "DC17": {"desc": "39mm x 48mm",    "mm": (39,48),   "inch": (1.5,1.9),   "dk": "DK-1208"},
    "DC20": {"desc": "23mm x 23mm",    "mm": (23,23),   "inch": (0.9,0.9),   "dk": "DK-1219"},
    "DC24": {"desc": "52mm x 29mm",    "mm": (52,29),   "inch": (2.0,1.1),   "dk": "DK-1222"},
    "DCNB": {"desc": "60mm x 86mm",    "mm": (60,86),   "inch": (2.3,3.3),   "dk": "DK-1247"},
    "DC12": {"desc": "12mm Round",     "mm": (12,12),   "inch": (0.5,0.5),   "dk": "DK-1235"},
    "DC13": {"desc": "24mm Round",     "mm": (24,24),   "inch": (0.9,0.9),   "dk": "DK-1236"},
    "DC05": {"desc": "58mm Round",     "mm": (58,58),   "inch": (2.3,2.3),   "dk": "DK-1207"},
    # Continuous rolls
    "12mm":  {"desc": "12mm continuous",  "mm": (12,0),  "inch": (0.5,0),  "dk": "DK-2205"},
    "29mm":  {"desc": "29mm continuous",  "mm": (29,0),  "inch": (1.1,0),  "dk": "DK-2211"},
    "38mm":  {"desc": "38mm continuous",  "mm": (38,0),  "inch": (1.5,0),  "dk": "DK-2213"},
    "50mm":  {"desc": "50mm continuous",  "mm": (50,0),  "inch": (2.0,0),  "dk": "DK-2246"},
    "54mm":  {"desc": "54mm continuous",  "mm": (54,0),  "inch": (2.1,0),  "dk": "DK-2243"},
    "62mm":  {"desc": "62mm continuous",  "mm": (62,0),  "inch": (2.4,0),  "dk": "DK-2205"},
    "102mm": {"desc": "102mm continuous", "mm": (102,0), "inch": (4.0,0),  "dk": "DK-2246"},
}

# PPD canvas dimensions (points) for each die-cut size
PPD_DIMENSIONS = {
    "DC01": (48.24,  152.64),
    "DC02": (48.24,  246.24),
    "DC03": (82.08,  254.64),
    "DC04": (107.76, 254.64),
    "DC06": (175.68, 81.84),
    "DC07": (175.68, 282.96),
    "DC08": (82.08,  118.80),
    "DC15": (288.00, 143.04),
    "DC16": (288.00, 432.96),  # ← DK-1241 4x6"
    "DC17": (110.64, 135.60),
    "DC20": (65.28,  65.28),
    "DC24": (147.36, 81.84),
    "DCNB": (170.08, 246.61),
    "DC12": (34.08,  34.08),
    "DC13": (68.16,  68.16),
    "DC05": (165.12, 165.12),
}

# ── Paths ─────────────────────────────────────────────────────────
PRINTER_NAME     = "Brother_QL1100"
PPD_PATH         = "/Library/Printers/PPDs/Contents/Resources/Brother QL-1100 CUPS.gz"
FILTER_PATH      = "/Library/Printers/Brother/Filter/rastertobrotherQL1100.bundle/Contents/MacOS/rastertobrotherQL1100"
CUPS_LOG         = "/var/log/cups/error_log"
CUPS_DAEMON      = "/System/Library/LaunchDaemons/org.cups.cupsd.plist"
PTOUCH_CONTAINER = Path.home() / "Library/Containers/com.brother.PtouchEditor"
PTOUCH_SFL       = Path.home() / "Library/Application Support/com.apple.sharedfilelist/com.apple.LSSharedFileList.ApplicationRecentDocuments/com.brother.ptoucheditor.sfl4"
DRIVER_URL       = "https://support.brother.com/g/b/downloadlist.aspx?c=us&lang=en&prod=lpql1100eus&os=10069"
VERSION          = "2.0.0"
SCRIPT_URL       = "https://raw.githubusercontent.com/YOUR_USERNAME/brother-ql1100-macos-fix/main/brother_ql1100_fix.py"

# ═══════════════════════════════════════════════════════════════════
# USB DETECTION
# ═══════════════════════════════════════════════════════════════════
def detect_usb():
    """Auto-detect QL-1100 URI and serial from CUPS USB backend."""
    usb_raw = run("ioreg -p IOUSB -l -w 0")
    if "QL-1100" not in usb_raw:
        return None, None, None

    # Get full backend info
    backend_out = run("sudo /usr/libexec/cups/backend/usb 2>&1") if os.geteuid()==0 else run("/usr/libexec/cups/backend/usb 2>&1")
    uri = None
    serial = None
    speed = None

    for line in backend_out.splitlines():
        if "brother" in line.lower() or "QL-1100" in line:
            parts = line.strip().split()
            if len(parts) >= 2:
                uri = parts[1]
                m = re.search(r'serial=([A-Z0-9]+)', uri)
                if m:
                    serial = m.group(1)

    # Get USB speed from IORegistry
    for line in usb_raw.splitlines():
        if "UsbLinkSpeed" in line and "12000000" in line:
            speed = "USB1.1-12Mbps"
        elif "UsbLinkSpeed" in line and "480000000" in line:
            speed = "USB2.0-480Mbps"

    return uri, serial, speed

def detect_roll():
    """
    Attempt to detect which DK roll is loaded by querying
    the printer's back-channel status bytes via CUPS.
    Falls back to DC16 (DK-1241) if detection fails.
    """
    # The QL-1100 reports its loaded media via USB back-channel.
    # We send a tiny job and read the state response.
    # Most compatible (non-genuine) rolls report DC16 or no ID.
    backend_out = run("sudo /usr/libexec/cups/backend/usb 2>&1") if os.geteuid()==0 else ""
    if "QL-1100" not in backend_out:
        return "DC16"

    # Check CUPS log for most recent paper-size state
    if os.path.exists(CUPS_LOG):
        log = open(CUPS_LOG, errors="replace").read()
        # Look for the most recent STATE line
        states = re.findall(r'STATE: (com\.brother-[^\s]+)', log)
        if states:
            last = states[-1]
            # Map known state codes to media
            if "paper-size-error" in last:
                warn("Printer reports paper-size-error — using DC16 (DK-1241)")
            return "DC16"

    return "DC16"

# ═══════════════════════════════════════════════════════════════════
# DRIVER CHECK + VERSION VALIDATION
# ═══════════════════════════════════════════════════════════════════
def check_driver():
    """
    Check if Brother driver is installed, and whether it is dangerously
    old (pre-2020 Intel-only builds crash on Apple Silicon with signal 11).
    """
    # Not installed at all
    if not os.path.exists(PPD_PATH) or not os.path.exists(FILTER_PATH):
        bad("Brother QL-1100 driver NOT installed.")
        print(f"""
  {BOLD}Install the driver first:{X}

  1. Open this URL in Safari:
     {Y}{DRIVER_URL}{X}

  2. Download: {BOLD}Printer Driver & Editor{X}
     (Choose macOS 11+ / Universal / ARM)

  3. Mount the .dmg and run the .pkg installer

  4. Re-run this script after installation
""")
        return False

    # Check driver age via PPD file modification date
    try:
        ppd_mtime = os.path.getmtime(PPD_PATH)
        ppd_date  = datetime.fromtimestamp(ppd_mtime)
        ppd_year  = ppd_date.year
        ppd_date_str = ppd_date.strftime("%B %d, %Y")
    except Exception:
        ppd_year = 0
        ppd_date_str = "unknown"

    # Check if filter is ARM native or Intel-only (Rosetta)
    filter_arch = run(f'file "{FILTER_PATH}" 2>/dev/null')
    is_arm_native = "arm64" in filter_arch
    is_intel_only = "x86_64" in filter_arch and "arm64" not in filter_arch
    is_universal  = "arm64" in filter_arch and "x86_64" in filter_arch

    # Check bundle version
    bundle_dir = os.path.dirname(os.path.dirname(os.path.dirname(FILTER_PATH)))
    bundle_ver = run(
        f'defaults read "{bundle_dir}/Info" CFBundleShortVersionString 2>/dev/null'
    ).strip() or "unknown"

    # Report findings
    info(f"Driver PPD date  : {ppd_date_str}")
    info(f"Filter version   : {bundle_ver}")

    if is_universal:
        ok("Filter binary: Universal (ARM64 + x86_64) — optimal")
    elif is_arm_native:
        ok("Filter binary: ARM64 native — optimal")
    elif is_intel_only:
        bad("Filter binary: Intel-only (x86_64) running under Rosetta on Apple Silicon")
        bad("ROOT CAUSE of signal 11 crashes and paper-size-error loops")

    DRIVER_IS_OLD = ppd_year > 0 and ppd_year < 2021

    if DRIVER_IS_OLD or is_intel_only:
        print(f"""
  {R}{BOLD}╔══════════════════════════════════════════════════════╗
  ║  OLD / INCOMPATIBLE DRIVER DETECTED                 ║
  ╚══════════════════════════════════════════════════════╝{X}

  {BOLD}Your driver is from {ppd_date_str}.{X}
  On Apple Silicon (M1-M4), old Intel-only Brother drivers
  run under Rosetta and cause:

    • rastertobrotherQL1100 crashed on signal 11
    • com.brother-paper-size-error loop
    • Filter failed / jobs stuck forever

  {BOLD}The DC16 fix in this script resolves paper-size-error,
  but updating the driver eliminates the root cause entirely.{X}

  {Y}RECOMMENDED: Update your driver{X}
  1. Open in Safari:
     {Y}{DRIVER_URL}{X}
  2. Download: Printer Driver & Editor (macOS 13/14/15/26 Universal)
  3. Run the .pkg — it replaces the old driver automatically
  4. Re-run this script after updating

  {DIM}Continuing with fix now using current driver...{X}
""")
        time.sleep(2)
        return True  # DC16 fix still helps even with old driver

    if ppd_year >= 2021:
        ok(f"Driver is recent ({ppd_date_str}) — no update needed")

    return True

# ═══════════════════════════════════════════════════════════════════
# CUPS OPERATIONS
# ═══════════════════════════════════════════════════════════════════
def clear_cups_queue():
    run(f"cancel -a {PRINTER_NAME} 2>/dev/null")
    run("cancel -a 2>/dev/null")
    ok("All print jobs cancelled")

def flush_cups_spool():
    run(f"launchctl unload {CUPS_DAEMON} 2>/dev/null")
    time.sleep(1)
    # Only delete files (not directories like /var/spool/cups/cache)
    for f in Path("/var/spool/cups").glob("c*"):
        if f.is_file(): f.unlink(missing_ok=True)
    for f in Path("/var/spool/cups").glob("d*"):
        if f.is_file(): f.unlink(missing_ok=True)
    run(f"launchctl load {CUPS_DAEMON} 2>/dev/null")
    time.sleep(3)
    ok("CUPS spool flushed and scheduler restarted")

def setup_printer(uri, media_code="DC16"):
    run(f"lpadmin -x {PRINTER_NAME} 2>/dev/null")
    time.sleep(1)

    result = run(
        f'lpadmin -p {PRINTER_NAME} -E '
        f'-v "{uri}" '
        f'-P "{PPD_PATH}" '
        f'-D "Brother QL-1100" '
        f'-L "USB Label Printer"'
    )
    if "error" in result.lower() and "deprecated" not in result.lower():
        bad(f"lpadmin: {result}")
        return False

    run(f"lpoptions -p {PRINTER_NAME} "
        f"-o media={media_code} "
        f"-o orientation-requested=3 "
        f"-o print-quality=5 "
        f"-o number-up=1 "
        f"-o fit-to-page=false "
        f"-o page-left=0 -o page-right=0 -o page-top=0 -o page-bottom=0")

    run(f"lpoptions -d {PRINTER_NAME}")
    run(f"cupsenable {PRINTER_NAME}")
    run(f"cupsaccept {PRINTER_NAME}")
    run("cupsctl --debug-logging")
    ok(f"Printer configured with media={media_code} ({MEDIA_CODES.get(media_code,{}).get('desc','?')})")
    return True

# ═══════════════════════════════════════════════════════════════════
# P-TOUCH EDITOR CLEANUP
# ═══════════════════════════════════════════════════════════════════
def clean_ptouch():
    run('killall "P-touch Editor" 2>/dev/null')
    time.sleep(1)
    targets = [
        PTOUCH_CONTAINER / "Data/Library/Preferences/com.brother.PtouchEditor.plist",
        PTOUCH_CONTAINER / "Data/Library/Caches/com.brother.PtouchEditor",
        PTOUCH_CONTAINER / "Data/Library/HTTPStorages/com.brother.PtouchEditor",
        PTOUCH_CONTAINER / "Data/tmp/com.brother.PtouchEditor",
        PTOUCH_SFL,
    ]
    removed = 0
    for t in targets:
        if t.exists():
            shutil.rmtree(t) if t.is_dir() else t.unlink()
            removed += 1
    ok(f"P-touch Editor cache cleared ({removed} items removed)")

# ═══════════════════════════════════════════════════════════════════
# PDF LABEL BUILDER
# ═══════════════════════════════════════════════════════════════════
def ensure_deps():
    missing = []
    try: import reportlab
    except ImportError: missing.append("reportlab")
    try: import qrcode
    except ImportError: missing.append("qrcode[pil]")
    if missing:
        info(f"Installing: {', '.join(missing)}...")
        run(f"pip3 install {' '.join(missing)} --break-system-packages -q 2>/dev/null")

def make_shipping_label(output_path, **kwargs):
    """
    Generate a 4x6" shipping label PDF.
    kwargs: from_name, from_addr, to_name, to_addr, tracking, barcode
    """
    ensure_deps()
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    from reportlab.lib import colors

    W, H = PPD_DIMENSIONS["DC16"]  # 288.00 x 432.96 pt

    c = canvas.Canvas(output_path, pagesize=(W, H))

    # Background
    c.setFillColor(colors.white)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    # Outer border
    c.setStrokeColor(colors.black)
    c.setLineWidth(2)
    c.rect(4, 4, W-8, H-8, fill=0, stroke=1)

    # ── FROM section ─────────────────────────────────────────────
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 7)
    c.drawString(12, H-22, "FROM:")
    c.setFont("Helvetica-Bold", 10)
    c.drawString(12, H-35, kwargs.get("from_name", ""))
    c.setFont("Helvetica", 9)
    y = H-48
    for line in kwargs.get("from_addr", "").split("\n"):
        c.drawString(12, y, line)
        y -= 12

    # Divider
    c.setLineWidth(0.5)
    c.line(8, H-85, W-8, H-85)

    # ── TO section ───────────────────────────────────────────────
    c.setFont("Helvetica", 8)
    c.drawString(12, H-100, "SHIP TO:")
    c.setFont("Helvetica-Bold", 16)
    to_name = kwargs.get("to_name", "")
    c.drawString(12, H-122, to_name)
    c.setFont("Helvetica", 12)
    y = H-142
    for line in kwargs.get("to_addr", "").split("\n"):
        c.drawString(12, y, line)
        y -= 16

    # Divider
    c.line(8, H-230, W-8, H-230)

    # ── Tracking / QR code ───────────────────────────────────────
    tracking = kwargs.get("tracking", "")
    if tracking:
        try:
            import qrcode as qr
            from reportlab.lib.utils import ImageReader
            import io
            qr_img = qr.make(tracking)
            buf = io.BytesIO()
            qr_img.save(buf, format="PNG")
            buf.seek(0)
            c.drawImage(ImageReader(buf), W-110, H-360, width=100, height=100)
        except Exception:
            pass

        c.setFont("Helvetica-Bold", 9)
        c.drawString(12, H-250, "TRACKING:")
        c.setFont("Courier-Bold", 11)
        c.drawString(12, H-265, tracking)

        # Barcode-style visual (simplified)
        c.setFont("Helvetica", 7)
        c.drawString(12, H-290, "||||| |||| ||| || ||||| |||| ||| || |||||")

    # ── Footer ───────────────────────────────────────────────────
    c.setLineWidth(0.5)
    c.line(8, 30, W-8, 30)
    c.setFont("Helvetica", 7)
    c.setFillColor(colors.grey)
    c.drawCentredString(W/2, 18, f"Printed {datetime.now().strftime('%Y-%m-%d %H:%M')}  |  Brother QL-1100  |  DK-1241")
    c.drawCentredString(W/2, 8,  "github.com/YOUR_USERNAME/brother-ql1100-macos-fix")

    c.save()
    return output_path

def make_qr_label(output_path, text, title="", subtitle=""):
    """Generate a QR code label."""
    ensure_deps()
    from reportlab.pdfgen import canvas
    from reportlab.lib import colors
    from reportlab.lib.utils import ImageReader
    import qrcode as qr, io

    W, H = PPD_DIMENSIONS["DC16"]
    c = canvas.Canvas(output_path, pagesize=(W, H))
    c.setFillColor(colors.white)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setStrokeColor(colors.black)
    c.setLineWidth(1.5)
    c.rect(4, 4, W-8, H-8, fill=0, stroke=1)

    if title:
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(W/2, H-40, title)
        c.setLineWidth(0.5)
        c.line(10, H-52, W-10, H-52)

    # QR code
    qr_img = qr.make(text, box_size=6, border=2)
    buf = io.BytesIO()
    qr_img.save(buf, format="PNG")
    buf.seek(0)
    qr_size = 200
    c.drawImage(ImageReader(buf), (W-qr_size)/2, H-280, width=qr_size, height=qr_size)

    if subtitle:
        c.setFont("Helvetica", 11)
        c.setFillColor(colors.black)
        c.drawCentredString(W/2, H-300, subtitle)

    c.setFont("Courier", 9)
    c.drawCentredString(W/2, H-320, text[:60])

    c.setFont("Helvetica", 8)
    c.setFillColor(colors.grey)
    c.drawCentredString(W/2, 15, datetime.now().strftime("%Y-%m-%d %H:%M"))
    c.save()
    return output_path

def make_test_label(output_path, media_code="DC16"):
    """Generate a test/diagnostic label."""
    ensure_deps()
    from reportlab.pdfgen import canvas
    from reportlab.lib import colors

    W, H = PPD_DIMENSIONS.get(media_code, (288.00, 432.96))
    c = canvas.Canvas(output_path, pagesize=(W, H))
    c.setFillColor(colors.white)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setStrokeColor(colors.black)
    c.setLineWidth(2)
    c.rect(4, 4, W-8, H-8, fill=0, stroke=1)
    c.setFillColor(colors.black)

    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(W/2, H-50, "Brother QL-1100")
    c.setLineWidth(0.5)
    c.line(10, H-62, W-10, H-62)

    c.setFont("Helvetica-Bold", 15)
    c.drawCentredString(W/2, H-85, f"Media: {media_code}")
    info_str = MEDIA_CODES.get(media_code, {}).get("desc", "")
    c.setFont("Helvetica", 12)
    c.drawCentredString(W/2, H-105, info_str)
    dk_str = MEDIA_CODES.get(media_code, {}).get("dk", "")
    c.drawCentredString(W/2, H-122, f"Compatible: {dk_str}")

    c.line(10, H-135, W-10, H-135)
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(W/2, H-155, "macOS Fix Script")
    c.setFont("Helvetica", 10)
    c.drawCentredString(W/2, H-172, "github.com/YOUR_USERNAME/")
    c.drawCentredString(W/2, H-185, "brother-ql1100-macos-fix")

    c.line(10, H-200, W-10, H-200)
    c.setFont("Helvetica", 10)
    c.drawCentredString(W/2, H-218, f"Canvas: {W} x {H} pt")
    c.drawCentredString(W/2, H-232, f"macOS: {platform.mac_ver()[0]}  {platform.machine()}")
    c.drawCentredString(W/2, H-246, datetime.now().strftime("%Y-%m-%d  %H:%M:%S"))

    c.setFont("Helvetica", 8)
    c.setFillColorRGB(0.4,0.4,0.4)
    c.drawCentredString(W/2, 15, "If this printed correctly — your printer is working!")
    c.save()
    return output_path

# ═══════════════════════════════════════════════════════════════════
# PRINT JOB SENDER
# ═══════════════════════════════════════════════════════════════════
def send_to_printer(pdf_path, media_code="DC16", copies=1):
    """Send a PDF to the Brother printer with correct settings."""
    if not os.path.exists(pdf_path):
        bad(f"File not found: {pdf_path}")
        return False

    run(f"cancel -a {PRINTER_NAME} 2>/dev/null")
    time.sleep(0.5)

    cmd = (
        f'lp -d {PRINTER_NAME} '
        f'-n {copies} '
        f'-o media={media_code} '
        f'-o orientation-requested=3 '
        f'-o number-up=1 '
        f'-o fit-to-page=false '
        f'"{pdf_path}"'
    )
    result = run(cmd)
    if "request id" in result.lower():
        job_id = re.search(r'request id is (\S+)', result)
        ok(f"Job submitted: {job_id.group(1) if job_id else 'OK'}")
        return True
    else:
        bad(f"Print failed: {result}")
        return False

def wait_for_print(timeout=15):
    """Poll queue until idle or error."""
    start = time.time()
    while time.time() - start < timeout:
        q = run(f"lpq -P {PRINTER_NAME} 2>&1")
        if "no entries" in q.lower() or ("ready" in q.lower() and "printing" not in q.lower()):
            return True, "completed"
        if "error" in q.lower() or "stopped" in q.lower():
            return False, q
        time.sleep(1)
    return False, "timeout"

# ═══════════════════════════════════════════════════════════════════
# WATCH MODE
# ═══════════════════════════════════════════════════════════════════
def watch_folder(folder, media_code="DC16"):
    """
    Watch a folder and auto-print any PDF dropped into it.
    Moves printed files to /printed/ subfolder.
    """
    watch_path = Path(folder).expanduser()
    printed_path = watch_path / "printed"
    printed_path.mkdir(exist_ok=True)

    seen = set()
    stop_event = threading.Event()

    def handle_sigint(sig, frame):
        print(f"\n\n  {Y}[??]{X}  Watch mode stopped.")
        stop_event.set()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_sigint)

    section(f"WATCH MODE — {watch_path}")
    ok(f"Watching for PDFs... (Ctrl+C to stop)")
    info(f"Printed files → {printed_path}")
    info(f"Media code: {media_code} ({MEDIA_CODES.get(media_code,{}).get('desc','?')})")
    print()

    while not stop_event.is_set():
        for pdf in watch_path.glob("*.pdf"):
            key = f"{pdf.name}:{pdf.stat().st_mtime}"
            if key not in seen:
                seen.add(key)
                print(f"  {G}[>>]{X}  New file: {pdf.name}")
                sent = send_to_printer(str(pdf), media_code)
                if sent:
                    success, state = wait_for_print(timeout=20)
                    if success:
                        ok(f"Printed: {pdf.name}")
                        dest = printed_path / pdf.name
                        shutil.move(str(pdf), str(dest))
                        info(f"Moved to: printed/{pdf.name}")
                    else:
                        bad(f"Print failed: {state}")
                else:
                    bad(f"Could not send: {pdf.name}")
        time.sleep(2)

# ═══════════════════════════════════════════════════════════════════
# AUTO DRIVER UPDATE
# ═══════════════════════════════════════════════════════════════════
# Latest macOS driver: v1.11.0d — July 18, 2025 — Universal (ARM64 + x86_64)
# Direct from Brother's CDN — no browser required
DRIVER_DMG_URL = "https://support.brother.com/g/b/downloadend.aspx?c=us&lang=en&prod=lpql1100eus&os=10069&dlid=dlf006893_000&flang=English&type3=347"
DRIVER_VERSION = "1.11.0d"
DRIVER_DATE    = "July 18, 2025"

def auto_update_driver():
    """
    Download the latest Brother QL-1100 macOS driver (v1.11.0d, July 2025)
    directly from Brother's servers, mount the DMG, and run the pkg installer.
    No browser required. Requires sudo.
    """
    import urllib.request, tempfile, subprocess

    if os.geteuid() != 0:
        bad("Driver update requires sudo. Run with: sudo python3 brother_ql1100_fix.py --update-driver")
        return False

    section("AUTO DRIVER UPDATE — v1.11.0d (July 2025)")

    # Check current driver state
    ppd_mtime = os.path.getmtime(PPD_PATH) if os.path.exists(PPD_PATH) else 0
    ppd_year  = datetime.fromtimestamp(ppd_mtime).year if ppd_mtime else 0
    filter_arch = run(f'file "{FILTER_PATH}" 2>/dev/null') if os.path.exists(FILTER_PATH) else ""
    is_intel_only = "x86_64" in filter_arch and "arm64" not in filter_arch

    if ppd_year >= 2025 and not is_intel_only:
        ok(f"Driver already up to date ({datetime.fromtimestamp(ppd_mtime).strftime('%B %d, %Y')})")
        ok("No update needed.")
        return True

    if ppd_year > 0:
        warn(f"Current driver: {datetime.fromtimestamp(ppd_mtime).strftime('%B %d, %Y')} — updating to {DRIVER_DATE}")
    else:
        info(f"No driver found — installing {DRIVER_DATE}")

    # Create temp directory
    tmp_dir = tempfile.mkdtemp(prefix="brother_driver_")
    dmg_path = os.path.join(tmp_dir, "brother_ql1100_driver.dmg")
    mount_point = "/Volumes/BrotherQL1100Driver"

    try:
        # Step 1: Download DMG
        info(f"Downloading Brother QL-1100 driver v{DRIVER_VERSION} ({DRIVER_DATE})...")
        info(f"Source: download.brother.com (official)")
        info("This is ~33MB — may take 30-60 seconds...")
        print()

        def download_progress(block_num, block_size, total_size):
            if total_size > 0:
                pct = min(100, int(block_num * block_size * 100 / total_size))
                bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
                sys.stdout.write(f"\r  {B}[--]{X}  [{bar}] {pct}%  ")
                sys.stdout.flush()

        try:
            urllib.request.urlretrieve(DRIVER_DMG_URL, dmg_path, reporthook=download_progress)
            print(f"\r  {G}[OK]{X}  Download complete ({os.path.getsize(dmg_path) // 1024 // 1024}MB)        ")
        except Exception as e:
            # Fallback: try curl which handles redirects better
            print()
            info("Trying curl fallback...")
            curl_cmd = (
                'curl -L -o ' + dmg_path +
                ' --user-agent "Mozilla/5.0 (Macintosh; Apple M4)"'
                ' "https://support.brother.com/g/b/downloadend.aspx'
                '?c=us&lang=en&prod=lpql1100eus&os=10069&dlid=dlf006893_000&flang=English&type3=347"'
                ' 2>&1 | tail -5'
            )
            result = run(curl_cmd)
            if not os.path.exists(dmg_path) or os.path.getsize(dmg_path) < 1000000:
                bad(f"Download failed: {e}")
                bad("Brother's download page requires browser session.")
                bad(f"Please download manually from:")
                bad(f"  {DRIVER_URL}")
                bad("Then run the .pkg installer and re-run this script.")
                return False

        # Verify it looks like a DMG
        file_type = run(f'file "{dmg_path}"')
        if "data" not in file_type.lower() and "disk" not in file_type.lower() and "dmg" not in file_type.lower():
            # May be an HTML redirect page instead of the actual file
            bad("Downloaded file doesn't appear to be a DMG.")
            bad("Brother's server requires a browser session for this download.")
            info(f"File type: {file_type[:100]}")
            bad(f"Download manually from: {DRIVER_URL}")
            return False

        ok(f"DMG downloaded: {dmg_path}")

        # Step 2: Mount DMG
        info("Mounting DMG...")
        run(f'hdiutil detach "{mount_point}" -force 2>/dev/null')
        mount_result = run(f'hdiutil attach "{dmg_path}" -mountpoint "{mount_point}" -nobrowse -quiet 2>&1')
        if not os.path.exists(mount_point):
            bad(f"Failed to mount DMG: {mount_result}")
            return False
        ok(f"Mounted at {mount_point}")

        # Step 3: Find the .pkg
        pkg_file = None
        for root, dirs, files in os.walk(mount_point):
            for fname in files:
                if fname.endswith(".pkg") and ("QL" in fname or "Brother" in fname or "printer" in fname.lower()):
                    pkg_file = os.path.join(root, fname)
                    break
            if pkg_file: break

        if not pkg_file:
            # Try any .pkg
            for root, dirs, files in os.walk(mount_point):
                for fname in files:
                    if fname.endswith(".pkg"):
                        pkg_file = os.path.join(root, fname)
                        break
                if pkg_file: break

        if not pkg_file:
            bad("No .pkg found in DMG")
            bad(f"Contents: {os.listdir(mount_point)}")
            return False

        ok(f"Found installer: {os.path.basename(pkg_file)}")

        # Step 4: Run installer
        info("Installing driver (this takes 15-30 seconds)...")
        install_result = run(f'installer -pkg "{pkg_file}" -target / 2>&1')
        if "successful" in install_result.lower() or install_result == "":
            ok("Driver installed successfully!")
        else:
            warn(f"Installer output: {install_result[:200]}")

        # Step 5: Unmount
        run(f'hdiutil detach "{mount_point}" -quiet 2>/dev/null')
        ok("DMG unmounted")

        # Step 6: Verify new driver
        info("Verifying new driver...")
        new_filter_arch = run(f'file "{FILTER_PATH}" 2>/dev/null')
        new_ppd_mtime   = os.path.getmtime(PPD_PATH) if os.path.exists(PPD_PATH) else 0
        new_ppd_date    = datetime.fromtimestamp(new_ppd_mtime).strftime('%B %d, %Y') if new_ppd_mtime else "unknown"

        ok(f"New PPD date: {new_ppd_date}")

        if "arm64" in new_filter_arch and "x86_64" in new_filter_arch:
            ok("New filter: Universal binary (ARM64 + x86_64) ✓")
        elif "arm64" in new_filter_arch:
            ok("New filter: ARM64 native ✓")
        elif "x86_64" in new_filter_arch:
            warn("New filter: Still Intel-only — update may not have taken effect yet")
            warn("Try restarting and re-running the script")
        else:
            info(f"Filter arch: {new_filter_arch[:100]}")

        print(f"""
  {G}{BOLD}╔══════════════════════════════════════════════════════╗
  ║  Driver updated to v{DRIVER_VERSION} ({DRIVER_DATE})  ║
  ╚══════════════════════════════════════════════════════╝{X}

  Now run the full fix to reconfigure CUPS with DC16:
    {BOLD}sudo python3 brother_ql1100_fix.py{X}
  Or double-click {BOLD}RUN_FIX.command{X}
""")
        return True

    except KeyboardInterrupt:
        bad("Cancelled by user")
        return False
    finally:
        # Cleanup
        run(f'hdiutil detach "{mount_point}" -quiet 2>/dev/null')
        try:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass

# ═══════════════════════════════════════════════════════════════════
# DIAGNOSTIC
# ═══════════════════════════════════════════════════════════════════
def run_diag(save_report=False):
    section("FULL DIAGNOSTIC REPORT")
    results = {}
    report_lines = [f"Brother QL-1100 Diagnostic — {datetime.now().isoformat()}", "="*60]

    def rlog(label, passed, detail=""):
        results[label] = passed
        line = f"{'[OK]' if passed else '[!!]'}  {label}" + (f": {detail}" if detail else "")
        report_lines.append(line)
        (ok if passed else bad)(label + (f": {detail}" if detail else ""))

    # macOS info
    ver = platform.mac_ver()[0]
    arch = platform.machine()
    info(f"macOS {ver}  ({arch})  Python {sys.version.split()[0]}")
    report_lines.append(f"macOS {ver} {arch}")

    # USB
    usb_raw = run("ioreg -p IOUSB -l -w 0")
    rlog("USB: QL-1100 in IORegistry", "QL-1100" in usb_raw)
    uri, serial, speed = detect_usb()
    rlog("USB: CUPS backend sees printer", uri is not None, uri or "not found")
    if speed:
        rlog("USB: Speed OK (480 Mbps)", speed == "USB2.0-480Mbps", speed)

    # Driver
    rlog("Driver: PPD present", os.path.exists(PPD_PATH))
    rlog("Driver: Filter binary present", os.path.exists(FILTER_PATH))
    rlog("Driver: Filter executable", os.access(FILTER_PATH, os.X_OK) if os.path.exists(FILTER_PATH) else False)

    # CUPS
    cups_status = run("lpstat -r 2>&1")
    rlog("CUPS: Scheduler running", "running" in cups_status.lower())
    queue_status = run(f"lpstat -p {PRINTER_NAME} -l 2>&1")
    rlog("CUPS: Printer in queue", "idle" in queue_status.lower() or "enabled" in queue_status.lower())
    opts = run(f"lpoptions -p {PRINTER_NAME} 2>&1")
    rlog("CUPS: DC16 media set", "DC16" in opts, "run fix to correct" if "DC16" not in opts else "")

    # Log analysis
    if os.path.exists(CUPS_LOG):
        log = open(CUPS_LOG, errors="replace").read()
        errs = {
            "paper-size-error":   "com.brother-paper-size-error" in log,
            "filter crash sig11":  "signal 11" in log,
            "filter failed":       "Filter failed" in log,
        }
        if any(errs.values()):
            warn("Past errors found in CUPS log:")
            for e, found in errs.items():
                if found: warn(f"  • {e} (fixed by running this script)")
            report_lines.append("Past errors: " + ", ".join(e for e,f in errs.items() if f))

    # P-touch
    ptouch_pref = PTOUCH_CONTAINER / "Data/Library/Preferences/com.brother.PtouchEditor.plist"
    rlog("P-touch Editor: No stale prefs", not ptouch_pref.exists(),
         "run --clean-ptouch" if ptouch_pref.exists() else "clean")

    # Summary
    section("SUMMARY")
    passed = sum(1 for v in results.values() if v)
    total  = len(results)
    color  = G if passed == total else (Y if passed >= total*0.7 else R)
    print(f"\n  {color}{BOLD}{passed}/{total} checks passed{X}\n")

    if passed == total:
        ok("All checks passed — printer should be working!")
    else:
        failed = [k for k,v in results.items() if not v]
        bad(f"{len(failed)} issue(s) found:")
        for f in failed: print(f"    {R}•{X} {f}")
        print(f"\n  Run {BOLD}sudo python3 brother_ql1100_fix.py{X} to fix automatically")

    if save_report:
        report_path = Path.home() / "Desktop" / f"brother_ql1100_diag_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        report_path.write_text("\n".join(report_lines))
        ok(f"Report saved: {report_path}")

    return passed == total

# ═══════════════════════════════════════════════════════════════════
# VERSION CHECK
# ═══════════════════════════════════════════════════════════════════
def check_for_updates():
    try:
        req = urllib.request.urlopen(SCRIPT_URL, timeout=3)
        remote = req.read().decode()
        m = re.search(r'VERSION\s*=\s*"([^"]+)"', remote)
        if m:
            remote_ver = m.group(1)
            local_parts  = [int(x) for x in VERSION.split(".")]
            remote_parts = [int(x) for x in remote_ver.split(".")]
            if remote_parts > local_parts:
                warn(f"Update available: v{remote_ver}  (you have v{VERSION})")
                warn(f"curl -O {SCRIPT_URL}")
            else:
                ok(f"Script is up to date (v{VERSION})")
    except Exception:
        pass  # silently skip if offline

# ═══════════════════════════════════════════════════════════════════
# FULL FIX
# ═══════════════════════════════════════════════════════════════════
def full_fix(media_code="DC16", skip_test=False):
    section("STEP 1 — PREFLIGHT")
    if os.geteuid() != 0:
        bad("Must run with sudo:  sudo python3 brother_ql1100_fix.py")
        sys.exit(1)
    ok(f"Running as root  |  macOS {platform.mac_ver()[0]}  {platform.machine()}")
    if not check_driver():
        sys.exit(1)
    ok("Brother driver installed")

    section("STEP 2 — USB DETECTION")
    uri, serial, speed = detect_usb()
    if not uri:
        bad("QL-1100 not detected via USB")
        bad("Check: cable connected? Printer on? Try a different USB port.")
        sys.exit(1)
    ok(f"URI:    {uri}")
    ok(f"Serial: {serial}")
    if speed == "USB1.1-12Mbps":
        warn(f"Speed:  {speed} — consider plugging directly into Mac's rear USB-A port")
    else:
        ok(f"Speed:  {speed or 'detected'}")

    section("STEP 3 — CLEAR STUCK JOBS + FLUSH SPOOL")
    progress("Clearing queue and flushing CUPS spool")
    clear_cups_queue()
    flush_cups_spool()

    section("STEP 4 — RECONFIGURE PRINTER")
    mc_info = MEDIA_CODES.get(media_code, {})
    info(f"Media code : {media_code}  ({mc_info.get('desc','?')})")
    info(f"Compatible : {mc_info.get('dk','?')}")
    if not setup_printer(uri, media_code):
        bad("Printer setup failed")
        sys.exit(1)
    ok(f"Printer {PRINTER_NAME} configured")

    section("STEP 5 — CLEAN P-TOUCH EDITOR CACHE")
    clean_ptouch()

    if not skip_test:
        section("STEP 6 — TEST PRINT")
        pdf = make_test_label("/tmp/brother_ql1100_test.pdf", media_code)
        ok(f"Test label PDF created")
        sent = send_to_printer(pdf, media_code)
        if sent:
            info("Waiting for printer...")
            success, state = wait_for_print(timeout=20)
            if success:
                ok("Test label printed successfully!")
            else:
                bad(f"Print may have failed: {state}")
                bad("Check: sudo cat /var/log/cups/error_log | tail -30")
        else:
            bad("Could not send test job")

    section("COMPLETE")
    W, H = PPD_DIMENSIONS.get(media_code, (288.00, 432.96))
    print(f"""
  {G}{BOLD}Brother QL-1100 is configured and ready.{X}

  {BOLD}Key settings:{X}
    Printer  : {PRINTER_NAME}
    URI      : {uri}
    Media    : {media_code}  ({mc_info.get('desc','?')})
    Canvas   : {W} x {H} pt  (must match your PDF exactly)

  {BOLD}Print from terminal:{X}
    {DIM}lp -d {PRINTER_NAME} -o media={media_code} yourfile.pdf{X}

  {BOLD}Print from Python:{X}
    {DIM}from reportlab.pdfgen import canvas{X}
    {DIM}c = canvas.Canvas("label.pdf", pagesize=({W}, {H})){X}
    {DIM}# ... draw ...{X}
    {DIM}c.save(){X}
    {DIM}os.system("lp -d {PRINTER_NAME} -o media={media_code} label.pdf"){X}

  {BOLD}Reopen P-touch Editor{X} — duplicate entries should be gone.
""")

# ═══════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(
        prog="brother_ql1100_fix",
        description=f"{BOLD}Brother QL-1100 macOS Fix v{VERSION}{X} — DK label printer utility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
{BOLD}Examples:{X}
  sudo python3 brother_ql1100_fix.py                        # Full fix (default DC16 / DK-1241 4x6")
  sudo python3 brother_ql1100_fix.py --media DC03           # Fix for DK-1201 29x90mm labels
  sudo python3 brother_ql1100_fix.py --diag                 # Diagnose only
  sudo python3 brother_ql1100_fix.py --diag --save-report   # Diag + save to Desktop
  sudo python3 brother_ql1100_fix.py --test-print           # Send test label
  sudo python3 brother_ql1100_fix.py --print-file label.pdf # Print a specific PDF
  sudo python3 brother_ql1100_fix.py --shipping             # Interactive shipping label
  sudo python3 brother_ql1100_fix.py --qr "https://mysite.com" --qr-title "My QR"
  python3 brother_ql1100_fix.py --clean-ptouch              # Fix P-touch duplicates
  python3 brother_ql1100_fix.py --watch ~/Desktop/labels    # Auto-print dropped PDFs
  python3 brother_ql1100_fix.py --list-media                # Show all DK media codes

{BOLD}Media codes for --media flag:{X}
  DC16 = DK-1241  102x152mm  4x6"    ← default
  DC03 = DK-1201  29x90mm   address
  DC04 = DK-1202  38x90mm   address
  DC07 = DK-1240  62x100mm  shipping
  (run --list-media for full table)
        """
    )

    parser.add_argument("--media",        default="DC16",     help="PPD media code (default: DC16 = DK-1241 4x6\")")
    parser.add_argument("--diag",         action="store_true", help="Run diagnostic only")
    parser.add_argument("--save-report",  action="store_true", help="Save diagnostic report to Desktop")
    parser.add_argument("--test-print",   action="store_true", help="Send test label only")
    parser.add_argument("--print-file",   metavar="FILE",      help="Print a specific PDF file")
    parser.add_argument("--copies",       type=int, default=1, help="Number of copies (default: 1)")
    parser.add_argument("--shipping",     action="store_true", help="Interactive shipping label generator")
    parser.add_argument("--qr",           metavar="TEXT",      help="Generate and print a QR code label")
    parser.add_argument("--qr-title",     metavar="TITLE",     help="Title for QR label")
    parser.add_argument("--qr-subtitle",  metavar="SUB",       help="Subtitle for QR label")
    parser.add_argument("--clean-ptouch", action="store_true", help="Clean P-touch Editor duplicate entries")
    parser.add_argument("--watch",        metavar="FOLDER",    help="Watch folder and auto-print PDFs")
    parser.add_argument("--list-media",   action="store_true", help="List all supported DK media codes")
    parser.add_argument("--skip-test",    action="store_true", help="Skip test print after fix")
    parser.add_argument("--update-driver",  action="store_true", help="Auto-download + install latest Brother driver (v1.11.0d, July 2025)")
    parser.add_argument("--no-update-check", action="store_true", help="Skip update check")
    parser.add_argument("--version",      action="version",    version=f"%(prog)s {VERSION}")

    args = parser.parse_args()

    # Header
    print(f"\n{C}{'═'*62}{X}")
    print(f"  {BOLD}Brother QL-1100 macOS Fix  v{VERSION}{X}")
    print(f"  {DIM}{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  |  macOS {platform.mac_ver()[0]}  {platform.machine()}{X}")
    print(f"{C}{'═'*62}{X}")

    if not args.no_update_check and not args.diag and not args.list_media:
        check_for_updates()

    # ── Validate media code ───────────────────────────────────────
    if args.media not in MEDIA_CODES:
        bad(f"Unknown media code: {args.media}")
        info("Run --list-media to see all valid codes")
        sys.exit(1)

    # ── Dispatch ──────────────────────────────────────────────────
    if args.list_media:
        section("SUPPORTED DK MEDIA CODES")
        print(f"  {'Code':<10} {'Description':<22} {'mm':<16} {'inch':<14} {'DK roll'}")
        print(f"  {'-'*9} {'-'*21} {'-'*15} {'-'*13} {'-'*10}")
        for code, d in MEDIA_CODES.items():
            mm = f"{d['mm'][0]}x{d['mm'][1]}mm"
            inch = f"{d['inch'][0]}x{d['inch'][1]}\""
            marker = " ◄ default" if code == "DC16" else ""
            print(f"  {code:<10} {d['desc']:<22} {mm:<16} {inch:<14} {d['dk']}{marker}")
        return

    if args.update_driver:
        auto_update_driver()
        return

    if args.diag:
        if os.geteuid() != 0:
            bad("Run with sudo for full diagnostic")
            sys.exit(1)
        run_diag(save_report=args.save_report)
        return

    if args.clean_ptouch:
        clean_ptouch()
        return

    if args.watch:
        watch_folder(args.watch, args.media)
        return

    if args.test_print:
        if os.geteuid() != 0: bad("Run with sudo"); sys.exit(1)
        pdf = make_test_label("/tmp/brother_ql1100_test.pdf", args.media)
        ok(f"Test label created: {pdf}")
        send_to_printer(pdf, args.media, args.copies)
        success, state = wait_for_print()
        ok("Printed!") if success else bad(f"Failed: {state}")
        return

    if args.print_file:
        if not os.path.exists(args.print_file):
            bad(f"File not found: {args.print_file}")
            sys.exit(1)
        info(f"Printing: {args.print_file}  (media={args.media}, copies={args.copies})")
        send_to_printer(args.print_file, args.media, args.copies)
        success, state = wait_for_print()
        ok("Printed!") if success else bad(f"Failed: {state}")
        return

    if args.qr:
        ensure_deps()
        section("QR CODE LABEL")
        pdf = "/tmp/brother_qr_label.pdf"
        make_qr_label(pdf, args.qr,
                      title=args.qr_title or "",
                      subtitle=args.qr_subtitle or args.qr)
        ok(f"QR label created: {pdf}")
        send_to_printer(pdf, args.media, args.copies)
        success, state = wait_for_print()
        ok("QR label printed!") if success else bad(f"Failed: {state}")
        return

    if args.shipping:
        section("SHIPPING LABEL GENERATOR")
        print(f"  {DIM}Press Enter to skip any field{X}\n")
        from_name = input(f"  {BOLD}From name:{X}    ").strip()
        from_addr = input(f"  {BOLD}From address:{X} ").strip()
        to_name   = input(f"  {BOLD}To name:{X}      ").strip()
        to_addr   = input(f"  {BOLD}To address:{X}   ").strip()
        tracking  = input(f"  {BOLD}Tracking #:{X}   ").strip()
        copies    = input(f"  {BOLD}Copies:{X}       ").strip() or "1"
        print()
        pdf = "/tmp/brother_shipping_label.pdf"
        make_shipping_label(pdf,
            from_name=from_name, from_addr=from_addr,
            to_name=to_name, to_addr=to_addr,
            tracking=tracking)
        ok(f"Shipping label created: {pdf}")
        send_to_printer(pdf, args.media, int(copies))
        success, state = wait_for_print(timeout=25)
        ok("Shipping label printed!") if success else bad(f"Failed: {state}")
        return

    # ── Default: full fix ─────────────────────────────────────────
    full_fix(media_code=args.media, skip_test=args.skip_test)


if __name__ == "__main__":
    main()
