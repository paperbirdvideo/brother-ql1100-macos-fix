# 🖨️ brother-ql1100-macos-fix

**Fix Brother QL-1100 not printing on macOS Sequoia. Resolves paper-size-error, filter crashes, and stuck jobs. Includes shipping label generator, QR code printer, and folder watch mode.**

> Tested on Mac Studio M4 · macOS 26 / Sequoia · COLORWING DK-1241 compatible rolls  
> Works with genuine Brother DK rolls too

---

## The Problem

You plug in your Brother QL-1100, install the driver, add it to CUPS — and nothing prints. Jobs disappear silently, or loop forever. The CUPS log is full of:

```
STATE: com.brother-paper-size-error
rastertobrotherQL1100 crashed on signal 11
printer-state-message = "Filter failed"
```

P-touch Editor shows two identical `QL-1100(USB)` entries and you don't know which one works.

**This script fixes all of it in one command.**

---

## Quick Start

### Option A — One-line install
```bash
curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/brother-ql1100-macos-fix/main/install.sh | bash
```

### Option B — Manual
```bash
git clone https://github.com/YOUR_USERNAME/brother-ql1100-macos-fix
cd brother-ql1100-macos-fix
pip3 install -r requirements.txt --break-system-packages
sudo python3 brother_ql1100_fix.py
```

That's it. Watch the printer.

---

## What Was Actually Wrong

After hours of diagnostics we traced it to four root causes:

| # | Symptom | Root Cause | Fix |
|---|---------|-----------|-----|
| 1 | `paper-size-error` repeating forever | CUPS sends the wrong media code to the printer | Use `media=DC16` — Brother's internal PPD name for 102×152mm |
| 2 | `rastertobrotherQL1100` crashes (signal 11) | PDF canvas dimensions don't match what the PPD declares | Build PDFs at exactly **288.00 × 432.96 points** |
| 3 | Jobs stuck in queue, never start | Previous failed jobs block new ones and CUPS spool fills | Flush spool + cancel all jobs before reconfiguring |
| 4 | Duplicate QL-1100 entries in P-touch Editor | Stale printer prefs cached in sandboxed app container | Wipe `~/Library/Containers/com.brother.PtouchEditor` |

### The Critical Discovery

The Brother PPD has an internal name for every label size. For the DK-1241 (102mm × 152mm / 4×6") it is `DC16`.

If you pass `media=Custom.4x6in`, `media=w10200h15200`, or anything else — the filter crashes or the printer rejects the job. **The only value that works is `-o media=DC16`.**

This is not documented anywhere on Brother's website, in their driver, or anywhere else we could find.

---

## Requirements

- macOS 13 Ventura or later (tested on macOS 15 Sequoia and macOS 26)
- Apple Silicon or Intel Mac
- Python 3.8+
- Brother QL-1100 driver installed — download from [Brother's support site](https://support.brother.com/g/b/downloadlist.aspx?c=us&lang=en&prod=lpql1100eus&os=10069)
- `reportlab` and `qrcode` — auto-installed on first run, or: `pip3 install -r requirements.txt --break-system-packages`

---

## All Commands

```bash
# ── Core fix ─────────────────────────────────────────────────────
sudo python3 brother_ql1100_fix.py                    # Full fix, default DC16 (DK-1241 4x6")
sudo python3 brother_ql1100_fix.py --media DC03       # Fix for a different label size
sudo python3 brother_ql1100_fix.py --skip-test        # Fix without sending a test print

# ── Diagnostics ──────────────────────────────────────────────────
sudo python3 brother_ql1100_fix.py --diag             # Full diagnostic, no changes made
sudo python3 brother_ql1100_fix.py --diag --save-report  # Save report to Desktop

# ── Printing ─────────────────────────────────────────────────────
sudo python3 brother_ql1100_fix.py --test-print       # Send a test label
sudo python3 brother_ql1100_fix.py --print-file label.pdf          # Print any PDF
sudo python3 brother_ql1100_fix.py --print-file label.pdf --copies 3  # Multiple copies

# ── Label generators ─────────────────────────────────────────────
sudo python3 brother_ql1100_fix.py --shipping         # Interactive shipping label
sudo python3 brother_ql1100_fix.py --qr "https://yoursite.com"          # QR code label
sudo python3 brother_ql1100_fix.py --qr "https://yoursite.com" --qr-title "My Store"

# ── Automation ───────────────────────────────────────────────────
python3 brother_ql1100_fix.py --watch ~/Desktop/PrintQueue   # Auto-print dropped PDFs

# ── Utilities ────────────────────────────────────────────────────
python3 brother_ql1100_fix.py --clean-ptouch          # Fix P-touch Editor duplicates
python3 brother_ql1100_fix.py --list-media            # Show all supported DK label codes
python3 brother_ql1100_fix.py --version               # Show version
```

---

## What the Full Fix Does

When you run `sudo python3 brother_ql1100_fix.py` it runs six steps:

1. **Preflight** — confirms driver and filter binary are installed, checks macOS version
2. **USB detection** — auto-detects the printer serial number and USB URI, checks link speed
3. **Clear queue** — cancels all stuck jobs, stops CUPS, flushes the spool directory, restarts CUPS
4. **Reconfigure printer** — removes the broken CUPS queue and recreates it with `DC16` as the permanent default media
5. **Clean P-touch Editor** — kills the app and wipes its sandboxed preference container to remove duplicate printer entries
6. **Test print** — generates a properly-sized PDF at exactly 288.00 × 432.96 pt and sends it to the printer

---

## Printing from Python

```python
from reportlab.pdfgen import canvas
import subprocess

# Canvas dimensions MUST match the PPD exactly — do not change these
# DC16 = DK-1241 = 102mm x 152mm = 4" x 6"
W, H = 288.00, 432.96  # points

c = canvas.Canvas("/tmp/label.pdf", pagesize=(W, H))

c.setFont("Helvetica-Bold", 24)
c.drawCentredString(W / 2, H / 2 + 20, "Ship To:")
c.setFont("Helvetica", 18)
c.drawCentredString(W / 2, H / 2 - 10, "123 Main St, Wilmington NC")

c.save()

subprocess.run([
    "lp",
    "-d", "Brother_QL1100",
    "-o", "media=DC16",
    "-o", "orientation-requested=3",
    "-o", "fit-to-page=false",
    "/tmp/label.pdf"
])
```

---

## Printing from Terminal

```bash
lp -d Brother_QL1100 \
   -o media=DC16 \
   -o orientation-requested=3 \
   -o fit-to-page=false \
   yourfile.pdf
```

---

## Manual Fix (No Script)

If you just want to copy-paste the fix without running the full script:

```bash
# 1. Cancel all stuck jobs
cancel -a Brother_QL1100 2>/dev/null

# 2. Flush CUPS spool
sudo launchctl unload /System/Library/LaunchDaemons/org.cups.cupsd.plist
sudo rm -f /var/spool/cups/c* /var/spool/cups/d* 2>/dev/null
sudo launchctl load /System/Library/LaunchDaemons/org.cups.cupsd.plist
sleep 3

# 3. Find your printer's USB serial number
/usr/libexec/cups/backend/usb 2>&1

# 4. Remove old queue and recreate with correct settings
lpadmin -x Brother_QL1100 2>/dev/null
lpadmin -p Brother_QL1100 -E \
  -v "usb://Brother/QL-1100?serial=YOUR_SERIAL_HERE" \
  -P "/Library/Printers/PPDs/Contents/Resources/Brother QL-1100 CUPS.gz" \
  -D "Brother QL-1100"

# 5. Set DC16 as permanent default — THIS IS THE KEY FIX
lpoptions -p Brother_QL1100 \
  -o media=DC16 \
  -o orientation-requested=3 \
  -o fit-to-page=false

# 6. Print
lp -d Brother_QL1100 -o media=DC16 yourfile.pdf
```

---

## Supported Label Sizes

See [MEDIA_CODES.md](MEDIA_CODES.md) for the complete table of all 23 DK label sizes and their exact PPD codes and canvas dimensions.

Quick reference for the most common sizes:

| PPD Code | Label Size | DK Roll | PDF Canvas (pt) |
|----------|-----------|---------|----------------|
| `DC16` ⭐ | 102 × 152 mm — 4 × 6" shipping | DK-1241 | 288.00 × 432.96 |
| `DC03` | 29 × 90 mm — standard address | DK-1201 | 82.08 × 254.64 |
| `DC04` | 38 × 90 mm — large address | DK-1202 | 107.76 × 254.64 |
| `DC07` | 62 × 100 mm — shipping (S) | DK-1240 | 175.68 × 282.96 |
| `DC15` | 102 × 51 mm — wide short | DK-1247 | 288.00 × 143.04 |

⭐ Default — most common for 4×6" shipping labels

---

## Troubleshooting

**Printer not detected at all**
- Check the USB cable is firmly connected at both ends
- Make sure the printer is powered on (solid green power light)
- Try plugging directly into a rear USB-A port on your Mac — bypass all hubs and docks
- If you see `UsbLinkSpeed = 12000000` in the diagnostic that means USB 1.1 speed (12 Mbps instead of 480 Mbps) — almost always caused by a bad cable or hub

**Still getting paper-size-error after fix**
```bash
sudo python3 brother_ql1100_fix.py --diag --save-report
```
Open the report on your Desktop and look for the CUPS log section.

**Editor Lite LED is glowing green**
The printer physically blocks all CUPS printing while Editor Lite mode is active. Hold the Editor Lite button on the top of the printer until the green LED turns off.

**COLORWING rolls not printing**
COLORWING compatible rolls work perfectly — they just don't have the auto-detect chip that genuine Brother rolls have. The `DC16` media code bypasses chip detection entirely, which is why the fix works.

**P-touch Editor still shows two printers after clean**
```bash
python3 brother_ql1100_fix.py --clean-ptouch
```
Then fully quit and reopen P-touch Editor.

**Jobs process but nothing comes out**
Check that the label roll is loaded correctly and the roll guide is snapped in. Press the feed button manually — if the printer feeds a blank label, the hardware is fine and the issue is in the job data.

---

## Tested On

| Hardware | macOS | Label Roll | Result |
|----------|-------|-----------|--------|
| Mac Studio M4 | macOS 26.5.1 | COLORWING DK-1241 (4 roll pack) | ✅ Working |
| Mac Studio M4 | macOS 15.5 Sequoia | COLORWING DK-1241 | ✅ Working |

Confirmed working on Intel Macs as well — open an issue if you test it and we'll add your config to this table.

---

## Folder Watch Mode

Drop any PDF into a watched folder and it prints automatically.

```bash
# Create the watch folder
mkdir ~/Desktop/PrintQueue

# Start watching (Ctrl+C to stop)
python3 brother_ql1100_fix.py --watch ~/Desktop/PrintQueue
```

Printed files are automatically moved to `~/Desktop/PrintQueue/printed/` so you always know what has been sent.

---

## File Structure

```
brother-ql1100-macos-fix/
├── brother_ql1100_fix.py   # Main script — fix + print utility
├── install.sh              # One-line installer + alias setup
├── requirements.txt        # reportlab, qrcode, Pillow
├── MEDIA_CODES.md          # Complete DK label size reference
└── README.md               # This file
```

---

## How This Was Found

This fix came out of a real troubleshooting session on a Mac Studio M4 running macOS 26 with COLORWING DK-1241 compatible rolls. The printer was detected, CUPS said it was idle, jobs submitted — and nothing printed.

After building comprehensive diagnostic tooling we found the CUPS error log showing `com.brother-paper-size-error` repeating on every job, and `rastertobrotherQL1100` crashing with signal 11 (segfault) when the PDF dimensions didn't match the PPD.

The breakthrough was reading the raw PPD file directly and finding that Brother's filter uses its own internal code system — `DC16` for the 102×152mm label — completely separate from standard CUPS media names. Nothing in Brother's documentation, support pages, or any forum post mentioned this.

---

## Contributing

PRs welcome. If you get this working on other hardware, macOS versions, or label sizes, please open an issue or PR with your results.

Found this useful? **⭐ Star the repo** so other people can find it when they're Googling their Brother printer problems at midnight.

---

## License

MIT — free to use, modify, and distribute.
