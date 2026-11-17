#!/usr/bin/env python3
"""CC-Printer A1 flow calibration: single-wall square box printed in spiral (vase) mode,
no seam, open top. Extrusion uses the stadium bead model so the caliper should read W
if flow is right. Measure mid-height of each face, away from corners."""
import math, sys
OUT = sys.argv[1]
CX, CY = 100.0, 100.0
SIDE = 40.0                 # outer size, mm
H = 15.0                    # height, mm
W, LH = 0.45, 0.2           # target wall width / layer height
L0, W0 = 0.3, 0.5           # first layer
FIL_A = math.pi * (1.75 / 2) ** 2
V, V0 = 30, 15              # mm/s spiral / first layer
T_NOZ = int(sys.argv[2]) if len(sys.argv) > 2 else 200   # usage: gen_flow_box.py <out.gcode> [hotend C]
T_BED, ACC = 60, 1000
BRIM = 4
SEG = 2.0                   # segment length for the Z ramp

def stadium(w, h):          # bead cross-section with round sides
    return (w - h) * h + math.pi * h * h / 4
EPM = stadium(W, LH) / FIL_A
EPM0 = W0 * L0 / FIL_A
HC = SIDE / 2 - W / 2       # wall centreline half-size

g = []; e = 0.0; pos = [0.0, 0.0]; t_est = 0.0
def emit(s): g.append(s)
def travel(x, y, f=3000):
    emit(f"G0 X{x:.3f} Y{y:.3f} F{f}"); pos[:] = [x, y]
def ext(x, y, z, f, epm):
    global e, t_est
    d = math.hypot(x - pos[0], y - pos[1]); e += d * epm; t_est += d / (f / 60)
    emit(f"G1 X{x:.3f} Y{y:.3f}" + (f" Z{z:.4f}" if z is not None else "") + f" E{e:.5f} F{f}")
    pos[:] = [x, y]
def corners(h):             # CCW from front-left
    return [(CX - h, CY - h), (CX + h, CY - h), (CX + h, CY + h), (CX - h, CY + h), (CX - h, CY - h)]

emit("; CC-Printer A1 - calibracion de FLUJO: caja de pared simple en espiral (generada, no Cura)")
emit(f"; {SIDE:.0f}x{SIDE:.0f}x{H:.0f} mm, pared objetivo {W} mm (modelo de cordon redondeado), capa {LH}, {V} mm/s, {T_NOZ} C")
emit("; Medir el espesor a media altura en las 4 caras, lejos de las esquinas, sin apretar el calibre")
for s in ["M220 S100", "M221 S100", "G90", "M82", f"M140 S{T_BED}", "M104 S160", "G28", "G1 Z10 F600",
          f"M190 S{T_BED}", f"M109 S{T_NOZ}", "G92 E0", "G1 X3 Y20 Z0.3 F2400", "G1 X3 Y180 Z0.3 F1200 E12",
          "G1 X3.5 Y180 Z0.3 F2400", "G1 X3.5 Y20 Z0.3 F1200 E24", "G92 E0", "G1 Z2 F600",
          f"M204 P{ACC} T{ACC}", "M107", "M117 Flujo: capa 1"]:
    emit(s)
# first layer: brim loops outward-in, then the wall loop
travel(CX - HC - BRIM * W0, CY - HC - BRIM * W0)
emit(f"G1 Z{L0:.3f} F300")
for k in range(BRIM, -1, -1):
    h = HC + k * W0
    pts = corners(h)
    travel(*pts[0]) if k != BRIM else None
    for x, y in pts[1:]:
        ext(x, y, None, V0 * 60, EPM0)
emit("M106 S255")
emit("M117 Flujo: espiral")
# spiral: z rises LH per loop; first loop ramps flow from 0 to full
pts = corners(HC)
loops = int(round((H - L0) / LH))
per = []
for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
    n = max(1, int(round(math.hypot(x1 - x0, y1 - y0) / SEG)))
    per += [(x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n) for i in range(1, n + 1)]
N = len(per)
for L in range(loops):
    for i, (x, y) in enumerate(per):
        frac = (i + 1) / N
        z = L0 + LH * (L + frac)
        ext(x, y, z, V * 60, EPM * (frac if L == 0 else 1.0))
emit("M400")
emit("G91"); emit("G1 E-2 F1500"); emit("G1 Z10 F600"); emit("G90")
emit("G1 X0 Y190 F2400"); emit("M104 S0"); emit("M140 S0"); emit("M107"); emit("M84")
emit("M117 Flujo listo: medir!")
open(OUT, "w").write("\n".join(g) + "\n")
print(f"loops={loops} top={L0+LH*loops:.2f} mm  E/mm={EPM:.5f} (Cura 0.4x0.2 = {0.08/FIL_A:.5f})  "
      f"tiempo de impresion ~{t_est/60:.1f} min + calentar  filamento {e/1000:.2f} m")
