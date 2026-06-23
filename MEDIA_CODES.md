# Brother QL-1100 Media Codes — Complete Reference

These are the **exact PPD internal codes** the `rastertobrotherQL1100` filter accepts.
Using any other value (e.g. `w10200h15200`, `Custom.4x6in`) causes filter crashes or `paper-size-error`.

## Die-Cut Labels

| PPD Code | Description     | Size (mm)    | Size (inch) | Compatible DK Roll | PDF Canvas (pt)      |
|----------|----------------|--------------|-------------|-------------------|----------------------|
| `DC01`   | Return address  | 17 × 54 mm   | 0.66 × 2.1" | DK-1204           | 48.24 × 152.64       |
| `DC02`   | File folder     | 17 × 87 mm   | 0.66 × 3.4" | DK-1203           | 48.24 × 246.24       |
| `DC03`   | Address (S)     | 29 × 90 mm   | 1.1 × 3.5"  | DK-1201           | 82.08 × 254.64       |
| `DC04`   | Address (L)     | 38 × 90 mm   | 1.5 × 3.5"  | DK-1202           | 107.76 × 254.64      |
| `DC06`   | Small address   | 62 × 29 mm   | 2.4 × 1.1"  | DK-1209           | 175.68 × 81.84       |
| `DC07`   | Shipping (S)    | 62 × 100 mm  | 2.4 × 3.9"  | DK-1240           | 175.68 × 282.96      |
| `DC08`   | Square          | 29 × 42 mm   | 1.1 × 1.6"  | DK-1221           | 82.08 × 118.80       |
| `DC15`   | Wide short      | 102 × 51 mm  | 4.0 × 2.0"  | DK-1247           | 288.00 × 143.04      |
| **`DC16`** | **Shipping (L)** | **102 × 152 mm** | **4.0 × 6.0"** | **DK-1241** ⭐ | **288.00 × 432.96** |
| `DC17`   | Name badge      | 39 × 48 mm   | 1.5 × 1.9"  | DK-1208           | 110.64 × 135.60      |
| `DC20`   | Square small    | 23 × 23 mm   | 0.9 × 0.9"  | DK-1219           | 65.28 × 65.28        |
| `DC24`   | Medium          | 52 × 29 mm   | 2.0 × 1.1"  | DK-1222           | 147.36 × 81.84       |
| `DCNB`   | Name badge (L)  | 60 × 86 mm   | 2.3 × 3.3"  | DK-1247           | 170.08 × 246.61      |
| `DC12`   | Round (S)       | 12 mm dia    | 0.5" dia    | DK-1235           | 34.08 × 34.08        |
| `DC13`   | Round (M)       | 24 mm dia    | 0.9" dia    | DK-1236           | 68.16 × 68.16        |
| `DC05`   | Round (L)       | 58 mm dia    | 2.3" dia    | DK-1207           | 165.12 × 165.12      |

⭐ = Most common — 4×6" shipping label (COLORWING compatible)

## Continuous Roll Labels

| PPD Code | Width    | DK Roll  |
|----------|----------|----------|
| `12mm`   | 12 mm    | DK-2205  |
| `29mm`   | 29 mm    | DK-2211  |
| `38mm`   | 38 mm    | DK-2213  |
| `50mm`   | 50 mm    | DK-2246  |
| `54mm`   | 54 mm    | DK-2243  |
| `62mm`   | 62 mm    | DK-2205  |
| `102mm`  | 102 mm   | DK-2246  |

## Usage

### Command line
```bash
# Use default DC16 (DK-1241 4x6")
sudo python3 brother_ql1100_fix.py

# Use a specific media code
sudo python3 brother_ql1100_fix.py --media DC03

# Print a file with specific media
sudo python3 brother_ql1100_fix.py --print-file label.pdf --media DC07
```

### lp command
```bash
lp -d Brother_QL1100 -o media=DC16 -o orientation-requested=3 yourfile.pdf
```

### Python (reportlab)
```python
from reportlab.pdfgen import canvas

# Use EXACT canvas dimensions from table above
# DC16 (DK-1241): 288.00 x 432.96 points
W, H = 288.00, 432.96
c = canvas.Canvas("label.pdf", pagesize=(W, H))
# ... draw content ...
c.save()
```

## Critical Notes

1. **Canvas dimensions must match PPD exactly** — even 1pt off can cause a filter crash
2. **`fit-to-page=false`** — never let CUPS rescale your PDF, it changes the dimensions
3. **COLORWING rolls** work fine with `DC16` even without the auto-detect chip
4. **USB speed** — if you see `UsbLinkSpeed = 12000000` (USB 1.1), plug directly into Mac's rear port
5. **Editor Lite LED** — if the green LED is on, hold the button until it turns off before printing
