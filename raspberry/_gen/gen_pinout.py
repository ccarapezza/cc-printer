#!/usr/bin/env python3
"""CC-Printer A1: Raspberry Pi 4 GPIO pinout sheet (fan + ADXL345 wiring for Klipper).
usage: gen_pinout.py <out_base>   -> <out_base>.png and <out_base>.pdf (A4 landscape)"""
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle, Circle

OUT = sys.argv[1]
NAMES = {1: "3,3 V", 2: "5 V", 3: "GPIO2 (SDA1)", 4: "5 V", 5: "GPIO3 (SCL1)", 6: "GND", 7: "GPIO4",
         8: "GPIO14 (TXD)", 9: "GND", 10: "GPIO15 (RXD)", 11: "GPIO17", 12: "GPIO18", 13: "GPIO27",
         14: "GND", 15: "GPIO22", 16: "GPIO23", 17: "3,3 V", 18: "GPIO24", 19: "GPIO10 (MOSI)",
         20: "GND", 21: "GPIO9 (MISO)", 22: "GPIO25", 23: "GPIO11 (SCLK)", 24: "GPIO8 (CE0)",
         25: "GND", 26: "GPIO7 (CE1)", 27: "ID_SD", 28: "ID_SC", 29: "GPIO5", 30: "GND", 31: "GPIO6",
         32: "GPIO12", 33: "GPIO13", 34: "GND", 35: "GPIO19", 36: "GPIO16", 37: "GPIO26",
         38: "GPIO20", 39: "GND", 40: "GPIO21"}
def kind(p):
    n = NAMES[p]
    return "5v" if n == "5 V" else "3v3" if n == "3,3 V" else "gnd" if n == "GND" else "io"
COL = {"5v": "#d32f2f", "3v3": "#ef6c00", "gnd": "#212121", "io": "#9e9e9e"}
FAN, ADXL = "#c62828", "#1565c0"
USE = {4: ("VENTILADOR  cable ROJO", FAN), 6: ("VENTILADOR  cable NEGRO", "#212121"),
       17: ("ADXL345  VCC", ADXL), 19: ("ADXL345  SDA", ADXL), 21: ("ADXL345  SDO", ADXL),
       23: ("ADXL345  SCL", ADXL), 24: ("ADXL345  CS", ADXL), 25: ("ADXL345  GND", ADXL)}

fig = plt.figure(figsize=(11.69, 8.27))
fig.text(0.5, 0.955, "Raspberry Pi 4 Model B  -  conector GPIO de 40 pines", ha="center",
         fontsize=17, weight="bold")
fig.text(0.5, 0.925, "CC-Printer A1 (Klipper): ventilador de la Pi + acelerómetro ADXL345",
         ha="center", fontsize=11, color="#444")

# ---------- left: board top view, rotated so USB is down and GPIO is on the right ----------
ab = fig.add_axes([0.02, 0.16, 0.30, 0.72]); ab.set_aspect("equal"); ab.axis("off")
ab.set_xlim(-16, 72); ab.set_ylim(-10, 100)
ab.add_patch(FancyBboxPatch((0, 0), 56, 85, boxstyle="round,pad=0,rounding_size=3",
                            fc="#4caf50", ec="#1b5e20", lw=1.5))
for x, y in [(3.5, 81.5), (52.5, 81.5), (3.5, 23.5), (52.5, 23.5)]:
    ab.add_patch(Circle((x, y), 1.4, fc="white", ec="#1b5e20"))
ab.add_patch(Rectangle((24.5, 48.5), 15, 15, fc="#bdbdbd", ec="#616161"))
ab.text(32, 56, "CPU", ha="center", va="center", fontsize=8)
ab.add_patch(Rectangle((2, -3), 52, 22, fc="#cfd8dc", ec="#546e7a", lw=1.2))
ab.text(28, 8, "USB  /  Ethernet", ha="center", va="center", fontsize=9, weight="bold")
for y, t in [(73.8, "USB-C"), (59, "HDMI"), (45.5, "HDMI")]:
    ab.add_patch(Rectangle((-2.5, y - 4), 6, 8, fc="#cfd8dc", ec="#546e7a"))
ab.annotate("USB-C\nalimentación", (-2.5, 73.8), (-15, 90), fontsize=8, ha="left",
            arrowprops=dict(arrowstyle="->", lw=0.8))
ab.text(-4, 52, "micro-HDMI", rotation=90, ha="right", va="center", fontsize=7.5, color="#333")
ab.add_patch(Rectangle((21, 83), 14, 4, fc="none", ec="#333", ls="--"))
ab.text(28, 89, "microSD (por debajo)", ha="center", fontsize=7.5, color="#333")
# header: odd (inner) column x=50, even (edge) column x=52.5, pin 1 at top
ab.add_patch(Rectangle((48.3, 26.9), 5.9, 51.2, fc="#263238", ec="#ffeb3b", lw=2.2))
for i in range(20):
    y = 76.6 - i * 2.54
    for p, x in ((2 * i + 1, 50.0), (2 * i + 2, 52.5)):
        c = USE[p][1] if p in USE else "#90a4ae"
        ab.add_patch(Circle((x, y), 0.85, fc=c, ec="none"))
ab.annotate("Pin 1", (50, 76.6), (57, 93), fontsize=9, weight="bold",
            arrowprops=dict(arrowstyle="->", lw=1.2, color="#f57f17"))
ab.text(60, 52, "GPIO (agrandado a la derecha)", rotation=-90, ha="center", va="center",
        fontsize=8, color="#333")
ab.text(28, -9, "Poné la Pi así:\nUSB abajo, conector GPIO a la derecha", ha="center", va="top",
        fontsize=10, weight="bold")

# ---------- right: enlarged header ----------
ah = fig.add_axes([0.33, 0.15, 0.66, 0.74]); ah.axis("off")
ah.set_xlim(-10.6, 11.6); ah.set_ylim(-20.0, 1.6)
XO, XE = 0.0, 1.2
ah.add_patch(FancyBboxPatch((XO - 0.55, -19.5), XE - XO + 1.1, 20, boxstyle="round,pad=0,rounding_size=0.3",
                            fc="#263238", ec="none"))
ah.text(XO - 0.45, 0.95, "adentro\n(impares)", ha="right", va="bottom", fontsize=8.5, color="#555")
ah.text(XE + 0.45, 0.95, "borde de la placa\n(pares)", ha="left", va="bottom", fontsize=8.5, color="#555")
for i in range(20):
    y = -i
    for p, x, side in ((2 * i + 1, XO, -1), (2 * i + 2, XE, +1)):
        k = kind(p); used = p in USE
        fc = COL[k]
        ah.scatter([x], [y], s=330, marker="s" if p == 1 else "o", c=fc,
                   edgecolors="#ffeb3b" if used else "#455a64", linewidths=2.4 if used else 0.8,
                   alpha=1.0 if used or k != "io" else 0.75, zorder=3)
        ah.text(x, y, str(p), ha="center", va="center", fontsize=7.5, weight="bold",
                color="white" if k != "io" else "#111", zorder=4)
        nx = x + side * 0.42
        ah.annotate(NAMES[p], (x, y), xytext=(side * 17, 0), textcoords="offset points",
                ha="left" if side > 0 else "right", va="center",
                fontsize=9.5 if used else 8.5, weight="bold" if used else "normal",
                color=COL[k] if k != "io" else ("#111" if used else "#777"))
        if used:
            label, c = USE[p]
            cx = x + side * (5.0 if side < 0 else 3.75)
            ah.plot([x + side * (3.95 if side < 0 else 3.1), cx - side * 0.15], [y, y], color=c, lw=1.4, zorder=2)
            ah.text(cx, y, label, ha="left" if side > 0 else "right", va="center", fontsize=10.5,
                    weight="bold", color="white",
                    bbox=dict(boxstyle="round,pad=0.3", fc=c, ec="none"))
ah.text(XO - 2.0, 0, "opcional: rojo del ventilador acá\n(gira más lento y silencioso)",
        ha="right", va="center", fontsize=7.5, style="italic", color="#777")
# legend
lx, ly = -10.2, -17.3
for j, (k, t) in enumerate([("5v", "5 V"), ("3v3", "3,3 V"), ("gnd", "GND (tierra)"), ("io", "GPIO")]):
    ah.scatter([lx], [ly - j * 0.75], s=120, c=COL[k], edgecolors="#455a64", linewidths=0.6)
    ah.text(lx + 0.4, ly - j * 0.75, t, va="center", fontsize=8.5)

notes = ("1) Conectá todo con la Pi DESENCHUFADA.      "
         "2) Pin 1: es el único con soldadura CUADRADA (se ve dando vuelta la placa).\n"
         "3) ADXL345 (GY-291): INT1 e INT2 quedan sin conectar; va a 3,3 V (pin 17), nunca a 5 V.      "
         "4) Ventilador: la etiqueta mira hacia la placa.")
fig.text(0.5, 0.045, notes, ha="center", va="center", fontsize=9.5,
         bbox=dict(boxstyle="round,pad=0.6", fc="#fff8e1", ec="#f9a825"))
fig.savefig(OUT + ".png", dpi=170)
fig.savefig(OUT + ".pdf")
print("ok", OUT)
